import os
import traceback
from urllib.parse import quote

from flask import Response, abort, current_app, jsonify, send_file

from cndx_corp_back.common.decorators import component
from cndx_corp_back.common.utils import prepare_file_download_response


class FsMountFileDownloadComponent:

    @component
    def execute(self, file_path: str, logger=None) -> Response:
        """
        FsMountからファイルをダウンロードする
        osライブラリを使用してファイルサーバのパスを参照
        """
        if logger is None:
            logger = current_app.logger

        logger.info(
            f"[DEBUG] FsMountFileDownloadComponent.execute開始: file_path={file_path}"
        )
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        logger.info(f"ダウンロードファイルパス：{file_path}")

        # ファイルが存在するかチェック
        logger.info(f"[DEBUG] ファイル存在チェック実行: file_path={file_path}")
        if not os.path.isfile(file_path):
            logger.error(f"FsMountファイルが存在しません: {file_path}")
            abort(
                404,
                description=f"ファイルが見つかりません: {os.path.basename(file_path)}",
            )

        # ファイルへのアクセス権限をチェック
        logger.info(f"[DEBUG] ファイルアクセス権限チェック実行: file_path={file_path}")
        if not os.access(file_path, os.R_OK):
            logger.error(f"FsMountファイルへのアクセス権限がありません: {file_path}")
            abort(403, description="ファイルへのアクセス権限がありません")

        # MIMEタイプを決定
        logger.info("[DEBUG] MIMEタイプ決定処理開始")
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
        logger.info(f"[DEBUG] MIMEタイプ決定: mimetype={mimetype}")

        # ファイル名を取得
        file_name = os.path.basename(file_path)
        encoded_filename = quote(file_name)
        logger.info(
            f"[DEBUG] ファイル名エンコード: file_name={file_name}, encoded_filename={encoded_filename}"
        )

        try:
            # ファイルを送信
            logger.info("[DEBUG] send_file実行開始")
            response = send_file(
                file_path,
                mimetype=mimetype,
                as_attachment=True,
                download_name=encoded_filename,
            )
            logger.info("[DEBUG] send_file実行完了")

            # 共通関数でレスポンスを準備
            logger.info("[DEBUG] prepare_file_download_response実行開始")
            result = prepare_file_download_response(response, encoded_filename)
            logger.info("[DEBUG] prepare_file_download_response実行完了")
            logger.info("[DEBUG] FsMountFileDownloadComponent.execute終了")
            return result
        except Exception as e:
            logger.error(
                f"FsMountファイルダウンロード処理でエラーが発生しました: {str(e)}"
            )
            logger.error(traceback.format_exc())
            # return jsonify({"error": f"Failed to fetch file: {str(e)}"}), 500
            return (
                jsonify(
                    {
                        "error": "ダウンロードに失敗しました。"
                        "恐れ入りますが、時間をおいて再度お試しください。"
                    }
                ),
                500,
            )
