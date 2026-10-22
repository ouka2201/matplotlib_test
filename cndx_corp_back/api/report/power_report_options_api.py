# cndx_corp_back/api/report/power_report_options_api.py
import os
from typing import Any, Dict

from flask import current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.power_report_options_service import (
    PowerReportOptionsService,
)


class PowerReportOptionsApi(MethodView):
    """
    GET /api/report/power-report/options

    拠点候補・契約電力・対象月（acquisition_date の前6桁）など
    電力見える化レポート作成モーダルに必要な選択肢一式を返却する。
    """

    @controller
    def get(self, dict_request_data: Dict[str, Any], logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 処理開始")

        # Service 層に処理を委譲
        result_data = PowerReportOptionsService().get_options(dict_request_data)

        logger.info(f"{os.path.basename(__file__)} 処理終了")
        return jsonify(result_data), 200


# ルーティング登録
power_report_options_view = PowerReportOptionsApi.as_view("power_report_options_api")
report_bp.add_url_rule(
    "/power-report/options", view_func=power_report_options_view, methods=["GET"]
)
