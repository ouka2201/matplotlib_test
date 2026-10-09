"""1件のSQL取得からPDF保存までを、CPU数のプロセスで処理する。"""

from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import multiprocessing
from multiprocessing.util import Finalize
import os
from pathlib import Path
import sys

# 子プロセス内で数値計算スレッドが増えすぎないようにする。
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")


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


def managed_report_filename(target):
    """管理レコードの企業ID・供給地点・加入フラグ・対象年月からPDF名を作る。

    未加入は「企業ID_供給地点特定番号_YYYYMM.pdf」、加入は
    「企業ID_供給地点特定番号_syousapo_YYYYMM.pdf」。管理テーブルの
    値をそのまま使用し、先頭ゼロを削除したり欠損値を代用したりしない。

    Args:
        target (dict): company_id、supply_point、target_year_month、
            syousapo_flgを持つ管理テーブルの取得レコード。

    Returns:
        str: 拡張子.pdfを含む保存ファイル名。

    Raises:
        ValueError: 企業ID・供給地点・対象年月が不正、または加入フラグが
            boolでない場合。パス区切り等が含まれる値も拒否する。
    """
    import re
    from services.data_service import bounds

    company = target["company_id"]
    point, month = target["supply_point"], target["target_year_month"]
    joined = target["syousapo_flg"]
    if not isinstance(company, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,14}", company
    ):
        raise ValueError("企業IDは14文字以内の英数字・ハイフン・下線が必要です")
    if not isinstance(point, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,22}", point):
        raise ValueError(
            "供給地点特定番号は22文字以内の英数字・ハイフン・下線が必要です"
        )
    if not isinstance(month, str) or not re.fullmatch(r"\d{6}", month):
        raise ValueError("管理テーブルの対象年月はYYYYMMの6桁文字列が必要です")
    bounds(f"{month[:4]}-{month[4:]}")
    # "False"などの文字列をbool()でTrueと解釈し、加入者の名前にしない。
    if not isinstance(joined, bool):
        raise ValueError("省サポ加入フラグSYOUSAPO_FLGはTrueまたはFalseが必要です")
    suffix = "_syousapo" if joined else ""
    return f"{company}_{point}{suffix}_{month}.pdf"


def run_parallel(items, function, *, workers=None, initializer=None, initargs=()):
    """1件ずつ有限数を投入し、完了した結果を順に返す共通の並列処理。

    Args:
        items (list): 軽い対象情報。実績・画像・DB接続は含めない。
        function (Callable): 子プロセスで1件を処理するモジュール直下の関数。
        workers (int | None): 並列数。省略時は利用可能CPU数。
        initializer (Callable | None): 各子プロセスで一度だけ行う初期化。
        initargs (tuple): 初期化関数へ渡す引数。

    Yields:
        dict: 完了順の1件の結果。

    Raises:
        ValueError: 並列数が不正な場合。
        concurrent.futures.process.BrokenProcessPool: 初期化やプロセスが異常終了した場合。
    """
    count = cpu_workers() if workers is None else workers
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("workersは正の整数で指定してください")
    if not items:
        return
    count = min(count, len(items))
    if sys.platform == "win32" and count > 61:
        raise ValueError("Windowsのworkersは61以下で指定してください")
    with ProcessPoolExecutor(
        max_workers=count,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=initializer,
        initargs=initargs,
    ) as pool:
        iterator = iter(items)
        pending = set()
        # 実行中と待機中を合わせてCPU数の2倍まで。全件をキューへ積まない。
        for _ in range(count * 2):
            item = next(iterator, None)
            if item is None:
                break
            pending.add(pool.submit(function, item))
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                yield future.result()
                item = next(iterator, None)
                if item is not None:
                    pending.add(pool.submit(function, item))


_worker = None


def _close_reports():
    """ワーカー終了時に、再利用していたReportServiceを閉じる。"""
    if _worker is not None:
        _worker["service"].close()


def _initialize_reports(get_session, load_sql_file, options):
    """子プロセスで既存DB関数と帳票サービスを一度だけ準備する。

    Args:
        get_session (Callable): 新しいDBセッションを返す既存関数。
        load_sql_file (Callable): SQL文字列を返す既存関数。
        options (dict): 対象月、保存先、任意の書体と列設定。
    """
    global _worker
    from services.report_service import ReportService

    _worker = {
        **options,
        "get_session": get_session,
        "load_sql_file": load_sql_file,
        "service": ReportService(
            font=options.get("font"),
            browser=options.get("browser"),
            bold_font=options.get("bold_font"),
        ),
    }
    Finalize(None, _close_reports, exitpriority=10)


def _run_report(target):
    """同じワーカーで1件のSQL取得・PDF生成・保存まで行う。

    Args:
        target (dict): supply_point_number、company_id、syousapo_flgの対象行。

    Returns:
        dict: 地点、成功・失敗、保存先。失敗時はerrorも含める。
    """
    from sqlalchemy import text
    from services.data_service import bounds

    point = target["supply_point_number"]
    output = None
    try:
        if _worker is None:
            raise RuntimeError("run_reportsからワーカーを初期化してください")
        month = _worker["report_month"]
        filename = managed_report_filename(
            {
                **target,
                "supply_point": point,
                "target_year_month": month.replace("-", ""),
            }
        )
        output = (_worker["output_dir"] / filename).resolve()
        get_session, load_sql_file = _worker["get_session"], _worker["load_sql_file"]
        # 生のResultを保持せず、セッション内で全行を取り出す。
        with get_session() as session:
            customer = dict(
                session.execute(
                    text(load_sql_file("select_power_report_cust.sql")),
                    {"supply_point_number": point},
                )
                .mappings()
                .one()
            )
        start, end, _ = bounds(month)
        with get_session() as session:
            daily_rows = [
                dict(row)
                for row in session.execute(
                    text(load_sql_file("select_power_report_30min.sql")),
                    {
                        "supply_point_number": point,
                        "start_date": start.strftime("%Y%m%d"),
                        "end_date": end.strftime("%Y%m%d"),
                    },
                )
                .mappings()
                .all()
            ]
        result = _worker["service"].generate_query_results(
            customer_row=customer,
            daily_rows=daily_rows,
            supply_point=point,
            report_month=month,
            output=output,
            **_worker["column_options"],
        )
        return {**result, "supply_point_number": point}
    except Exception as exc:
        # 1件のエラーを結果へ変換し、次の対象を続ける。
        return {
            "status": "failed",
            "supply_point_number": point,
            "output": str(output) if output else None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_reports(
    targets,
    report_month,
    get_session,
    load_sql_file,
    output_dir,
    *,
    workers=None,
    font=None,
    browser=None,
    bold_font=None,
    column_options=None,
    on_result=None,
):
    """既存バッチの対象リストから、CPU数のプロセスでPDFを作成する。

    Args:
        targets (Iterable[Mapping]): 指定年月・状態2/5で取得した軽い対象行。
        report_month (str | datetime.date): YYYY-MM、YYYYMMまたは対象月の日付。
        get_session (Callable): 子プロセス内で新規DBセッションを返す関数。
        load_sql_file (Callable): SQLを読み込む関数。どちらもモジュール直下で定義する。
        output_dir (str | pathlib.Path): 完成PDFの保存先。
        workers (int | None): 並列数。省略時はCPU数。
        font (str | pathlib.Path | None): 通常書体。
        browser (str | pathlib.Path | None): Chromium実行ファイル。
        bold_font (str | pathlib.Path | None): 太字書体。
        column_options (dict | None): 任意のSQL列対応・共通注記。
        on_result (Callable | None): 親で結果を受け取る既存のログ・状態更新処理。

    Returns:
        list[dict]: 完了順の成功・失敗結果。対象0件は空配列。

    Raises:
        ValueError: 対象年月・対象行・並列数が不正な場合。
    """
    from services.query_result_service import row_to_dict
    from services.report_job_source import normalize_report_ym

    if hasattr(report_month, "strftime"):
        report_month = report_month.strftime("%Y-%m")
    ym = normalize_report_ym(report_month)
    rows = [
        {str(name).lower(): value for name, value in row_to_dict(row).items()}
        for row in targets
    ]
    points = [row["supply_point_number"] for row in rows]
    if len(points) != len(set(points)):
        raise ValueError("指定対象年月の供給地点が重複しています")
    options = {
        "report_month": f"{ym[:4]}-{ym[4:]}",
        "output_dir": Path(output_dir).resolve(),
        "column_options": column_options or {},
        "font": font,
        "browser": browser,
        "bold_font": bold_font,
    }
    results = []
    for result in run_parallel(
        rows,
        _run_report,
        workers=workers,
        initializer=_initialize_reports,
        initargs=(get_session, load_sql_file, options),
    ):
        results.append(result)
        if on_result is not None:
            on_result(result)
    return results
