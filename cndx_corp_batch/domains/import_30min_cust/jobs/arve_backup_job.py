from datetime import (
    date,
)

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.domains.import_30min_cust.services.arve_backup_service import (
    ArveBackupService,
)
from cndx_corp_batch.jobs.base import BaseJob


class ArveBackupJob(BaseJob):
    """ARVEお客さま情報バックアップJOB

    Args:
        BaseJob (BaseJob)
    """

    def __init__(self, context: BatchContext, historical_ymd: date):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
            historical_ymd (date): 過去分ARVEお客さま情報年月
        """
        super().__init__(context)
        self.context = context
        self.service = ArveBackupService(self.logger)
        self.historical_ymd = historical_ymd

    def execute(self):
        """バックアップ実行"""
        logger = self.logger

        logger.info("先月データバックアップ処理開始。")

        self.service.execute(self.historical_ymd)

        logger.info("先月データバックアップ処理完了。")
