import os
import tempfile

from flask import Response, abort, current_app, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.file import file_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.file.file_download_service import FileDownloadService
from cndx_corp_back.service.report.pdf_download_service import (
    CnKarteDownloadService,
)


class FileDownloadApi(MethodView):

    # @jwt_required()
    @jwt_user_context_db()
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):

        # ファイル又はbase64データを格納する変数
        input = None
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # --- file_name パラメータ必須 ---
        # file_path = request_dict.get("file_path", "").strip()
        file_path = request.args.get("file_path", "").strip()
        if not file_path:
            logger.error("file_path パラメータが不足しています")
            abort(400, description="file_path パラメータが不足しています")

        # サービスを呼び出す
        file_response = FileDownloadService().execute(
            file_path=file_path, logger=logger
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return file_response


file_download_view = FileDownloadApi.as_view("file_download_api")
file_bp.add_url_rule("/file-download", view_func=file_download_view, methods=["GET"])
