"""
認証初期化API

認証方式（SAML/通常ログイン）を判定し、適切な認証フローを開始します。
"""

from flask import current_app, jsonify, request
from flask.views import MethodView

from cndx_corp_back.common.decorators import controller
from cndx_corp_back.utils.utils import get_message

from . import auth_bp


class AuthInitApi(MethodView):
    """
    認証初期化API

    認証方式を判定し、適切な認証フローを開始します。
    """

    @controller
    def get(self, dict_request_data, logger=None):
        """
        認証初期化処理

        認証フローを返します。
        SMAL認証はGatewayにて処理されるため、常に"auth/signin"を返すようにします。

        Returns:
            Response:
            - {"message": "auth/signin"}
        """
        if logger is None:
            logger = current_app.logger

        logger.info("認証初期化処理開始")

        if request.method == "OPTIONS":
            return jsonify({"message": get_message("OK")}), 200

        return jsonify({"message": "auth/signin"}), 200


# エンドポイント登録
auth_init_view = AuthInitApi.as_view("auth_init_api")
auth_bp.add_url_rule("/auth_init", view_func=auth_init_view, methods=["GET"])
