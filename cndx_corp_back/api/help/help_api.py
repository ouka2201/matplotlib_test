import os
import platform
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

from flask import abort, current_app, jsonify, request, send_file
from flask.views import MethodView
from werkzeug.exceptions import NotFound

from cndx_corp_back.api.help import help_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.common.utils import prepare_file_download_response
from cndx_corp_back.service.file.fsMount_file_check_service import (
    FsMountFileCheckService,
)
from cndx_corp_back.service.file.fsMount_file_download_service import (
    FsMountFileDownloadService,
)


class HelpApi(MethodView):
    """
    ヘルプファイル取得API
    storageから静的ファイルを取得する
    """

    # エンドポイントとファイルパスのマッピング
    # 実際のファイルパスは環境に応じて設定してください
    ENDPOINT_FILE_MAP = {
        "/api/help/manual_EP": "/bd-fs-mnt/TenantShare/corp/help/LecMoc_Manual_EP.pdf",
        "/api/help/manual_TCS": "/bd-fs-mnt/TenantShare/corp/help/LecMoc_Manual_TCS.pdf",
        "/api/help/manual_REP": "/bd-fs-mnt/TenantShare/corp/help/LecMoc_Manual_REP.pdf",
        "/api/help/manual_financial": "/bd-fs-mnt/TenantShare/corp/help/LecMoc_Manual_Financial.pdf",
        "/api/help/consent_form_EP": "/bd-fs-mnt/TenantShare/corp/help/Data_Consent_Form_EP.docx",
        "/api/help/consent_form_REP": "/bd-fs-mnt/TenantShare/corp/help/Data_Consent_Form_REP.docx",
        "/api/help/consent_form_financial": "/bd-fs-mnt/TenantShare/corp/help/Data_Consent_Form_Financial.docx",
    }

    # 英語表記のファイル名を日本語表記に変換するマッピング
    FILENAME_EN_TO_JA_MAP = {
        "LecMoc_Manual_EP.pdf": "LecMocマニュアル_EP.pdf",
        "LecMoc_Manual_TCS.pdf": "LecMocマニュアル_TCS.pdf",
        "LecMoc_Manual_REP.pdf": "LecMocマニュアル_REP.pdf",
        "LecMoc_Manual_Financial.pdf": "LecMocマニュアル_金融機関.pdf",
        "Data_Consent_Form_EP.docx": "データ提供同意書（ミドル）_EP.docx",
        "Data_Consent_Form_REP.docx": "データ提供同意書（ミドル）_REP.docx",
        "Data_Consent_Form_Financial.docx": "データ提供同意書_金融機関.docx",
    }

    @staticmethod
    def convert_filename_to_japanese(english_filename: str) -> str:
        """
        英語表記のファイル名を日本語表記に変換する

        Args:
            english_filename: 英語表記のファイル名（例: "LecMoc_Manual_EP.pdf"）

        Returns:
            日本語表記のファイル名（例: "LecMocマニュアル_EP.pdf"）
            マッピングに存在しない場合は元のファイル名をそのまま返す
        """
        return HelpApi.FILENAME_EN_TO_JA_MAP.get(english_filename, english_filename)

    @jwt_user_context_db()
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):
        """
        storageから静的ファイルを取得
        エンドポイントで分岐してファイルパスを決定
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # リクエストパスからエンドポイントを取得
        endpoint = request.path
        logger.info(f"リクエストエンドポイント: {endpoint}")

        # エンドポイントに対応するファイルパスを取得
        file_path = self.ENDPOINT_FILE_MAP.get(endpoint)
        if not file_path:
            logger.error(f"未定義のエンドポイント: {endpoint}")
            abort(404, description=f"エンドポイントが見つかりません: {endpoint}")

        logger.info(f"取得対象ファイルパス: {file_path}")

        # ローカル実行環境かどうかを判定（config.pyの設定を使用）
        is_local_env = self._is_local_environment()

        # OSを取得
        system = platform.system()

        # ①ローカル環境（localhost）の場合、Windows/Mac/Linuxの環境でローカル取得
        if is_local_env:
            logger.info(
                f"ローカル実行環境（OS: {system}）のため、local_data配下からファイルを取得します"
            )
            local_file_path = self._resolve_local_file_path(file_path)
            return self._send_local_file(local_file_path, logger)
        else:
            # ②ローカル環境でない場合
            if system == "Linux":
                # FsMountからファイルを取得
                logger.info(
                    f"[DEBUG] ダウンロード処理開始: file_path={file_path}, system={system}"
                )
                logger.info(f"FsMountからファイルを取得します: {file_path}")
                logger.info("[DEBUG] FsMountFileDownloadServiceを呼び出し")
                download_service = FsMountFileDownloadService()
                try:
                    response = download_service.execute(
                        file_path=file_path, logger=logger
                    )
                    logger.info("[DEBUG] FsMountFileDownloadService処理完了")

                    # レスポンスのファイル名を日本語表記に変換
                    english_filename = file_path.split("/")[-1]
                    japanese_filename = self.convert_filename_to_japanese(
                        english_filename
                    )
                    encoded_filename = quote(japanese_filename)
                    # レスポンスヘッダーを更新（prepare_file_download_responseの形式に合わせる）
                    if hasattr(response, "headers"):
                        # Content-DispositionヘッダーをRFC 5987形式で更新
                        content_disposition = (
                            f"attachment; filename*=UTF-8''{encoded_filename}"
                        )
                        response.headers["Content-Disposition"] = content_disposition
                    return response
                except NotFound:
                    # 404エラー（ファイルが見つからない）の場合、日本語ファイル名に変換
                    logger.error(f"FsMountファイルが見つかりません: {file_path}")
                    english_filename = file_path.split("/")[-1]
                    japanese_filename = self.convert_filename_to_japanese(
                        english_filename
                    )
                    abort(
                        404,
                        description=f"ファイルが見つかりません: {japanese_filename}",
                    )
            else:
                # Linux以外の環境（ありえないケース）: 例外を返す
                error_msg = f"本番/ステージング環境では{system}OSはサポートされていません。Linux環境でのみ動作します。"
                logger.error(error_msg)
                abort(500, description=error_msg)

    def _is_local_environment(self) -> bool:
        """
        config.pyの設定を使用してローカル実行環境かどうかを判定
        """
        try:
            flask_env = os.getenv("FLASK_ENV", "").lower()
            # FLASK_ENVが設定されていない、またはdevelopment/devの場合はローカル環境
            if flask_env in ("", "development"):
                return True

            # JWT_COOKIE_DOMAINがlocalhostの場合はローカル環境
            if hasattr(current_app, "config"):
                jwt_cookie_domain = current_app.config.get("JWT_COOKIE_DOMAIN", "")
                if jwt_cookie_domain == "localhost":
                    return True

            return False
        except Exception:
            # エラーが発生した場合は安全のためFalseを返す
            return False

    def _resolve_local_file_path(self, file_path: str) -> str:
        """
        HDFSパスの場合はlocal_data配下を指すパスを返却
        """
        if file_path.startswith("/bd-fs-mnt/"):
            file_name = file_path.split("/")[-1]
            current_dir = os.path.dirname(os.path.abspath(__file__))
            local_data_dir = os.path.join(current_dir, "local_data")
            if not os.path.isdir(local_data_dir):
                raise FileNotFoundError(
                    f"local_dataディレクトリが存在しません。パス: {local_data_dir}"
                )
            return os.path.join(local_data_dir, file_name)
        return file_path

    def _local_file_exists(self, file_path: str, logger) -> bool:
        """
        ローカル環境でファイルが存在するかを判定
        """
        try:
            local_file_path = self._resolve_local_file_path(file_path)
            exists = os.path.isfile(local_file_path) and os.access(
                local_file_path, os.R_OK
            )
            if not exists:
                logger.warning(
                    f"ローカルファイルが存在しないかアクセスできません: {local_file_path}"
                )
            return exists
        except Exception as e:
            logger.error(
                f"ローカルファイル存在チェックでエラーが発生しました: {str(e)}"
            )
            logger.error(traceback.format_exc())
            return False

    def _check_file_availability(self, file_path: str, logger) -> bool:
        """
        ファイルがダウンロード可能か判定
        """
        logger.info(f"[DEBUG] _check_file_availability開始: file_path={file_path}")

        is_local_env = self._is_local_environment()
        system = platform.system()
        logger.info(f"[DEBUG] is_local_env={is_local_env}, system={system}")

        if is_local_env:
            logger.info("[DEBUG] ローカル環境のため_local_file_existsを呼び出し")
            return self._local_file_exists(file_path, logger)

        if system != "Linux":
            logger.error(
                f"サポートされていないOSのためファイル確認に失敗しました: OS={system}"
            )
            return False

        # FsMountからファイル存在チェック
        logger.info(
            f"[DEBUG] サービス層（FsMountFileCheckService）を呼び出し: file_path={file_path}"
        )
        check_service = FsMountFileCheckService()
        result = check_service.execute(file_path=file_path, logger=logger)
        logger.info(f"[DEBUG] サービス層処理完了: result={result}")
        return result

    def _send_local_file(self, local_file_path: str, logger):
        """
        ローカルファイルをレスポンスとして返却
        FileDownloadComponentと同じレスポンス形式で返却する
        """
        if not os.path.isfile(local_file_path):
            logger.error(f"ローカルファイルが存在しません: {local_file_path}")
            english_filename = os.path.basename(local_file_path)
            japanese_filename = self.convert_filename_to_japanese(english_filename)
            abort(404, description=f"ファイルが見つかりません: {japanese_filename}")

        if not os.access(local_file_path, os.R_OK):
            logger.error(
                f"ローカルファイルへのアクセス権限がありません: {local_file_path}"
            )
            abort(403, description="ファイルへのアクセス権限がありません")

        # FileDownloadComponentと同じ形式でMIMEタイプを決定
        lower_path = local_file_path.lower()
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

        # FileDownloadComponentと同じ形式でファイル名をURLエンコード
        # 英語表記のファイル名を日本語表記に変換
        english_filename = os.path.basename(local_file_path)
        file_name = self.convert_filename_to_japanese(english_filename)
        encoded_filename = quote(file_name)

        # 304レスポンスを防ぐため、リクエストヘッダーから条件付きリクエストヘッダーを削除
        # Flaskのsend_fileはIf-Modified-SinceやIf-None-Matchがあると304を返す可能性がある
        from flask import request as flask_request

        if hasattr(flask_request, "headers"):
            if "If-Modified-Since" in flask_request.headers:
                flask_request.headers.pop("If-Modified-Since", None)
            if "If-None-Match" in flask_request.headers:
                flask_request.headers.pop("If-None-Match", None)

        # FileDownloadComponentと同じパラメータでsend_fileを呼び出す
        response = send_file(
            local_file_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=encoded_filename,
        )

        # 共通関数でレスポンスを準備
        return prepare_file_download_response(response, encoded_filename)


class HelpAvailabilityApi(MethodView):
    """
    ヘルプファイルのダウンロード可否を返却
    """

    @jwt_user_context_db()
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} availabilityチェック開始。")
        help_api = HelpApi()
        availability = {}

        # アプリケーションコンテキストを取得（スレッド間で共有するため）
        app = current_app._get_current_object()

        # 並列処理でファイル存在チェックを実行
        # 全ての結果をまとめて返却するため、全てのタスクが完了するまで待機
        with ThreadPoolExecutor(max_workers=len(HelpApi.ENDPOINT_FILE_MAP)) as executor:
            # 各ファイルチェックタスクを並列実行
            future_to_key = {
                executor.submit(
                    self._check_file_availability_with_context,
                    app,
                    help_api,
                    file_path,
                    logger,
                ): endpoint.split("/")[-1]
                for endpoint, file_path in HelpApi.ENDPOINT_FILE_MAP.items()
            }

            # 完了したタスクから順に結果を取得
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    availability[key] = future.result(timeout=5)
                except TimeoutError:
                    logger.error(
                        f"ファイル存在チェックがタイムアウトしました: key={key}"
                    )
                    availability[key] = False
                except Exception as e:
                    logger.error(
                        f"ファイル存在チェックでエラーが発生しました: key={key}, error={str(e)}"
                    )
                    logger.error(traceback.format_exc())
                    availability[key] = False

        logger.info(f"{os.path.basename(__file__)} availabilityチェック終了。")
        return jsonify(availability), 200

    @staticmethod
    def _check_file_availability_with_context(app, help_api, file_path, logger):
        """
        アプリケーションコンテキスト内でファイル存在チェックを実行
        """
        with app.app_context():
            return help_api._check_file_availability(file_path, logger)


# エンドポイントを登録（ENDPOINT_FILE_MAPに定義されたエンドポイントに合わせる）
help_view = HelpApi.as_view("help_api")

# マニュアル: EP
help_bp.add_url_rule("/manual_EP", view_func=help_view, methods=["GET"])

# マニュアル: TCS
help_bp.add_url_rule("/manual_TCS", view_func=help_view, methods=["GET"])

# マニュアル: REP
help_bp.add_url_rule("/manual_REP", view_func=help_view, methods=["GET"])

# マニュアル: 金融機関
help_bp.add_url_rule("/manual_financial", view_func=help_view, methods=["GET"])

# データ提供同意書: EP
help_bp.add_url_rule("/consent_form_EP", view_func=help_view, methods=["GET"])

# データ提供同意書: REP
help_bp.add_url_rule("/consent_form_REP", view_func=help_view, methods=["GET"])

# データ提供同意書: 金融機関
help_bp.add_url_rule("/consent_form_financial", view_func=help_view, methods=["GET"])

# ファイル可否チェック
availability_view = HelpAvailabilityApi.as_view("help_availability_api")
help_bp.add_url_rule("/availability", view_func=availability_view, methods=["GET"])
