"""
ユーザー情報初期化API

SAML認証成功後、Flask sessionからname_idを取得し、
ユーザーバリデーション、セッションID発行、最終ログイン登録・更新を行う
"""

import datetime
import json
import os

import jwt
from flask import current_app, jsonify, request
from flask import session as flask_session
from flask.views import MethodView
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt_identity,
    set_access_cookies,
    set_refresh_cookies,
    verify_jwt_in_request,
)

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.common.load_master import mst_data

from . import auth_bp
from .util import (
    complete_login_process,
    process_user_login,
)


class UserInfoInitApi(MethodView):
    """
    ユーザー情報初期化API

    SAML認証成功後、ユーザー情報を初期化し、JWTトークンを発行します。
    """

    @controller
    def get(self, dict_request_data, logger=None):
        """
        ユーザー情報を初期化し、JWTトークンを発行

        Returns:
            Response: JWTトークンを含むレスポンス
        """
        if logger is None:
            logger = current_app.logger

        logger.info("ユーザー情報初期化処理開始")

        try:
            # cookies(jwt)からname_idを取得
            name_id = None
            refresh_token = request.cookies.get("refresh_token_cookie")
            token = request.cookies.get("saml_jwt_token")

            if refresh_token and not token:
                decoded = decode_token(refresh_token)
                name_id = decoded.get("sub")

            if not name_id and token:

                pubkey = current_app.config.get("REVERPROXY_JWT_PUBLIC_KEY", "")
                try:
                    payload = jwt.decode(
                        token,
                        pubkey,
                        algorithms=["RS256"],
                        audience="sp",
                        issuer="authgateway",
                    )
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                name_id = payload["sub"]

            if not name_id:
                logger.error(
                    f"ログインユーザの情報取得が失敗しました。errocode: 401", auth=True
                )
                return (
                    jsonify(
                        {
                            "message": "認証情報が見つかりません。再度ログインしてください。"
                        }
                    ),
                    401,
                )
            logger.info(f"jwtからname_idを取得: {name_id}")
            # データベースからユーザー情報を取得
            with get_scoped_session() as session:
                # 共通のログイン処理（パスワードチェックなし、エラーコード追加）
                login_user, error_info = process_user_login(
                    session,
                    name_id,
                    logger,
                    password=None,
                    use_db_timestamp=True,
                    add_error_code=True,
                )

                if error_info:
                    error_message, http_status, error_response = error_info
                    logger.error(f"ユーザー情報取得失敗です。errocode: 401", auth=True)
                    if error_response:
                        return jsonify(error_response), http_status
                    return jsonify({"message": error_message}), http_status

                # ログイン処理を完了
                session_id, payload = complete_login_process(
                    session, login_user, use_db_timestamp=True
                )

                # JWTトークンを生成
                access_token = create_access_token(
                    identity=login_user.user_id,
                    additional_claims=payload,
                    expires_delta=datetime.timedelta(hours=2),
                )
                refresh_token = create_refresh_token(identity=login_user.user_id)

                # レスポンスデータを作成
                response_data = {
                    "status": "ok",
                    "token": access_token,
                    "refreshToken": refresh_token,
                }

                if mst_data:
                    response_data["master"] = mst_data

                response_data["session_id"] = session_id

                # レスポンスを作成
                response = jsonify(response_data)

                # クッキーを設定
                set_access_cookies(response, access_token)
                set_refresh_cookies(response, refresh_token)

                # session_idをcookieに設定
                response.set_cookie(
                    "session_id",
                    session_id,
                    httponly=True,
                    secure=os.getenv("FLASK_ENV") == "production",
                    samesite="Lax",
                    max_age=current_app.config.get(
                        "JWT_REFRESH_TOKEN_EXPIRES"
                    ).total_seconds(),
                    path="/",
                )

                logger.info(f"ログイン成功。username:{login_user.user_id}", auth=True)
                return response, 200

        except Exception as e:
            # logger.error(f"ユーザー情報初期化エラー: {str(e)}")
            logger.error(f"ログイン処理が失敗しました。", auth=True)
            return jsonify({"message": f"ユーザー情報初期化エラー: {str(e)}"}), 500


# エンドポイント登録
user_info_init_view = UserInfoInitApi.as_view("user_info_init_api")
auth_bp.add_url_rule("/user_info_init", view_func=user_info_init_view, methods=["GET"])
