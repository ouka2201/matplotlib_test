import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from cndx_corp_back.api.corp import corp_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.corp.basic_info_service import CorpBasicInfoService


class CorpBasicInfoApi(MethodView):

    @jwt_user_context_db(refresh=False)
    # @jwt_required()
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        login_org_id = user_context.get("org_id")
        org_type_code = user_context.get("org_type_code")
        role_id = user_context.get("role")
        user_id = user_context.get("user_id")
        # サービスを呼び出す
        res = CorpBasicInfoService().get_corp_basic_info(
            dict_request_data, login_org_id, org_type_code, role_id, user_id
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"ok": True, "result_list": res}), 200

    # @jwt_required()
    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger

        # claims = get_jwt()

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # サービスを呼び出す
        CorpBasicInfoService().post_corp_basic_info(
            dict_request_data, user_context.get("user_id"), user_context.get("org_id")
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"ok": True}), 200


corp_basic_info__view = CorpBasicInfoApi.as_view("basic_info_api")
corp_bp.add_url_rule("/basic-info", view_func=corp_basic_info__view, methods=["GET"])
corp_bp.add_url_rule("/basic-info", view_func=corp_basic_info__view, methods=["POST"])
