# cndx_corp_back/service/report/power_report_download_service.py

import mimetypes
import os
from typing import Any, Dict

from flask import (
    Blueprint,
    Response,
    abort,
    stream_with_context,
)
from werkzeug.utils import safe_join

from cndx_corp_back.common.decorators import service

files_bp = Blueprint("files", __name__)


class PowerReportContactDownloadService:
    @service
    def execute(self, filename: str, logger=None):
        # 開発
        storage_path = (
            "/bd-fs-mnt/TenantShare/corp/electricity_vis_middle/user_power_report/"
        )
        # ローカル
        # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        # storage_path = os.path.join(BASE_DIR, "..", "report", "storage")
        # storage_path = os.path.abspath(storage_path)

        file_path = safe_join(storage_path, filename)

        if not file_path or not os.path.isfile(file_path):
            abort(404)

        mime_type, _ = mimetypes.guess_type(file_path)

        @stream_with_context
        def generate():
            with open(file_path, "rb") as file_handle:
                while True:
                    chunk = file_handle.read(64 * 1024)
                    if not chunk:
                        break

                    yield chunk

        response = Response(
            generate(), mimetype=mime_type or "application/octet-stream"
        )
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{os.path.basename(file_path)}"'
        )
        response.content_length = os.path.getsize(file_path)
        logger.info("PowerReportContactDownloadService: レポート取得成功")
        return response
