import io
import os
from datetime import datetime
from pathlib import Path

from cndx_corp_batch.domains.common_services.file_upload_service import (
    FileUploadService,
)


class ReportFileUploadService:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def upload_pdf(
        self,
        corp_number: str,
        pdf_stream: io.BytesIO,
        pdf_file_name: str,
        repot_type_dir: str,
    ) -> str:
        pdf_temp_path: str | None = None

        try:
            today = datetime.now().strftime("%Y%m%d")
            target_dir = (
                f"/bd-fs-mnt/TenantShare/corp/{repot_type_dir}/{today}/{corp_number}"
            )
            os.makedirs(target_dir, exist_ok=True)

            upload_target_path = os.path.join(target_dir, pdf_file_name)

            with open(upload_target_path, "wb") as f:
                f.write(pdf_stream.getvalue())
            self.logger.info(f"upload_target_path: 【{upload_target_path}】")
            return upload_target_path
        finally:
            if pdf_temp_path and Path(pdf_temp_path).exists():
                Path(pdf_temp_path).unlink(missing_ok=True)
