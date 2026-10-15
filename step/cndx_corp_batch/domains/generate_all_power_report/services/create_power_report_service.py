import logging
from pathlib import Path

from sqlalchemy import text

from cndx_corp_batch.common.db import get_session, init_db
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import get_current_time
from cndx_corp_batch.common.utils import get_sysuser

from .data_service import bounds
from .report_service import ReportService

_report_service = None
_SQL_QUERIES = {}
OUTPUT_PATH = "/"
# OUTPUT_PATH = "/bd-fs-mnt/TenantShare/corp/electricity_vis_middle/power_report"


def multiprocessing_initializer(db_url, queue):
    """子プロセスが起動した瞬間に1度だけ走る初期化処理"""
    global _report_service
    init_db(db_url)

    _report_service = ReportService()
    _SQL_QUERIES["select_cust"] = text(load_sql_file("select_power_report_cust.sql"))
    _SQL_QUERIES["select_30min"] = text(load_sql_file("select_power_report_30min.sql"))
    _SQL_QUERIES["update_target"] = text(
        load_sql_file("update_power_report_target.sql")
    )

    queue_handler = logging.handlers.QueueHandler(queue)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(queue_handler)


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
        f"{company_id}_{supply_point_number}_{report_ym_str}.pdf"
        if row.syousapo_flg
        else f"{company_id}_{supply_point_number}_syousapo_{report_ym_str}.pdf"
    )

    output = Path(OUTPUT_PATH, file_name)

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

    from .query_result_service import prepare_query_results

    logger.info(f"A")

    try:
        frame, config = prepare_query_results(
            customer, daily_rows, supply_point_number, report_ym_str
        )
    except ValueError as e:
        err_msg = str(e)
        truncate_msg = err_msg[:97] + "..." if len(err_msg) > 100 else err_msg
        update_params["error_message"] = truncate_msg
        update_params["create_status"] = "4"
        with get_session() as session:
            session.execute(_SQL_QUERIES["update_target"], update_params)
            session.commit()

    except Exception as e:
        err_msg = str(e)
        truncate_msg = err_msg[:97] + "..." if len(err_msg) > 100 else err_msg
        update_params["error_message"] = truncate_msg
        update_params["create_status"] = "5"
        with get_session() as session:
            session.execute(_SQL_QUERIES["update_target"], update_params)
            session.commit()
    logger.info(f"B")
    try:
        # 最新の generate_frame を呼び出し
        _report_service.generate_frame(
            df=frame,
            config=config,
            output=output,
            debug_dir=None,
        )

        with get_session() as session:
            session.execute(_SQL_QUERIES["update_target"], update_params)
            session.commit()

        logger.info(f"{supply_point_number}レポート作成処理完了。")

    except ValueError as e:
        err_msg = str(e)
        truncate_msg = err_msg[:97] + "..." if len(err_msg) > 100 else err_msg
        update_params["error_message"] = truncate_msg
        update_params["create_status"] = "4"
        with get_session() as session:
            session.execute(_SQL_QUERIES["update_target"], update_params)
            session.commit()

    except Exception as e:
        err_msg = str(e)
        truncate_msg = err_msg[:97] + "..." if len(err_msg) > 100 else err_msg
        update_params["error_message"] = truncate_msg
        update_params["create_status"] = "5"
        with get_session() as session:
            session.execute(_SQL_QUERIES["update_target"], update_params)
            session.commit()
