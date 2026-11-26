from datetime import date

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.domains.repository.ep_contracted_power_repository import (
    TEpContractedPowerRepository,
)
from cndx_corp_batch.jobs.base import BaseJob


class GetEpPowerLatestCreatedAtJob(BaseJob):
    """EPデータ参照基盤契約電力最新作成日時取得JOB

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
        """EPデータ参照基盤契約電力最新作成日時取得実行

        Returns:
            date: EPデータ参照基盤契約電力最新作成日時
        """
        logger = self.logger

        logger.info("EPデータ参照基盤契約電力最新作成日時取得処理開始...")

        with get_session() as session:
            repo = TEpContractedPowerRepository(session)
            latest_create_at = repo.get_latest_create_at()

        logger.info(
            f"EPデータ参照基盤契約電力最新作成日時取得処理完了。最新日時：{latest_create_at}"
        )

        return latest_create_at
