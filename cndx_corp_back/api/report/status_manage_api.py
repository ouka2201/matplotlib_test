import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.status_manage_service import StatusManageService


class StatusManageApi(MethodView):

    @jwt_required()
    @controller
    def get(self, dict_request_data, logger=None):

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # サービスを呼び出す
        report_info_list = StatusManageService().get_report_info(dict_request_data)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"report_info_list": report_info_list}), 200

    @controller
    def post(self, dict_request_data, logger=None):

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        message_list = list()

        response = {"message": message_list}

        # サービスを呼び出す
        StatusManageService().post_report_info(
            request_dict=dict_request_data, message_list=message_list, logger=logger
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(response), 200


report_manage_view = StatusManageApi.as_view("status_manage_api")
report_bp.add_url_rule("/status/inquiry", view_func=report_manage_view, methods=["GET"])
report_bp.add_url_rule("/status/update", view_func=report_manage_view, methods=["POST"])
