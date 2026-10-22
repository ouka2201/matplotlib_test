import base64
import os
import re
from io import BytesIO

from flask import abort, current_app, jsonify, request
from flask.views import MethodView
from pydantic import ValidationError

from cndx_corp_back.api.FLUL_30m_data import per_30m_data_upload_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.dto.file.per30m_upload_in_dto import Per30mUploadInDto
from cndx_corp_back.service.FLUL_30m_data.FLUL_30_data_file import (
    Per30mDataFileService,
)
from cndx_corp_back.utils.utils import get_message

# from flask_jwt_extended import jwt_required


class Per30mDataFileApi(MethodView):

    # @jwt_required()
    @controller
    @jwt_user_context_db(refresh=False)
    def post(self, dict_request_data, user_context=None, logger=None):

        # ファイル又はbase64データを格納する変数
        if logger is None:
            logger = current_app.logger

        userid = user_context.get("user_id")

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # リクエストにファイルが含まれているか確認
        if "file" in request.files:

            file = request.files["file"]

            # ファイルが選択されているか確認
            if file.filename == "":
                return (
                    jsonify({"error_message_list": get_message("FILE_NOT_SELECT")}),
                    400,
                )
            content_type = file.headers.get("Content-Type", "")
            match = re.search(r"charset=([\w\-]+)", content_type, re.IGNORECASE)
            encoding = match.group(1) if match else "utf-8"
            file_stream = file.stream
        else:
            try:
                base64_result = dict_request_data["file_data"].split(",")[-1]
                decoded = base64.b64decode(base64_result)
                file_stream = BytesIO(decoded)
                encoding = "utf-8"
            except Exception as e:
                return (
                    jsonify({"error_message_list": get_message("FILE_NOT_EXIST")}),
                    400,
                )

        try:
            dto = Per30mUploadInDto.model_validate(dict_request_data)
        except ValidationError as e:
            abort(400, description=e.errors())

        # サービスを呼び出す
        message_list = Per30mDataFileService().upload_30m_data_file(
            file=file_stream, encoding=encoding, dto=dto, userid=userid, logger=logger
        )

        response = {"message": message_list}
        if message_list:
            return jsonify(response), 400

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"ok": True}), 200


per_30m_data_upload_view = Per30mDataFileApi.as_view("30m_file_api")
per_30m_data_upload_bp.add_url_rule(
    "", view_func=per_30m_data_upload_view, methods=["POST"]
)
