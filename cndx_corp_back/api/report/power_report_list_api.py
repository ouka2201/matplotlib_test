import os
import traceback
from typing import Any, Dict

from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.report.power_report_list_service import (
    PowerReportListService,
)


class PowerReportListApi(MethodView):
    """
    GET /api/report/power-report/list
    指定された法人番号や年度などで「電力見える化レポート」の一覧を取得。
    """

    # @jwt_required()
    @jwt_user_context_db(refresh=False)
    @controller
    def get(self, dict_request_data: Dict[str, Any], user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 電力レポート一覧取得開始")

        org_id = user_context.get("org_id")
        try:
            result = PowerReportListService().get_power_report_list(
                request_dict=dict_request_data,
                user_context=user_context,
            )

            logger.info(f"{os.path.basename(__file__)} 電力レポート一覧取得完了")
            return jsonify({"power_report_list": result}), 200

        except Exception as exc:
            logger.error(f"電力レポート一覧取得失敗: {exc}")
            logger.debug(traceback.format_exc())
            return jsonify({"error": "サーバーエラーが発生しました"}), 500


# ルーティング登録
power_report_list_view = PowerReportListApi.as_view("power_report_list_api")
# -> /api/report/power-report/list
report_bp.add_url_rule(
    "/power-report/list", view_func=power_report_list_view, methods=["GET"]
)
