import re

import pandas as pd
from flask import current_app, g, jsonify, make_response, request
from flask.views import MethodView
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import jwt_user_context_db
from cndx_corp_back.common.load_master import mst_data
from cndx_corp_back.utils.utils import get_message

from . import auth_bp
from .util import (
    complete_login_process,
    create_auth_response,
    get_user_permissions,
    process_user_login,
)


def is_valid_email(email):
    """
    メールアドレスのバリデーション

    Args:
        email: 検証するメールアドレス文字列

    Returns:
        bool: 有効なメールアドレスの場合True、それ以外はFalse

    例:
        - "user@example.com" -> True
        - "test.user+tag@example.co.jp" -> True
        - "invalid@email" -> False
        - "user@example.日本語" -> False
    """
    # Noneまたは空文字列のチェック
    if not email or not isinstance(email, str):
        return False

    # 禁止文字パターン（半角カナ、全角カナ、ひらがな、漢字、全角スペース）
    FORBIDDEN_PATTERN = re.compile(r"[ｦ-ﾟ 　ァ-ンぁ-ん一-龥]")

    # 禁止文字が含まれている場合は無効
    if FORBIDDEN_PATTERN.search(email):
        return False

    # メールアドレス形式のチェック
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(email_regex, email) is not None


class AuthApi(MethodView):

    def post(self):
        logger = current_app.logger
        """ ログイン"""
        if request.method == "OPTIONS":
            return jsonify({"message": get_message("OK")}), 200

        try:
            data = request.json
            if not data or "email_address" not in data or "password" not in data:
                logger.error(f"ログインデータが不正です: {data}")
                logger.error(
                    f"ログイン失敗しました。username:{data["email_address"]}, errocode: 401",
                    auth=True,
                )
                return jsonify({"message": get_message("UNAUTHORIZED")}), 401

            email_address = data["email_address"]
            password = data["password"]

            # メールアドレスのバリデーション
            if not is_valid_email(email_address):
                logger.error(f"メールアドレス形式が不正です: {email_address}")
                logger.error(
                    f"存在しないユーザです。username:{email_address}, errocode: 404",
                    auth=True,
                )
                return (
                    jsonify(
                        {
                            "message": get_message(
                                "INCORRECT", item_name="メールアドレス"
                            )
                        }
                    ),
                    400,
                )

            with get_scoped_session() as session:
                # 共通のログイン処理
                login_user, error_info = process_user_login(
                    session,
                    email_address,
                    logger,
                    password=password,
                    use_db_timestamp=False,
                )
                if not login_user:
                    logger.error(
                        f"存在しないユーザです。username:{email_address}, errocode: 404",
                        auth=True,
                    )
                    return (
                        jsonify({"message": "User not found"}),
                        404,
                    )
                if error_info:
                    error_message, http_status, _ = error_info
                    # パスワードエラーの場合は専用メッセージを使用
                    if http_status == 401:
                        logger.error(
                            f"パスワードが間違っています。username:{email_address}, errocode: 401",
                            auth=True,
                        )
                        return (
                            jsonify(
                                {
                                    "message": get_message(
                                        "INCORRECT", item_name="パスワード"
                                    )
                                }
                            ),
                            http_status,
                        )
                    return jsonify({"message": error_message}), http_status

                # ログイン処理を完了
                session_id, payload = complete_login_process(
                    session, login_user, use_db_timestamp=False
                )

                # JWTトークンを生成し、認証レスポンスを作成（session_scope内で実行）
                # JWT生成に失敗した場合、session_scopeがロールバックする
                response = create_auth_response(
                    user_id=login_user.user_id,
                    payload=payload,
                    mst_data=mst_data,
                    session_id=session_id,
                )

                g.user_id = login_user.user_id

                logger.info(f"ログイン成功。username:{email_address}", auth=True)
                return response

        except ValueError as e:
            # get_user_permissions()で発生する可能性がある
            logger.error(f"権限情報取得エラー: {str(e)}")
            return jsonify({"message": f"権限情報取得エラー: {str(e)}"}), 500
        except Exception as e:
            # その他すべての例外（SQLAlchemy関連、JWT関連、その他）
            logger.error(f"ログインエラー: {str(e)}")
            return jsonify({"message": "ログイン処理中にエラーが発生しました。"}), 500


@auth_bp.route("/refresh", methods=["POST", "OPTIONS"])
# @jwt_required(refresh=True, locations=["cookies"])
@jwt_user_context_db(refresh=True)
def refresh_token(user_context=None):
    if request.method == "OPTIONS":
        return jsonify({"message": get_message("OK")}), 200

    # current_user = get_jwt_identity()

    payload = {
        "user_id": user_context.get("user_id"),
        "org_id": user_context.get("org_id"),
        "name": user_context.get("user_name"),
        "role": user_context.get("role"),
        "org_type_code": user_context.get("org_type_code"),
        "authority_code_map": user_context.get("authority_code_map"),
    }
    new_access_token = create_access_token(
        identity=user_context.get("user_id"), additional_claims=payload
    )
    # new_access_token = create_access_token(identity=current_user)
    response = make_response(jsonify({"status": "ok", "token": new_access_token}))
    set_access_cookies(response, new_access_token)
    return response


@auth_bp.route("/permissions", methods=["GET", "OPTIONS"])
@jwt_required()
def get_permissions():
    if request.method == "OPTIONS":
        return jsonify({"message": get_message("OK")}), 200

    user_id = get_jwt_identity()
    # DataFrameに変換（インデックスが '0000', '0001' になる）
    df_users = pd.DataFrame.from_dict(mst_data["M_USER"])

    # 必要ならインデックスをリセット（数値にする）
    df_users.reset_index(drop=True, inplace=True)

    df_filtered_user = df_users[df_users["user_id"] == user_id]
    role = df_filtered_user.iloc[0]["user_role"]
    user_org_id = df_filtered_user.iloc[0]["org_id"]

    # 利用者組織マスタから組織IDに紐づくを取得
    with get_scoped_session() as session:
        auth_info = get_user_permissions(session, user_org_id, role)

    mapped_list = [
        {"authority_id": aid, "authority_code": acode}
        for aid, acode in auth_info.get("authority_code_map", [])
    ]

    return jsonify({"status": "ok", "permissions": mapped_list}), 200


@auth_bp.route("/signout", methods=["POST", "GET"])
def signout():
    response = make_response(
        jsonify({"status": "success", "message": get_message("LOGGED_OUT")})
    )
    unset_jwt_cookies(response)
    response.delete_cookie("session_id", path="/")
    return response


auth_view = AuthApi.as_view("auth_api")
auth_bp.add_url_rule("/login", view_func=auth_view, methods=["POST"])
