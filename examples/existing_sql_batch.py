"""既存のget_session/load_sql_fileを使う、SQL取得とPDF生成の組み込み例。"""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing
from pathlib import Path

from batch import cpu_workers, managed_report_filename
from services.data_service import bounds
from services.query_result_service import row_to_dict
from services.query_result_worker import (
    initialize_query_worker,
    render_query_result_job,
)
from services.report_job_source import normalize_report_ym
from sqlalchemy import text


def create_report_from_existing_sql(
    target,
    report_month,
    get_session,
    load_sql_file,
    pdf_pool,
    output_dir,
    column_options=None,
):
    """既存SQLで1件を取得し、PDF用プロセスへ取得結果だけを渡す。

    Args:
        target (Mapping | sqlalchemy.Row): supply_point_number、company_id、syousapo_flg。
        report_month (str | datetime.date): YYYY-MM/ YYYYMMまたは対象月の日付。
        get_session (Callable): スレッドごとに新しいDBセッションを返す既存関数。
        load_sql_file (Callable): ファイル名からSQL文字列を返す既存関数。
        pdf_pool (ProcessPoolExecutor): 初期化済みのPDF用プロセスプール。
        output_dir (str | pathlib.Path): 完成PDFの保存先。
        column_options (dict | None): 契約情報・日付・48枠の取得列設定と共通注記。

    Returns:
        dict: 1件のPDF生成結果。DB管理状態の更新は呼び出し元が行う。

    Raises:
        Exception: SQL取得・データ変換・PDF生成に失敗した場合。
    """
    # 親で取得した対象行は、接続を含まない辞書として扱う。
    target = {str(name).lower(): value for name, value in row_to_dict(target).items()}
    if hasattr(report_month, "strftime"):
        report_month = report_month.strftime("%Y-%m")
    report_ym = normalize_report_ym(report_month)
    month = f"{report_ym[:4]}-{report_ym[4:]}"
    point = target["supply_point_number"]
    filename = managed_report_filename(
        {
            "supply_point": point,
            "target_year_month": report_ym,
            "company_id": target["company_id"],
            "syousapo_flg": target["syousapo_flg"],
        }
    )

    with get_session() as session:
        sql = load_sql_file("select_power_report_cust.sql")
        # 名前で参照するためmappingsを使い、セッション内で通常の辞書へ変える。
        customer = dict(
            session.execute(text(sql), {"supply_point_number": point}).mappings().one()
        )

    start, end, _ = bounds(month)
    params = {
        "supply_point_number": point,
        "start_date": start.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
    }
    with get_session() as session:
        sql = load_sql_file("select_power_report_30min.sql")
        daily_rows = [
            dict(row) for row in session.execute(text(sql), params).mappings().all()
        ]

    payload = {
        **(column_options or {}),
        "customer_row": customer,
        "daily_rows": daily_rows,
        "supply_point": point,
        "report_month": month,
        "output": (Path(output_dir) / filename).resolve(),
    }
    # セッションを閉じてからPDF用プロセスへ渡す。完了まで待つので、
    # 全1000件の日別データを先に読み込まず、取得中のスレッド数に抑えられる。
    return pdf_pool.submit(render_query_result_job, payload).result()


def run_existing_sql_batch(
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
    """取得済み対象リストを1件ずつ、CPU数に応じて取得・PDF生成する。

    Args:
        targets (Iterable[Mapping]): 管理SQLで取得した軽い対象行の一覧。
        report_month (str | datetime.date): 検索に使った対象年月。
        get_session (Callable): 既存バッチの新規セッション取得関数。
        load_sql_file (Callable): 既存バッチのSQL読込関数。
        output_dir (str | pathlib.Path): 最終PDFの保存先。
        workers (int | None): DB取得スレッド数とPDF生成プロセス数。既定はCPU数。
        font (str | None): 通常書体のパス。
        browser (str | None): Chromiumのパス。
        bold_font (str | None): 太字書体のパス。
        column_options (dict | None): generate_query_results用の任意設定。
        on_result (Callable | None): 親で1件完了時に結果辞書を受け取る既存のログ・状態更新処理。

    Returns:
        list[dict]: 完了順の成功・失敗結果。0件の場合は空配列。

    Raises:
        ValueError: 並列数や対象行が不正、同じ供給地点が重複している場合。
    """
    targets = [
        {str(name).lower(): value for name, value in row_to_dict(row).items()}
        for row in targets
    ]
    points = [target["supply_point_number"] for target in targets]
    if len(points) != len(set(points)):
        raise ValueError("指定対象年月の供給地点が重複しています")
    count = cpu_workers() if workers is None else workers
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("workersは正の整数で指定してください")
    if not targets:
        return []
    count = min(count, len(targets))
    results = []
    # get_sessionやBaseJobを子へ渡さず、PDF用の入口はモジュール直下の関数にする。
    # Windows/spawnでも、DBエンジンやロガーをpickleする必要がない。
    with ProcessPoolExecutor(
        max_workers=count,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=initialize_query_worker,
        initargs=(font, browser, bold_font),
    ) as pdf_pool:
        with ThreadPoolExecutor(max_workers=count) as sql_pool:
            futures = {
                sql_pool.submit(
                    create_report_from_existing_sql,
                    target,
                    report_month,
                    get_session,
                    load_sql_file,
                    pdf_pool,
                    output_dir,
                    column_options,
                ): target
                for target in targets
            }
            for future in as_completed(futures):
                target = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        "status": "failed",
                        "error": f"{type(exc).__name__}: {exc}",
                        "output": None,
                    }
                result = {
                    **result,
                    "supply_point_number": target["supply_point_number"],
                }
                results.append(result)
                if on_result is not None:
                    on_result(result)
    return results
