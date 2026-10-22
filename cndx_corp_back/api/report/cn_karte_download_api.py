import os
import tempfile

from flask import Response, current_app, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.pdf_download_service import (
    CnKarteDownloadService,
)


class CnKarteDownloadApi(MethodView):

    # @jwt_required()
    @controller
    def get(self, dict_request_data, logger=None):

        # ファイル又はbase64データを格納する変数
        input = None
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # サービスを呼び出す
        file, file_name = CnKarteDownloadService().execute(
            request_dict=dict_request_data, logger=logger
        )

        # response = {"error_message_list": message_list}
        # if message_list:
        #     return jsonify(response), 400

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"file_base64": file, "file_name": file_name}), 200


pdf_download_view = CnKarteDownloadApi.as_view("cn_karte_download_api")
report_bp.add_url_rule(
    "/cn-karte-download", view_func=pdf_download_view, methods=["GET"]
)


# 直接ファイルダウンロードAPI（クラスの外）
@report_bp.route("/file/download", methods=["GET"])
def download_report_file():
    file_name = request.args.get("file_name")
    if not file_name:
        return Response("ファイル名が指定されていません", status=400)

    full_path = os.path.join("C:/HZY/FILE DOWNLOAD/PDF", file_name)
    if not os.path.isfile(full_path):
        return Response("ファイルが見つかりません", status=404)

    return send_file(full_path, as_attachment=True)
