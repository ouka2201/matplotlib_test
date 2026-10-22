# cndx_corp_back/api/report/power_report_target_months_api.py
import os
from typing import Any, Dict

from flask import current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.power_report_target_months_service import (
    PowerReportTargetMonthsService,
)


class PowerReportTargetMonthsApi(MethodView):
    """
    GET /api/report/power-report/options/months

    指定された拠点（building_id）と対象期間（start_year/start_month ～ end_year/end_month）で
    実際に電力データが存在する「対象月候補」を返す。
    返却フォーマット例：
    {
        "target_months": [
            { "value": "202412", "label": "2024年12月" },
            ...
        ]
    }
    """

    @controller
    def get(self, dict_request_data: Dict[str, Any], logger=None):
        # ───────────────────────────────
        # logger
        # ───────────────────────────────
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 処理開始")

        # ───────────────────────────────
        # Service 層に処理を委譲
        # ───────────────────────────────
        result_data = PowerReportTargetMonthsService().get_target_months(
            dict_request_data
        )

        logger.info(f"{os.path.basename(__file__)} 処理終了")
        return jsonify(result_data), 200


# ルーティング登録
power_report_target_months_view = PowerReportTargetMonthsApi.as_view(
    "power_report_target_months_api"
)
report_bp.add_url_rule(
    "/power-report/target-months",
    view_func=power_report_target_months_view,
    methods=["GET"],
)
