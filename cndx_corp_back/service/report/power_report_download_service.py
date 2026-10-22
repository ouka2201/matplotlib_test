# cndx_corp_back/service/report/power_report_download_service.py

import base64
import os
from typing import Any, Dict

from flask import current_app

from cndx_corp_back.common.decorators import service


class PowerReportDownloadService:
    @service
    def execute(self, request_dict: Dict[str, Any], logger=None) -> str:
        if logger is None:
            logger = current_app.logger

        logger.info("PowerReportDownloadService: レポートBase64取得開始")

        file_name = request_dict.get("file_name", "").strip()
        if not file_name:
            raise ValueError("file_name パラメータが不足しています")

        file_path = os.path.join("C:/HZY/FILE DOWNLOAD/PDF", file_name)

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        with open(file_path, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode("utf-8")

        logger.info("PowerReportDownloadService: レポートBase64取得成功")
        return encoded_file
