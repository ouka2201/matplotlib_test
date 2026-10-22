import os

from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.MSUS_UserInfoManagement import mst_user_info_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.MSUS_UserInfoManagement.user_related_info_search_service import (
    UserRelatedSearchInfoService,
)
from cndx_corp_back.utils.utils import get_message


class UserRelatedInfoSearchApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):
        """
        company_name: プルダウン用の企業名を取得
        branch_name: プルダウン用の支店名を取得
        user_role: プルダウン用のユーザー権限を取得
        user_status: プルダウン用のユーザーステータスを取得
        """
        url = request.path
        try:
            # サービスを呼び出す
            if logger is None:
                logger = current_app.logger
            logger.info(f"{os.path.basename(__file__)}処理開始。")
            user_id = user_context.get("user_id")
            role_id = user_context.get("role")
            org_id = user_context.get("org_id")

            if "company_name" in url:
                res = UserRelatedSearchInfoService().get_company_name_info(
                    dict_request_data, role_id, user_id
                )
                logger.info(f"{os.path.basename(__file__)}処理終了。")
                return jsonify({"result": res}), 200

            elif "branch_name" in url:
                res = UserRelatedSearchInfoService().get_branch_name_info(
                    dict_request_data
                )
                logger.info(f"{os.path.basename(__file__)}処理終了。")
                return jsonify({"result": res}), 200

            elif "user_role" in url:
                res = UserRelatedSearchInfoService().get_user_role_info(
                    dict_request_data
                )
                logger.info(f"{os.path.basename(__file__)}処理終了。")
                return jsonify({"result": res}), 200

            elif "user_status" in url:
                res = UserRelatedSearchInfoService().get_user_status_info(
                    dict_request_data
                )
                logger.info(f"{os.path.basename(__file__)}処理終了。")
                return jsonify({"result": res}), 200

        except Exception as e:
            logger.error(f"データ取得エラー: {str(e)}")
            return (
                jsonify({"error": get_message("FAILURE", field="プルダウン検索")}),
                500,
            )


# ルート登録
mst_user_related_search_info_view = UserRelatedInfoSearchApi.as_view(
    "user_related_info_search_api"
)

mst_user_info_bp.add_url_rule(
    "/search/company_name",
    view_func=mst_user_related_search_info_view,
    methods=["POST"],
)
mst_user_info_bp.add_url_rule(
    "/search/branch_name", view_func=mst_user_related_search_info_view, methods=["POST"]
)
mst_user_info_bp.add_url_rule(
    "/search/user_role", view_func=mst_user_related_search_info_view, methods=["POST"]
)
mst_user_info_bp.add_url_rule(
    "/search/user_status", view_func=mst_user_related_search_info_view, methods=["POST"]
)
