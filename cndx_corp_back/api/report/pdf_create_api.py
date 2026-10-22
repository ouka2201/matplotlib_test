import json
import os
import subprocess
import time
import traceback
import uuid
from urllib.parse import quote

import redis
from flask import abort, current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.dto.report.create_cn_karte_in_dto import CreateCnKarteInDto as InDto
from cndx_corp_back.service.report.pdf_create_service import (
    ReportPdfCreateService,
)
from cndx_corp_back.utils.utils import get_message


class ReportPdfCreateApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 入力チェック
        try:
            dto = InDto.model_validate(dict_request_data, by_name=True, by_alias=False)
        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}：チェックエラー：\n{e}")
            abort(400, description=str(e))

        # サービスを呼び出す
        user_id = user_context.get("user_id")
        login_org_id = user_context.get("org_id")
        report_location = ReportPdfCreateService().create_cn_report_bnk(
            dto, user_id, login_org_id, logger=logger
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"report_location": report_location}), 200


@report_bp.route("/pdf/output", methods=["POST", "OPTIONS"])
# @jwt_required()
def download_file():
    import io

    from flask import Response, request

    if request.method == "OPTIONS":
        return jsonify({"message": get_message("OK")}), 200

    logger = current_app.logger
    logger.info(f"{os.path.basename(__file__)}処理開始。")
    data = request.json
    if not data:
        return (
            jsonify(
                {"message": get_message("NOT_FOUND", item_name="リクエストデータ")}
            ),
            400,
        )

    hdfs_file_path = data["report_location"]
    logger.debug(f"hdfs_file_path★★{hdfs_file_path}")
    if not hdfs_file_path:
        return (
            jsonify({"error": get_message("REQUIRED", item_name="ファイルパス")}),
            400,
        )

    try:
        # HDFSからファイル内容を取得
        process = subprocess.run(
            ["hadoop", "fs", "-cat", hdfs_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        file_name = hdfs_file_path.split("/")[-1]  # ファイル名を取得
        encoded_filename = quote(file_name)

        # バイナリデータをレスポンスとして返す
        return Response(
            io.BytesIO(process.stdout),
            # process.stdout,
            # content_type='application/octet-stream',
            content_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"
            },
            # headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}",
            #          "Content-Type": "application/pdf"}
        )
    except subprocess.CalledProcessError as e:
        logger.error(traceback.format_exc())
        # return jsonify({"error": f"Failed to fetch file: {e.stderr.decode()}"}), 500
        return (
            jsonify(
                {
                    "error": "ダウンロードに失敗しました。"
                    "恐れ入りますが、時間をおいて再度お試しください。"
                }
            ),
            500,
        )


report_pdf_create_view = ReportPdfCreateApi.as_view("pdf_create_api")
report_bp.add_url_rule(
    "/cn-karte/create", view_func=report_pdf_create_view, methods=["POST"]
)
