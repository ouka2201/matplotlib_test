import traceback

from flask import jsonify

from cndx_corp_back.utils.utils import get_message

from .log import CorpLogger

# app = Flask(__name__)

logger = CorpLogger()


def register_error_handlers(app):
    # 正常なレスポンス（200 OK）
    @app.route("/success", methods=["GET"])
    def success():
        return jsonify({"message": get_message("OK")}), 200

    # 400 Bad Request のカスタムエラーハンドリング
    @app.errorhandler(400)
    def bad_request(error):
        logger.info(error)
        description = (
            error.description
            if hasattr(error, "description") and error.description
            else "The request is not valid"
        )

        if isinstance(description, list):
            normalized_messages = []
            for item in description:
                if isinstance(item, dict):
                    normalized_messages.append(
                        item.get("msg") or item.get("message") or str(item)
                    )
                else:
                    normalized_messages.append(str(item))
            message = normalized_messages
        elif isinstance(description, dict):
            message = [
                description.get("msg") or description.get("message") or str(description)
            ]
        else:
            message = description
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": message,
                }
            ),
            400,
        )

    # 404 Not Found のカスタムエラーハンドリング
    @app.errorhandler(404)
    def not_found(error):
        logger.info(error)
        message = (
            error.description
            if hasattr(error, "description") and error.description
            else "The requested resource was not found"
        )
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": message,
                }
            ),
            404,
        )

    # 409 Conflict のカスタムエラーハンドリング
    @app.errorhandler(409)
    def conflict(error):
        logger.info(error)
        message = (
            error.description
            if hasattr(error, "description") and error.description
            else "The request could not be completed due to a conflict"
        )
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": message,
                }
            ),
            409,
        )

    # 412 Precondition Failed のカスタムエラーハンドリング
    @app.errorhandler(412)
    def precondition_failed(error):
        logger.info(error)
        message = (
            error.description
            if hasattr(error, "description") and error.description
            else "The server does not meet one of the preconditions"
        )
        return (
            jsonify(
                {
                    "error": "Precondition Failed",
                    "message": message,
                }
            ),
            412,
        )

    # 500 Internal Server Error のカスタムエラーハンドリング
    @app.errorhandler(500)
    def internal_server_error(error):
        sys_error_msg = "システムエラーが発生しました。システム管理者にご連絡ください。"

        # --- 元例外を取得 ---
        orig = getattr(error, "original_exception", None)

        # error_content = str(error)
        # logger.error(f"Tableau ServerResponseError: {error_content}")

        # # 409093: リソースコンフリクト
        # if "409093" in error_content or "is already queued" in error_content:
        #     return jsonify({
        #         "error": "Resource Conflict",
        #         "message": "他のユーザーがレポートを印刷中です。しばらくしてから再度お試しください。",
        #         "error_code": "409093"
        #     }), 409

        if orig:
            error_type = type(orig).__name__
            error_msg = str(orig)
            message = f"{error_type}: {error_msg}"
        else:
            # 元例外がない場合 = HTTPException 等
            if hasattr(error, "description") and error.description:
                message = f"{sys_error_msg}{str(error.description).strip()}"
            else:
                message = sys_error_msg

        logger.error(message)
        return jsonify({"error": "Internal Server Error", "message": message}), 500

    # すべての未知のエラーをキャッチして 500 Internal Server Error を返す
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # error_trace = traceback.format_exc()
        # logger.error(f"Unexpected error: {error}\n{error_trace}")
        return internal_server_error(error)

    # データベースエラーのエラーハンドラー
    # @app.errorhandler(SQLAlchemyError)
    # def handle_database_error(error):
    #     db.session.rollback()  # エラー時にトランザクションをロールバック
    #     return internal_server_error(error)
