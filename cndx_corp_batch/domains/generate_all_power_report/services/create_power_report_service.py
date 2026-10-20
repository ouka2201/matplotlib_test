import logging
import logging.handlers
import os
from multiprocessing.util import Finalize
from pathlib import Path
from typing import Any

from sqlalchemy import text

from cndx_corp_batch.common.db import close_db, get_session, init_db
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import get_current_time
from cndx_corp_batch.common.utils import get_sysuser

from .data_service import bounds
from .database_source_service import NumericConversionError
from .query_result_service import prepare_query_results
from .report_service import ReportService

_report_service = None
_SQL_QUERIES = {}
# バッチ処理内容定義書18・19：省サポの加入・未加入にかかわらず、
# 共通で使用するレポート出力先。
OUTPUT_PATH = "/bd-fs-mnt/TenantShare/corp/electricity_vis_middle/power_report"


def close_worker() -> Any:
    """ワーカーが所有するブラウザーとDB接続プールを終了する。"""
    global _report_service
    try:
        if _report_service is not None:
            _report_service.close()
    finally:
        _report_service = None
        close_db()


def multiprocessing_initializer(db_url: Any, queue: Any) -> Any:
    """LOOPの実装補足：各ワーカーでDB接続・SQL・PDF生成サービスを一度だけ準備する。"""
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


def execute(row: Any, report_ym: Any) -> Any:
    """処理6～26：1つの供給地点についてデータを取得し、帳票を作成して管理情報を更新する。

    数値に変換できない場合は4（完了（警告））、その他の生成失敗は5（エラー）として登録する。
    運用上、生成前のDB取得で発生した例外は親処理へ通知し、この関数では管理状態を変更しない。
    """
    logger = logging.getLogger("batch.worker")

    supply_point_number = row.supply_point_number
    report_ym_str = report_ym.strftime("%Y%m")
    company_id = row.company_id
    current_time = get_current_time()

    logger.info(f"{supply_point_number} レポート作成処理開始...")

    params = {
        "supply_point_number": supply_point_number,
    }
    # 処理6(1)／データ項目更新仕様説明書No.5：供給地点をキーに、
    # 名義・住所・番号・契約電力を取得する。
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

    # 処理7(1)／データ項目更新仕様説明書No.6：対象月を含む1年分の、
    # 取得年月日・48枠を取得する。
    with get_session() as session:
        daily_rows = (
            session.execute(_SQL_QUERIES["select_30min"], params).mappings().all()
        )

    # 処理17～19：管理情報の企業ID・供給地点・加入フラグから、
    # 省サポの加入状況に応じたPDF名を設定する。
    file_name = (
        f"{company_id}_{supply_point_number}_syousapo_{report_ym_str}.pdf"
        if row.syousapo_flg
        else f"{company_id}_{supply_point_number}_{report_ym_str}.pdf"
    )

    # 実装補足：ローカル実行時はREPORT_OUTPUT_DIRで設計書の出力先を上書きできる。
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
        # 処理7(2)～(4)・13(2)：48枠の数値・時刻変換と契約電力の数値変換を先に行う。
        frame, config = prepare_query_results(
            customer, daily_rows, supply_point_number, report_ym_str
        )
        # 処理6(2)・9～16・18～19：帳票No.0～7を描画し、PDFを保存する。
        _report_service.generate_frame(
            df=frame,
            config=config,
            output=output,
            debug_dir=None,
        )

    except NumericConversionError as exc:
        # 処理8・14・22～23／入力項目チェックNo.1～49：
        # PDF作成をスキップし、警告を記録する。
        update_params["error_message"] = str(exc)[:100]
        update_params["create_status"] = "4"
        logger.warning(
            "LMMRCRC0401 %s 主キー=%s 列=%s 供給地点=%s 対象年月=%s",
            exc,
            exc.primary_key,
            exc.column,
            supply_point_number,
            report_ym_str,
        )
    except Exception as exc:
        # 処理24～26／データ項目更新仕様説明書No.9：
        # 想定外のエラーの概要を100文字以内で記録する。
        message = str(exc)
        update_params["error_message"] = (
            message[:97] + "..." if len(message) > 100 else message
        )
        update_params["create_status"] = "5"
        logger.exception(
            "レポート作成エラー 供給地点=%s 対象年月=%s",
            supply_point_number,
            report_ym_str,
        )

    # 処理20・22・25／データ項目更新仕様説明書No.7～9：
    # 生成結果に応じて状態を3・4・5のいずれかに更新する。
    with get_session() as session:
        session.execute(_SQL_QUERIES["update_target"], update_params)

    if update_params["create_status"] == "3":
        logger.info("%s レポート作成処理完了。", supply_point_number)
