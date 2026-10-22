# cndx_corp_back/api/report/power_report_download_api.py

import os

from flask import current_app, jsonify, request
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.power_report_download_service import (
    PowerReportDownloadService,
)


class PowerReportDownloadApi(MethodView):
    @controller
    def get(self, dict_request_data, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(
            f"{os.path.basename(__file__)} – 電力見える化レポートダウンロード処理開始"
        )

        # サービス呼び出し
        file_base64 = PowerReportDownloadService().execute(
            request_dict=dict_request_data, logger=logger
        )

        logger.info(f"{os.path.basename(__file__)} – ダウンロード処理正常終了")
        return jsonify({"file_base64": file_base64}), 200


# ルーティング登録
power_report_download_view = PowerReportDownloadApi.as_view("power_report_download_api")
report_bp.add_url_rule(
    "/power-report/download", view_func=power_report_download_view, methods=["GET"]
)
