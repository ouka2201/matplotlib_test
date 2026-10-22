"""
JWTトークン生成とレスポンス作成モジュールのテスト
"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, jsonify, make_response

from cndx_corp_back.api.auth.util.jwt_token import (
    create_auth_response,
    create_jwt_payload,
)


@pytest.fixture
def app():
    """Flaskアプリケーション"""
    app = Flask(__name__)
    return app


def test_create_jwt_payload():
    """JWTペイロードを作成できる"""
    user_data = {
        "user_id": "user01",
        "user_name": "テストユーザー",
        "org_id": "ORG01",
        "user_role": "admin",
    }
    auth_info = {
        "org_type_code": "01",
        "org_name": "テスト組織",
        "authority_code_map": [(1, "A"), (2, "B")],
    }

    result = create_jwt_payload(user_data, auth_info)

    assert result["user_id"] == "user01"
    assert result["name"] == "テストユーザー"
    assert result["org_id"] == "ORG01"
    assert result["role"] == "admin"
    assert result["org_type_code"] == "01"
    assert result["org_name"] == "テスト組織"
    assert result["authority_code_map"] == [
        {"authority_id": 1, "authority_code": "A"},
        {"authority_id": 2, "authority_code": "B"},
    ]


@patch("cndx_corp_back.api.auth.util.jwt_token.set_refresh_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.set_access_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_refresh_token")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_access_token")
def test_create_auth_response_basic(
    mock_create_access_token,
    mock_create_refresh_token,
    mock_set_access_cookies,
    mock_set_refresh_cookies,
    app,
):
    """基本的な認証レスポンスを作成できる"""
    mock_create_access_token.return_value = "access-token"
    mock_create_refresh_token.return_value = "refresh-token"

    payload = {
        "user_id": "user01",
        "org_id": "ORG01",
        "name": "テストユーザー",
        "role": "admin",
    }

    with app.app_context():
        response = create_auth_response("user01", payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["token"] == "access-token"
    assert data["refreshToken"] == "refresh-token"
    # session_idが指定されていない場合はレスポンスに含まれない
    assert "session_id" not in data

    mock_create_access_token.assert_called_once_with(
        identity="user01", additional_claims=payload
    )
    mock_create_refresh_token.assert_called_once_with(identity="user01")
    mock_set_access_cookies.assert_called_once()
    mock_set_refresh_cookies.assert_called_once()


@patch("cndx_corp_back.api.auth.util.jwt_token.set_refresh_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.set_access_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_refresh_token")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_access_token")
def test_create_auth_response_with_mst_data(
    mock_create_access_token,
    mock_create_refresh_token,
    mock_set_access_cookies,
    mock_set_refresh_cookies,
    app,
):
    """マスターデータを含む認証レスポンスを作成できる"""
    mock_create_access_token.return_value = "access-token"
    mock_create_refresh_token.return_value = "refresh-token"

    payload = {"user_id": "user01"}
    mst_data = {"M_USER": {"user01": "data"}}

    with app.app_context():
        response = create_auth_response("user01", payload, mst_data=mst_data)

    data = response.get_json()
    assert data["master"] == mst_data


@patch("cndx_corp_back.api.auth.util.jwt_token.set_refresh_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.set_access_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_refresh_token")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_access_token")
def test_create_auth_response_with_redirect_url(
    mock_create_access_token,
    mock_create_refresh_token,
    mock_set_access_cookies,
    mock_set_refresh_cookies,
    app,
):
    """リダイレクトURLを含む認証レスポンスを作成できる"""
    mock_create_access_token.return_value = "access-token"
    mock_create_refresh_token.return_value = "refresh-token"

    payload = {"user_id": "user01"}

    with app.app_context():
        response = create_auth_response("user01", payload, redirect_url="/after-login")

    data = response.get_json()
    assert data["redirect_url"] == "/after-login"


@patch("cndx_corp_back.api.auth.util.jwt_token.set_refresh_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.set_access_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_refresh_token")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_access_token")
def test_create_auth_response_with_expires_delta(
    mock_create_access_token,
    mock_create_refresh_token,
    mock_set_access_cookies,
    mock_set_refresh_cookies,
    app,
):
    """有効期限を指定した認証レスポンスを作成できる"""
    from datetime import timedelta

    mock_create_access_token.return_value = "access-token"
    mock_create_refresh_token.return_value = "refresh-token"

    payload = {"user_id": "user01"}
    expires_delta = timedelta(hours=2)

    with app.app_context():
        response = create_auth_response("user01", payload, expires_delta=expires_delta)

    mock_create_access_token.assert_called_once_with(
        identity="user01", additional_claims=payload, expires_delta=expires_delta
    )


@patch("cndx_corp_back.api.auth.util.jwt_token.set_refresh_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.set_access_cookies")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_refresh_token")
@patch("cndx_corp_back.api.auth.util.jwt_token.create_access_token")
def test_create_auth_response_with_session_id(
    mock_create_access_token,
    mock_create_refresh_token,
    mock_set_access_cookies,
    mock_set_refresh_cookies,
    app,
):
    """session_idを含む認証レスポンスを作成できる"""
    from datetime import timedelta

    mock_create_access_token.return_value = "access-token"
    mock_create_refresh_token.return_value = "refresh-token"

    # JWT_REFRESH_TOKEN_EXPIRESを設定
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(hours=3)

    payload = {"user_id": "user01"}
    session_id = "test-session-id-12345678901234567890123456789012"

    with app.app_context():
        response = create_auth_response("user01", payload, session_id=session_id)

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["token"] == "access-token"
    assert data["refreshToken"] == "refresh-token"
    assert data["session_id"] == session_id

    # session_idがcookieに設定されたことを確認
    cookies = [cookie for cookie in response.headers.getlist("Set-Cookie")]
    session_cookie = [c for c in cookies if c.startswith("session_id=")]
    assert len(session_cookie) > 0
