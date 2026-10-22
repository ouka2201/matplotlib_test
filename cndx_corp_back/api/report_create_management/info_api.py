import os
import traceback

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report_create_management import report_create_management_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.contact_person.info_service import (
    ContactPersonInfoService,
)


class ReportManagementInfoApi(MethodView):

    # @jwt_required()
    @controller
    @jwt_user_context_db(refresh=False)
    def post(self, dict_request_data, user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        if dict_request_data.get("corporate_number"):
            dict_request_data["corporate_number"] = dict_request_data[
                "corporate_number"
            ].strip()
        if dict_request_data.get("company_name"):
            dict_request_data["company_name"] = dict_request_data[
                "company_name"
            ].strip()
        if dict_request_data.get("company_address"):
            dict_request_data["company_address"] = dict_request_data[
                "company_address"
            ].strip()

        # 担当者検索の共通処理
        user_id = user_context.get("user_id")
        role_id = user_context.get("role")
        org_type_code = user_context.get("org_type_code")
        org_id = user_context.get("org_id")
        res = ContactPersonInfoService().get_corpration_info(
            dict_request_data, user_id, role_id, org_type_code, org_id
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(res), 200


contact_person_info_view = ReportManagementInfoApi.as_view("info_api")
report_create_management_bp.add_url_rule(
    "/info/inquiry", view_func=contact_person_info_view, methods=["POST"]
)
