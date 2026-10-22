import json
import os
import platform
import shutil
import subprocess
import time
import traceback
import uuid
from urllib.parse import quote

import redis
from flask import abort, current_app, jsonify, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import component, controller
from cndx_corp_back.common.utils import prepare_file_download_response
from cndx_corp_back.dto.report.create_cn_karte_in_dto import CreateCnKarteInDto as InDto
from cndx_corp_back.service.report.pdf_create_service import (
    ReportPdfCreateService,
)
from cndx_corp_back.utils.utils import get_message


class FileDownloadComponent:

    @component
    def execute(self, file_path, logger=None):
        logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        if file_path.startswith("dtap"):
            return self.dl_from_hdfs(file_path, logger)

        return self.dl_from_fs(file_path, logger)

    def dl_from_fs(self, file_path, logger=None):
        import io

        from flask import Response, request

        logger.info(f"ダウンロードファイルパス：{file_path}")

        lower_path = file_path.lower()
        if lower_path.endswith(".csv"):
            mimetype = "text/csv"
        elif lower_path.endswith(".pdf"):
            mimetype = "application/pdf"
        elif lower_path.endswith((".xlsx", ".xlsm", ".xls")):
            mimetype = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif lower_path.endswith(".docx"):
            mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif lower_path.endswith(".txt"):
            mimetype = "text/plain"
        elif lower_path.endswith(".zip"):
            mimetype = "application/zip"
        else:
            mimetype = "application/octet-stream"

        file_name = file_path.split("/")[-1]  # ファイル名を取得
        encoded_filename = quote(file_name)

        system = platform.system()
        if system == "Linux":
            try:

                # バイナリデータをレスポンスとして返す
                response = send_file(
                    file_path,
                    mimetype=mimetype,
                    as_attachment=False,  # True: download / False: ブラウザ内表示
                    download_name=encoded_filename,
                    conditional=True,  # Range対応（Chrome PDF Viewer対策）
                )
                return prepare_file_download_response(response, encoded_filename)
            except subprocess.CalledProcessError as e:
                logger.error(traceback.format_exc())
                return (
                    jsonify({"error": f"Failed to fetch file: {e.stderr.decode()}"}),
                    500,
                )

        elif system in ("Windows", "Darwin"):
            response = send_file(
                file_path,
                mimetype=mimetype,
                as_attachment=True,
                download_name=encoded_filename,
                conditional=True,
            )
            # 共通関数でレスポンスを準備
            return prepare_file_download_response(response, encoded_filename)
        else:
            logger.error(f"サポートされていないOSです: {system}")
            abort(500, description=f"サポートされていないOSです: {system}")

    def dl_from_hdfs(self, file_path, logger=None):
        import io

        from flask import Response, request

        logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        logger.info(f"ダウンロードファイルパス：{file_path}")

        lower_path = file_path.lower()
        if lower_path.endswith(".csv"):
            mimetype = "text/csv"
        elif lower_path.endswith(".pdf"):
            mimetype = "application/pdf"
        elif lower_path.endswith((".xlsx", ".xlsm", ".xls")):
            mimetype = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif lower_path.endswith(".docx"):
            mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif lower_path.endswith(".txt"):
            mimetype = "text/plain"
        elif lower_path.endswith(".zip"):
            mimetype = "application/zip"
        else:
            mimetype = "application/octet-stream"

        file_name = file_path.split("/")[-1]  # ファイル名を取得
        encoded_filename = quote(file_name)

        system = platform.system()
        if system == "Linux":
            try:
                # HDFSからファイル内容を取得
                process = subprocess.run(
                    ["hadoop", "fs", "-cat", file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )

                pdf_io = io.BytesIO(process.stdout)
                pdf_io.seek(0)

                # バイナリデータをレスポンスとして返す
                response = send_file(
                    pdf_io,
                    mimetype=mimetype,
                    as_attachment=False,  # True: download / False: ブラウザ内表示
                    download_name=encoded_filename,
                    conditional=True,  # Range対応（Chrome PDF Viewer対策）
                )
                return prepare_file_download_response(response, encoded_filename)
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

        elif system in ("Windows", "Darwin"):
            response = send_file(
                file_path,
                mimetype=mimetype,
                as_attachment=True,
                download_name=encoded_filename,
                conditional=True,
            )
            # 共通関数でレスポンスを準備
            return prepare_file_download_response(response, encoded_filename)
        else:
            logger.error(f"サポートされていないOSです: {system}")
            abort(500, description=f"サポートされていないOSです: {system}")
