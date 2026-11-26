from datetime import date

from sqlalchemy import text

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.jobs.base import BaseJob


class GetRegularCustomersJob(BaseJob):
    """通常顧客30分値取得対象のリスト取得JOB

    Args:
        BaseJob (BaseJob)
    """

    def __init__(
        self,
        context: BatchContext,
        arve_historical_year_month: date,
        target_year_month: date,
    ):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
            arve_historical_year_month (date): 過去分ARVEお客さま情報年月
            target_year_month (date): レポート作成対象年月
        """
        super().__init__(context)
        self.context = context
        self.arve_historical_year_month = arve_historical_year_month
        self.target_year_month = target_year_month

    def execute(self):
        """通常顧客30分値取得対象のリスト取得実行

        Returns:
            list: 供給地点特定番号リスト
        """
        logger = self.logger

        logger.info("通常顧客30分値取得対象のリスト取得処理開始...")

        params = {
            "arve_historical_year_month": self.arve_historical_year_month.strftime(
                "%Y%m"
            ),
            "target_year_month": self.target_year_month.strftime("%Y%m"),
        }

        # 通常顧客30分値取得対象のリスト取得
        with get_session() as session:
            sql_query = load_sql_file("get_regular_customers.sql")
            result = session.execute(text(sql_query), params)
            supply_point_list = [row[0] for row in result]

        logger.info(
            f"通常顧客30分値取得対象のリスト取得処理完了。{len(supply_point_list)}件"
        )
        return supply_point_list
