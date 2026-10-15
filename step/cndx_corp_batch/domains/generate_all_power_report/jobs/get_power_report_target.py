from sqlalchemy import text

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.jobs.base import BaseJob


class GetPowerReportTarget(BaseJob):
    """処理4／データ項目更新仕様説明書No.4：レポート作成対象情報を取得する。"""
    def __init__(self, context: BatchContext, target_year_month):
        super().__init__(context)
        self.context = context
        self.report_ym = target_year_month

    def execute(self):
        """対象年月の状態2（作成中）・5（エラー）の供給地点・企業ID・加入フラグを返す。"""
        logger = self.logger

        logger.info("レポート作成対象情報取得処理開始...")

        params = {
            "report_ym": self.report_ym.strftime("%Y%m"),
        }

        with get_session() as session:
            sql_query = load_sql_file("select_power_report_target.sql")
            result = session.execute(text(sql_query), params).all()
            logger.info("レポート作成対象情報取得処理完了。")
            return result
