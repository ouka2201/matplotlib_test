import os

from flask import abort, current_app, jsonify, request
from flask.views import MethodView
from pydantic import ValidationError

from cndx_corp_back.api.MSUS_UserInfoManagement import mst_user_info_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.MSUS_UserInfoManagement.user_search_info_service import (
    UserSearchInfoService,
)
from cndx_corp_back.utils.utils import get_message


class UserInfoSearchApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):
        """
        POST: ユーザー一覧検索処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            # サービスを呼び出す
            user_id = user_context.get("user_id")
            role_id = user_context.get("role")
            org_id = user_context.get("org_id")
            res = UserSearchInfoService().get_user_info(
                dict_request_data, user_id, role_id, org_id
            )

            logger.info(f"{os.path.basename(__file__)}処理終了。")
            return jsonify(res), 200

        except Exception as e:
            logger.error(f"データ取得エラー: {str(e)}")
            return (
                jsonify({"error": get_message("FAILURE", field="ユーザー一覧検索")}),
                500,
            )


# ルート登録
mst_user_search_info_view = UserInfoSearchApi.as_view("user_info_search_api")
mst_user_info_bp.add_url_rule(
    "/search/info", view_func=mst_user_search_info_view, methods=["POST"]
)
