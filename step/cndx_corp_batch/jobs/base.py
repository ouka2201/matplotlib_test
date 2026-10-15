# jobs/base.py
import inspect
import logging
import logging.handlers
import multiprocessing
import os
from abc import ABC, abstractmethod
from datetime import datetime

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.job_logger import JobLogger
from cndx_corp_batch.domains.common_services.file_upload_service import (
    FileUploadService,
)

# from sqlalchemy import inspect


class BaseJob(ABC):
    """
    バッチ内 Job の基底クラス
    """

    def __init__(self, context: BatchContext):
        """
        Args:
            context: BatchContext
        """
        self.context = context
        self.job_name: str = self._resolve_job_name()

        base_logger = context.logger.logger
        base_extra = dict(context.logger.extra)

        base_extra.update(
            {
                "job_name": self.job_name,
            }
        )

        self.logger = logging.LoggerAdapter(
            base_logger,
            base_extra,
        )

    def _resolve_job_name(self) -> str:
        """
        所属ファイル名（拡張子なし）を job_name とする
        """
        file_path = inspect.getfile(self.__class__)
        return os.path.splitext(os.path.basename(file_path))[0]

    def run(self, *args, **kwargs):
        start_at = datetime.now()

        self._log_start()

        try:
            result = self.execute(*args, **kwargs)

            self._log_success(start_at)
            return result

        except Exception as e:
            self._log_error(start_at, e)
            raise

    @abstractmethod
    def execute(self):
        """
        Job 固有処理
        """
        pass

    # --------------------
    # 共通処理
    # --------------------

    def _log_start(self):
        self.logger.info(f"[START] job={self.job_name}", extra=self._log_extra())

    def _log_success(self, start_at):
        elapsed = (datetime.now() - start_at).total_seconds()
        self.logger.info(
            f"[SUCCESS] job={self.job_name} elapsed={elapsed:.2f}s",
            extra=self._log_extra(),
        )

    def _log_error(self, start_at, error):
        elapsed = (datetime.now() - start_at).total_seconds()
        self.logger.error(
            f"[ERROR] job={self.job_name} elapsed={elapsed:.2f}s error={error}",
            extra=self._log_extra(),
            exc_info=True,
        )

    def _log_extra(self):
        """
        ログ共通メタ情報
        """
        return {
            "batch_id": self.context.batch_id,
            "batch_name": self.context.batch_name,
            "job_name": self.job_name,
        }
