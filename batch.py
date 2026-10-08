"""顧客ジョブをCPUコア数に応じてプロセス並列で実行するCLI。"""

import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import json
import multiprocessing
from multiprocessing.util import Finalize
import os
from pathlib import Path
import sys

# 各ライブラリ内の数値計算スレッドの増殖を抑える。外部設定があれば優先する。
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

# これらの変数は各ワーカープロセスの中で個別に保持される。
# 顧客データではなく、再利用するブラウザー・DB取得サービスだけを入れる。
_service = None
_source = None


def cpu_workers():
    """現在のプロセスが利用できる論理CPU数を求める。

    Returns:
        int: CPU数。未取得なら1。WindowsはProcessPoolExecutorの上限61まで。
    """
    # Pythonのバージョンに応じて、利用できる論理CPU数を取得する。
    # コンテナー等で実際の上限と異なる場合は--workersで明示的に調整する。
    if hasattr(os, "process_cpu_count"):
        count = os.process_cpu_count() or 1
    elif hasattr(os, "sched_getaffinity"):
        count = len(os.sched_getaffinity(0)) or 1
    else:
        count = os.cpu_count() or 1
    return min(count, 61) if sys.platform == "win32" else count


def _close_worker():
    """ワーカー終了時にChromiumを閉じる。"""
    try:
        if _service is not None:
            _service.close()
    finally:
        if _source is not None:
            _source.close()


def _init_worker(font, browser, db_settings=None, bold_font=None):
    """各ワーカー内で帳票サービスを一度だけ作る。

    Args:
        font (str | None): 日本語フォントの絶対パス。
        browser (str | None): Chromiumの絶対パス。
        db_settings (dict | None): DB取得設定。接続はワーカー内で作る。
        bold_font (str | None): 太字書体の絶対パス。
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
        from services.database_source import DatabaseSource

        _source = DatabaseSource(db_settings)


def _run_job(job):
    """1件を処理し、成功・失敗を小さな辞書で親へ返す。

    Args:
        job (dict): id、csvまたはsupply_point、config、outputを持つジョブ。

    Returns:
        dict: id、status、output、成功時のbytesまたは失敗時のerror。
    """
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


def run_jobs(
    jobs, workers=None, font=None, browser=None, db_settings=None, bold_font=None
):
    """ジョブを有限個ずつ投入し、完了した結果を順次返す。

    同時に投入する件数をワーカー数の2倍までに制限する。
    プロセス間でDataFrame、画像、PDFは受け渡さない。各ワーカーが
    CSVを読み、PDFを保存し、結果のメタデータだけを返す。

    Args:
        jobs (list[dict]): load_jobsで検証済みのジョブ。
        workers (int | None): 並列数。既定は利用可能CPU数。
        font (pathlib.Path | None): 日本語フォント。
        browser (pathlib.Path | None): Chromium実行ファイル。
        db_settings (dict | None): テーブル入力時のDB設定。
        bold_font (pathlib.Path | None): 太字書体。各ワーカーで一度だけ読み込む。

    Yields:
        dict: 完了順の成功・失敗結果。入力順とは限らない。

    Raises:
        ValueError: workersが正の整数でない場合。
        concurrent.futures.process.BrokenProcessPool: ワーカーが異常終了した場合。
    """
    count = cpu_workers() if workers is None else workers
    if not isinstance(count, int) or count < 1:
        raise ValueError("workersは正の整数で指定してください")
    count = min(count, len(jobs))
    if not jobs:
        return
    # spawnで独立したPythonプロセスを起動する。
    # Matplotlibの全体設定と同期Playwrightをワーカーごとに分離する。
    with ProcessPoolExecutor(
        max_workers=count,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_init_worker,
        initargs=(
            str(Path(font).resolve()) if font else None,
            str(Path(browser).resolve()) if browser else None,
            db_settings,
            str(Path(bold_font).resolve()) if bold_font else None,
        ),
    ) as pool:
        # 投入待ちのジョブを順番に取り出す。全件の重いデータを先に読み込まない。
        iterator = iter(jobs)
        pending = set()
        # 最初はワーカー数の2倍まで投入する。
        # 処理中のジョブと少数の待機ジョブだけを持ち、無制限にキューを増やさない。
        for _ in range(count * 2):
            job = next(iterator, None)
            if job is None:
                break
            pending.add(pool.submit(_run_job, job))
        while pending:
            # 1件以上の完了を待ち、完了した分だけ次のジョブを追加する。
            # 結果は入力順ではなく完了順で返り、遅い顧客が他の結果を止めない。
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                yield future.result()
                job = next(iterator, None)
                if job is not None:
                    pending.add(pool.submit(_run_job, job))


def main():
    """ジョブJSONに従って並列生成し、結果JSONを保存する。

    1件のデータ不正では他のジョブを止めず、失敗結果を記録する。
    失敗があれば終了コード1、全成功なら0で終了する。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("output/batch"))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--font-bold", type=Path)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--db-config", type=Path)
    parser.add_argument("--report-month", help="DB取得の最終月。指定月を含む12か月")
    args = parser.parse_args()
    jobs = load_jobs(args.jobs, args.output_dir)
    db_settings = (
        json.loads(args.db_config.read_text(encoding="utf-8"))
        if args.db_config
        else None
    )
    if any("supply_point" in job for job in jobs) and db_settings is None:
        parser.error("テーブル入力には--db-configが必要です")
    # CLIで対象月を指定した場合は、各DBジョブの月よりも優先する。
    if args.report_month:
        from services.data_service import bounds

        bounds(args.report_month)
        for job in jobs:
            if "supply_point" in job:
                job["report_month"] = args.report_month
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for result in run_jobs(
        jobs, args.workers, args.font, args.browser, db_settings, args.font_bold
    ):
        results.append(result)
        print(
            f'{len(results)}/{len(jobs)} {result["id"]}: {result["status"]}', flush=True
        )
    # 成功・失敗を保存先とともに記録する。再実行する顧客を判断するための一覧。
    (args.output_dir / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if any(row["status"] != "succeeded" for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    # Windowsや実行ファイル化した環境でも、子プロセスを正しく起動できるようにする。
    multiprocessing.freeze_support()
    main()
