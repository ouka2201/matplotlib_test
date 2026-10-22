"""
JWTトークン生成とレスポンス作成モジュール
"""
import os
from flask import make_response, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
)
from typing import Dict, Any, Optional


def create_jwt_payload(user_data: Dict[str, Any], auth_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    JWTペイロードを作成

    Args:
        user_data: ユーザーデータ辞書
            - user_id: ユーザーID
            - user_name: ユーザー名
            - org_id: 組織ID
            - user_role: ユーザーロール
        auth_info: 権限情報辞書
            - org_type_code: 組織種別コード
            - org_name: 組織名
            - authority_code_map: 権限コードマップ（(authority_id, authority_code)のリスト）

    Returns:
        dict: JWTペイロード辞書
    """
    mapped_list = [
        {"authority_id": aid, "authority_code": acode}
        for aid, acode in auth_info.get("authority_code_map", [])
    ]

    payload = {
        "user_id": user_data["user_id"],
        "email_address": user_data["email_address"],
        "org_id": user_data["org_id"],
        "name": user_data["user_name"],
        "role": user_data["user_role"],
        "org_type_code": auth_info.get("org_type_code"),
        "org_name": auth_info.get("org_name"),
        "authority_code_map": mapped_list,
    }
    return payload


def create_auth_response(
    user_id: str,
    payload: Dict[str, Any],
    mst_data: Optional[Dict[str, Any]] = None,
    redirect_url: Optional[str] = None,
    expires_delta: Optional[Any] = None,
    session_id: Optional[str] = None
) -> Any:
    """
    JWTトークンを生成し、認証レスポンスを作成

    Args:
        user_id: ユーザーID
        payload: JWTペイロード
        mst_data: マスターデータ（オプション）
        redirect_url: リダイレクトURL（オプション、SAML認証用）
        expires_delta: アクセストークンの有効期限（オプション）
        session_id: セッションID（オプション、cookieに設定するため）

    Returns:
        Response: JWTトークンを含むレスポンス
    """
    # JWTトークンを生成
    if expires_delta:
        access_token = create_access_token(
            identity=user_id,
            additional_claims=payload,
            expires_delta=expires_delta
        )
    else:
        access_token = create_access_token(
            identity=user_id,
            additional_claims=payload
        )
    refresh_token = create_refresh_token(identity=user_id)

    # レスポンスデータを作成
    response_data = {
        "status": "ok",
        "token": access_token,
        "refreshToken": refresh_token,
    }

    if mst_data:
        response_data["master"] = mst_data

    if redirect_url:
        response_data["redirect_url"] = redirect_url

    if session_id:
        response_data["session_id"] = session_id

    response = make_response(jsonify(response_data))

    # クッキーを設定
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

    # session_idをcookieに設定
    if session_id:
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            # secure=os.getenv("FLASK_ENV") == "production",
            secure=current_app.config["JWT_COOKIE_SECURE"],
            samesite="Lax",
            max_age=current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES").total_seconds(),
            path="/",
        )

    return response
