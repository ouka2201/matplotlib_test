"""顧客ジョブをCPUコア数に応じてプロセス並列で実行するCLI。"""

import argparse
import json
import multiprocessing
import os
from multiprocessing.util import Finalize
from pathlib import Path

from services.batch_service import cpu_workers, managed_report_filename, run_parallel

# これらの変数は各ワーカープロセスの中で個別に保持される。
# 顧客データではなく、再利用するブラウザー・DB取得サービスだけを入れる。
_service = None
_source = None


def _close_worker():
    """ワーカー終了時にChromiumを閉じる。"""
    try:
        if _service is not None:
            _service.close()
    finally:
        if _source is not None:
            _source.close()


def _init_worker(font, browser, db_settings=None, bold_font=None, managed=False):
    """各ワーカー内で帳票サービスを一度だけ作る。

    Args:
        font (str | None): 日本語フォントの絶対パス。
        browser (str | None): Chromiumの絶対パス。
        db_settings (dict | None): DB取得設定。接続はワーカー内で作る。
        bold_font (str | None): 太字書体の絶対パス。
        managed (bool): Trueなら管理状態・ARVE情報も扱うDBサービスを作る。
    """
    global _service, _source
    # 重いライブラリの読み込みと初期化は子プロセス側で行う。
    # 親で開いたブラウザーやDB接続をプロセス間で共有しないため。
    from services.report_service import ReportService

    _service = ReportService(
        Path(font) if font else None,
        Path(browser) if browser else None,
        Path(bold_font) if bold_font else None,
    )
    # ワーカーの通常終了時にブラウザーとDB接続プールを閉じる。
    Finalize(None, _close_worker, exitpriority=10)
    if db_settings is not None:
        if managed:
            from services.report_job_source import ReportJobSource as Source
        else:
            from services.database_source import DatabaseSource as Source

        _source = Source(db_settings)


def _run_managed_job(job):
    """管理テーブルから取得した1件を着手・作成・状態更新する。

    Args:
        job (dict): managementの取得レコード、config_values、output_dirを持つジョブ。

    Returns:
        dict: id、status、outputと生成結果。先に着手された1件はskipped。
            状態更新自体が失敗した場合はstate_update_errorも記録する。
    """
    target = job["management"]
    output, claimed = None, False
    try:
        if _source is None:
            raise ValueError("管理テーブル入力にはDB取得サービスが必要です")
        # 主キーごとの処理権を取得する。状態2も対象なので更新だけには頼らない。
        claimed = _source.claim(target)
        if not claimed:
            return {"id": job["id"], "status": "skipped", "output": None}
        filename = managed_report_filename(target)
        point, month = target["supply_point"], target["target_year_month"]
        report_month = f"{month[:4]}-{month[4:]}"
        # 添付の命名規則で保存し、同じ名前を管理テーブルにも記録する。
        output = (Path(job["output_dir"]) / filename).resolve()
        if len(str(output)) > 255:
            raise ValueError(
                "管理テーブルへ保存するPDFの絶対パスは255文字以内にしてください"
            )
        if output == Path(job["config_path"]):
            raise ValueError("PDF保存先と共通設定ファイルのパスが競合しています")
        # No.0の契約情報をARVEから取得し、サンプルの名義を使用しない。
        config = {
            **job["config_values"],
            **_source.load_customer(point),
            "target_month": report_month,
            "company_id": target["company_id"],
            "syousapo_flg": target["syousapo_flg"],
        }
        result = _service.generate_database(
            _source, point, report_month, config, output
        )
        # 原子的なPDF保存に成功した後でのみ、完了状態と保存先を記録する。
        _source.finish(target, output=output)
        return {"id": job["id"], **result, "create_status": "3"}
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result = {
            "id": job["id"],
            "status": "failed",
            "output": str(output) if output else None,
            "error": error,
        }
        if claimed:
            try:
                _source.finish(target, error=error)
                result["create_status"] = "5"
            except Exception as state_exc:
                # DB障害時に「状態更新も成功した」と報告しない。復旧判断用に残す。
                result["state_update_error"] = (
                    f"{type(state_exc).__name__}: {state_exc}"
                )
        return result
    finally:
        # 状態更新の障害時にも、次の1件へロックや接続を持ち越さない。
        if _source is not None:
            _source.release_claim()


def _run_job(job):
    """1件を処理し、成功・失敗を小さな辞書で親へ返す。

    Args:
        job (dict): CSV・DBの従来ジョブ、またはmanagementを持つ管理テーブルの1件。

    Returns:
        dict: id、status、output、成功時のbytesまたは失敗時のerror。
    """
    if "management" in job:
        return _run_managed_job(job)
    try:
        config = json.loads(Path(job["config"]).read_text(encoding="utf-8"))
        # 顧客1件ごとに設定とデータを読み込む。画像やDataFrameを親から送らない。
        if "supply_point" in job:
            if _source is None:
                raise ValueError("テーブル入力には--db-configが必要です")
            result = _service.generate_database(
                _source,
                job["supply_point"],
                job.get("report_month") or config["target_month"],
                config,
                Path(job["output"]),
            )
        else:
            result = _service.generate(Path(job["csv"]), config, Path(job["output"]))
        return {"id": job["id"], **result}
    # 顧客単位のエラーを結果に変換する。他の顧客の処理は継続できる。
    # ワーカー自体の異常終了は、この関数の外でExecutorのエラーになる。
    except Exception as exc:
        return {
            "id": job["id"],
            "status": "failed",
            "output": job["output"],
            "error": f"{type(exc).__name__}: {exc}",
        }


def load_jobs(manifest, output_dir):
    """ジョブ一覧を読み、パスと保存先の競合を事前に検査する。

    Args:
        manifest (pathlib.Path): ジョブ配列のJSON。csv/configの相対パスはこのファイル基準。
            DB入力ではcsvの代わりにsupply_pointを指定する。
        output_dir (pathlib.Path): 最終PDFの保存先フォルダー。

    Returns:
        list[dict]: 各パスを絶対パスにしたジョブ。

    Raises:
        ValueError: 空の一覧、ID重複、不正なID、入力と出力のパス競合がある場合。
    """
    import re

    # 入力ファイルの相対パスはジョブJSONの場所を基準に解決する。
    # 実行したカレントフォルダーに左右されないようにする。
    manifest = Path(manifest).resolve()
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("ジョブJSONには1件以上の配列が必要です")
    jobs, ids, outputs, inputs = [], set(), set(), set()
    for row in rows:
        # 顧客IDをPDF名に使うため、使用可能文字と重複を先に検査する。
        # 大小文字だけ違うIDも拒否し、Windowsでの同名ファイルを防ぐ。
        name = str(row["id"])
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or name.casefold() in ids:
            raise ValueError(f"IDが不正または重複しています: {name}")
        ids.add(name.casefold())
        has_csv = "csv" in row
        has_point = "supply_point" in row
        if has_csv == has_point:
            raise ValueError("ジョブにはcsvまたはsupply_pointのどちらか1つが必要です")
        if has_point and (
            not isinstance(row["supply_point"], str)
            or not row["supply_point"]
            or len(row["supply_point"]) > 22
        ):
            raise ValueError("供給地点特定番号は22文字以内の文字列で指定してください")
        config = (manifest.parent / row["config"]).resolve()
        output = (Path(output_dir) / f"{name}.pdf").resolve()
        key = os.path.normcase(str(output))
        if key in outputs:
            raise ValueError(f"PDF保存先が重複しています: {output}")
        outputs.add(key)
        inputs.add(os.path.normcase(str(config)))
        job = {"id": name, "config": str(config), "output": str(output)}
        if has_csv:
            csv = (manifest.parent / row["csv"]).resolve()
            inputs.add(os.path.normcase(str(csv)))
            job["csv"] = str(csv)
        else:
            job["supply_point"] = row["supply_point"]
            if "report_month" in row:
                from services.data_service import bounds

                bounds(row["report_month"])
                job["report_month"] = row["report_month"]
        jobs.append(job)
    # PDFの出力先がCSVや設定ファイルと同じなら、入力を上書きするため拒否する。
    if outputs & inputs:
        raise ValueError("PDF保存先と入力ファイルのパスが競合しています")
    return jobs


def load_managed_jobs(settings, output_dir, config_path, report_month):
    """親プロセスで管理テーブルから作成対象だけを取得する。

    取得用DB接続は子プロセス起動前に閉じる。各ジョブには主キー・対象月・
    共通設定だけを持たせ、実績と契約情報の取得は各ワーカーで実行する。

    Args:
        settings (dict): 管理・ARVE・実績テーブルのDB設定。
        output_dir (pathlib.Path): 最終PDFの保存先。
        config_path (pathlib.Path): 共通の注記などを持つJSON。契約値はDBで置き換える。
        report_month (str): 検索する対象年月。YYYY-MMまたはYYYYMM。

    Returns:
        list[dict]: 取得順の軽いジョブ一覧。対象0件なら空配列。
    """
    from services.report_job_source import ReportJobSource

    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("共通設定JSONにはオブジェクトが必要です")
    source = ReportJobSource(settings)
    try:
        targets = source.fetch_targets(report_month)
    finally:
        source.close()
    return [
        {
            "id": f'{target["supply_point"]}_{target["target_year_month"]}',
            "management": target,
            "config_values": config,
            "config_path": str(config_path),
            "output_dir": str(Path(output_dir).resolve()),
        }
        for target in targets
    ]


def run_jobs(
    jobs,
    workers=None,
    font=None,
    browser=None,
    db_settings=None,
    bold_font=None,
    managed=False,
):
    """ジョブを有限個ずつ投入し、完了した結果を順次返す。

    同時に投入する件数をワーカー数の2倍までに制限する。
    プロセス間でDataFrame、画像、PDFは受け渡さない。各ワーカーが
    CSVまたはDBから取得し、PDFを保存し、結果のメタデータだけを返す。

    Args:
        jobs (list[dict]): load_jobsまたはload_managed_jobsで取得したジョブ。
        workers (int | None): 並列数。既定は利用可能CPU数。
        font (pathlib.Path | None): 日本語フォント。
        browser (pathlib.Path | None): Chromium実行ファイル。
        db_settings (dict | None): テーブル入力時のDB設定。
        bold_font (pathlib.Path | None): 太字書体。各ワーカーで一度だけ読み込む。
        managed (bool): Trueなら管理テーブルの状態・ARVE情報を処理する。

    Yields:
        dict: 完了順の成功・失敗・スキップ結果。入力順とは限らない。

    Raises:
        ValueError: workersが正の整数でない場合。
        concurrent.futures.process.BrokenProcessPool: ワーカーが異常終了した場合。
    """
    yield from run_parallel(
        jobs,
        _run_job,
        workers=cpu_workers() if workers is None else workers,
        initializer=_init_worker,
        initargs=(
            str(Path(font).resolve()) if font else None,
            str(Path(browser).resolve()) if browser else None,
            db_settings,
            str(Path(bold_font).resolve()) if bold_font else None,
            managed,
        ),
    )


def main():
    """管理テーブルまたはジョブJSONに従って並列生成し、結果JSONを保存する。

    1件のデータ不正では他のジョブを止めず、失敗結果を記録する。
    失敗があれば終了コード1、全成功なら0で終了する。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--jobs", type=Path)
    source.add_argument(
        "--from-management",
        action="store_true",
        help="管理テーブルから指定年月の作成対象2・エラー5を取得する",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="管理テーブル入力の共通設定JSON。契約情報はARVEから取得する",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/batch"))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--font-bold", type=Path)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--db-config", type=Path)
    parser.add_argument(
        "--report-month",
        help="管理入力では対象年月YYYY-MM/ YYYYMM（必須）。通常DB入力では最終月YYYY-MM",
    )
    args = parser.parse_args()
    db_settings = (
        json.loads(args.db_config.read_text(encoding="utf-8"))
        if args.db_config
        else None
    )
    if args.from_management:
        if db_settings is None:
            parser.error("管理テーブル入力には--db-configが必要です")
        if not args.report_month:
            parser.error("管理テーブル入力には--report-monthが必要です")
        from services.report_job_source import normalize_report_ym

        try:
            normalize_report_ym(args.report_month)
        except ValueError as exc:
            parser.error(str(exc))
        jobs = load_managed_jobs(
            db_settings,
            args.output_dir,
            args.config or Path(__file__).parent / "examples" / "customer.json",
            args.report_month,
        )
    else:
        if args.config:
            parser.error("--configは--from-managementと併用してください")
        jobs = load_jobs(args.jobs, args.output_dir)
    if any("supply_point" in job for job in jobs) and db_settings is None:
        parser.error("テーブル入力には--db-configが必要です")
    # CLIで対象月を指定した場合は、各DBジョブの月よりも優先する。
    if args.report_month and not args.from_management:
        from services.data_service import bounds

        bounds(args.report_month)
        for job in jobs:
            if "supply_point" in job:
                job["report_month"] = args.report_month
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not jobs:
        print("作成対象が0件のため、並列処理を行わず終了します。", flush=True)
    results = []
    for result in run_jobs(
        jobs,
        args.workers,
        args.font,
        args.browser,
        db_settings,
        args.font_bold,
        managed=args.from_management,
    ):
        results.append(result)
        print(
            f'{len(results)}/{len(jobs)} {result["id"]}: {result["status"]}', flush=True
        )
    # 成功・失敗を保存先とともに記録する。再実行する顧客を判断するための一覧。
    (args.output_dir / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if any(row["status"] == "failed" for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    # Windowsや実行ファイル化した環境でも、子プロセスを正しく起動できるようにする。
    multiprocessing.freeze_support()
    main()
