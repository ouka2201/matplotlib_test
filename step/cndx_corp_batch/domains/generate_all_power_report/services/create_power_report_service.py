import logging
import logging.handlers
import os
from multiprocessing.util import Finalize
from pathlib import Path

from sqlalchemy import text

from cndx_corp_batch.common.db import close_db, get_session, init_db
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import get_current_time
from cndx_corp_batch.common.utils import get_sysuser

from .data_service import bounds
from .database_source import NumericConversionError
from .query_result_service import prepare_query_results
from .report_service import ReportService

_report_service = None
_SQL_QUERIES = {}
OUTPUT_PATH = "/bd-fs-mnt/TenantShare/corp/electricity_vis_middle/power_report"


def close_worker():
    """ワーカーが所有するブラウザーとDB接続プールを終了する。"""
    global _report_service
    try:
        if _report_service is not None:
            _report_service.close()
    finally:
        _report_service = None
        close_db()


def multiprocessing_initializer(db_url, queue):
    """子プロセスが起動した瞬間に1度だけ走る初期化処理"""
    global _report_service
    init_db(db_url)

    _SQL_QUERIES["select_cust"] = text(load_sql_file("select_power_report_cust.sql"))
    _SQL_QUERIES["select_30min"] = text(load_sql_file("select_power_report_30min.sql"))
    _SQL_QUERIES["update_target"] = text(
        load_sql_file("update_power_report_target.sql")
    )
    _report_service = ReportService()
    Finalize(None, close_worker, exitpriority=10)

    queue_handler = logging.handlers.QueueHandler(queue)
    logger = logging.getLogger("batch.worker")
    logger.handlers = [queue_handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False


def execute(row, report_ym):
    logger = logging.getLogger("batch.worker")

    supply_point_number = row.supply_point_number
    report_ym_str = report_ym.strftime("%Y%m")
    company_id = row.company_id
    current_time = get_current_time()

    logger.info(f"{supply_point_number} レポート作成処理開始...")

    params = {
        "supply_point_number": supply_point_number,
    }
    # 契約情報設定(ARVEお客さま情報,EPデータ参照基盤契約電力)
    with get_session() as session:
        customer = dict(
            session.execute(_SQL_QUERIES["select_cust"], params).mappings().one()
        )

    start_date, end_date, _ = bounds(report_ym_str)

    params = {
        "supply_point_number": supply_point_number,
        "start_date": start_date.strftime("%Y%m%d"),
        "end_date": end_date.strftime("%Y%m%d"),
    }

    # グラフ用データ取得・変換(EPデータ参照基盤30分値から1年分の30分値を取得する。)
    with get_session() as session:
        daily_rows = (
            session.execute(_SQL_QUERIES["select_30min"], params).mappings().all()
        )

    file_name = (
        f"{company_id}_{supply_point_number}_syousapo_{report_ym_str}.pdf"
        if row.syousapo_flg
        else f"{company_id}_{supply_point_number}_{report_ym_str}.pdf"
    )

    output = Path(os.getenv("REPORT_OUTPUT_DIR", OUTPUT_PATH), file_name)

    update_params = {
        "file_name": file_name,
        "report_created_at": current_time,
        "create_status": "3",
        "file_path": str(output),
        "error_message": "",
        "updated_by": get_sysuser(),
        "updated_at": current_time,
        "supply_point_number": supply_point_number,
        "target_year_month": report_ym_str,
    }

    try:
        frame, config = prepare_query_results(
            customer, daily_rows, supply_point_number, report_ym_str
        )
        _report_service.generate_frame(
            df=frame,
            config=config,
            output=output,
            debug_dir=None,
        )

    except NumericConversionError as exc:
        update_params["error_message"] = str(exc)[:100]
        update_params["create_status"] = "4"
        logger.warning(
            "LMMRCRC0401 %s 主キー=%s 列=%s 供給地点=%s 対象年月=%s",
            exc, exc.primary_key, exc.column, supply_point_number, report_ym_str,
        )
    except Exception as exc:
        message = str(exc)
        update_params["error_message"] = message[:97] + "..." if len(message) > 100 else message
        update_params["create_status"] = "5"
        logger.exception(
            "レポート作成エラー 供給地点=%s 対象年月=%s",
            supply_point_number, report_ym_str,
        )

    with get_session() as session:
        session.execute(_SQL_QUERIES["update_target"], update_params)

    if update_params["create_status"] == "3":
        logger.info("%s レポート作成処理完了。", supply_point_number)
