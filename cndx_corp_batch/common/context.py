# app/context.py
import uuid

from cndx_corp_batch.common.config import BatchConfig
from cndx_corp_batch.common.db import close_db, init_db
from cndx_corp_batch.common.logger import BatchLogger
from cndx_corp_batch.common.tableau import TableauClient
from cndx_corp_batch.domains.common_services.file_upload_service import (
    FileUploadService,
)


class BatchContext:
    def __init__(self, config: BatchConfig):

        self.batch_id = str(uuid.uuid4())
        self.batch_name = config.batch_name
        self.config = config

        self.logger = BatchLogger(
            batch_id=self.batch_id,
            batch_name=self.batch_name,
        )

        self.tableau = TableauClient(config.tableau)
        self.file_upload = FileUploadService()

        init_db(config.db_url)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc:
            self.logger.exception("Batch failed", exc_info=exc)
        self.close()

    def close(self):
        close_db()
