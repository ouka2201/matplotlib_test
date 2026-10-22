from flask import current_app, jsonify, request
from flask.views import MethodView

from ...common.decorators import controller
from ...service.user_management.user_management_service import (
    UserManagementService
)
from . import user_bp


class UserManagementController(MethodView):
    @controller
    def post(self, dict_request_data, logger=None):
        """
        ユーザ情報登録を処理する
        """
        if logger is None:
            logger = current_app.logger
        # サービスを呼び出す
        if request.path == "/api/user/insert":
            response = UserManagementService().execute_user_insert(dict_request_data)

        return jsonify(response), 200

# ビューを登録する
user_view = UserManagementController.as_view("user_controller")
# ユーザ登録
user_bp.add_url_rule("/insert", view_func=user_view, methods=["POST"])

