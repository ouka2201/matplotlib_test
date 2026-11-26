from datetime import date

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.domains.repository.arve_customer_info_repository import (
    TArveCustomerInfoRepository,
)
from cndx_corp_batch.jobs.base import BaseJob


class GetArveLatestCreatedAtJob(BaseJob):
    """ARVEお客さま情報最新作成日時取得JOB

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
        """ARVEお客さま情報最新作成日時取得実行

        Returns:
            date: ARVEお客さま情報最新作成日時
        """
        logger = self.logger

        logger.info("ARVEお客さま情報最新作成日時取得処理開始...")

        with get_session() as session:
            repo = TArveCustomerInfoRepository(session)
            latest_create_at = repo.get_latest_create_at()

        logger.info(
            f"ARVEお客さま情報最新作成日時取得処理完了。最新日時：{latest_create_at}"
        )

        return latest_create_at
