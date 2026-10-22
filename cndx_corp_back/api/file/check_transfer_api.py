import os
import tempfile

from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.file import file_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.file.check_transfer_service import FileCheckTransferService


class FileCheckTransferApi(MethodView):

    @jwt_required()
    @controller
    def post(self, dict_request_data, logger=None):

        # ファイル又はbase64データを格納する変数
        input = None
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # リクエストにファイルが含まれているか確認
        if "file" in request.files:

            file = request.files["file"]

            # ファイルが選択されているか確認
            if file.filename == "":
                return (
                    jsonify({"error_message_list": "ファイルが選択されていません。"}),
                    400,
                )

        # サービスを呼び出す
        message_list = FileCheckTransferService().execute(
            file=file, dict_request_data=dict_request_data, logger=logger
        )

        response = {
            # "path": path,
            # "file_name": file_name,
            "error_message_list": message_list
        }
        if message_list:
            return jsonify(response), 400

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(response), 200


file_view = FileCheckTransferApi.as_view("check_transfer_api")
file_bp.add_url_rule("/check-transfer", view_func=file_view, methods=["POST"])
