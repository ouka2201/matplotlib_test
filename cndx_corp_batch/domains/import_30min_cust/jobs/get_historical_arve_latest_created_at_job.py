from datetime import date

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.domains.repository.historical_arve_customer_info_repository import (
    THistoricalArveCustomerInfoRepository,
)
from cndx_corp_batch.jobs.base import BaseJob


class GetHistoricalArveLatestCreatedAtJob(BaseJob):
    """過去分ARVEお客さま情報最新取得年月取得JOB

    Args:
        BaseJob (BaseJob)
    """

    def __init__(self, context: BatchContext):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
        """
        super().__init__(context)
        self.context = context

    def execute(self) -> date:
        """過去分ARVEお客さま情報最新取得年月取得実行

        Returns:
            str: 過去分ARVEお客さま情報最新取得年月取得(YYYYMM)
        """
        logger = self.logger

        logger.info("過去分ARVEお客さま情報最新取得年月取得処理開始...")

        with get_session() as session:
            repo = THistoricalArveCustomerInfoRepository(session)
            latest_acquisition_year_month = repo.get_latest_acquisition_year_month()

        logger.info(
            f"過去分ARVEお客さま情報最新取得年月取得処理完了。最新取得年月：{latest_acquisition_year_month}"
        )

        return latest_acquisition_year_month
