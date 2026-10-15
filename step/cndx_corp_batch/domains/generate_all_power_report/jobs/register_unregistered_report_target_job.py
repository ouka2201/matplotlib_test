from sqlalchemy import text

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import get_current_time
from cndx_corp_batch.common.utils import get_sysuser
from cndx_corp_batch.jobs.base import BaseJob


class RegisterUnregisteredReportTargetJob(BaseJob):
    def __init__(self, context: BatchContext, target_year_month):
        super().__init__(context)
        self.context = context
        self.report_ym = target_year_month

    def execute(self):
        logger = self.logger

        logger.info("30分値データ取込確認処理開始。")

        params = {
            "user": get_sysuser(),
            "created_at": get_current_time(),
            "report_ym": self.report_ym.strftime("%Y%m"),
        }

        with get_session() as session:
            sql_query = load_sql_file("insert_unregistered_report_target.sql")
            session.execute(text(sql_query), params)

        logger.info("30分値データ取込確認処理完了。")
