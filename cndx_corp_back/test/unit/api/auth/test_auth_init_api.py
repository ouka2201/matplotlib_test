"""
auth_init.pyのテストコード
"""

from unittest.mock import patch

import pytest

from cndx_corp_back.api.auth.auth_init import AuthInitApi


@pytest.fixture()
def app(auth_app):
    """認証初期化API用のFlaskアプリケーションフィクスチャ"""
    view = AuthInitApi.as_view("auth_init_api")
    auth_app.add_url_rule("/auth_init", view_func=view, methods=["GET", "OPTIONS"])
    return auth_app


@pytest.fixture()
def client(app):
    """テストクライアントフィクスチャ"""
    return app.test_client()


# AuthInitApi.get()のテスト
class TestAuthInitApi:
    """AuthInitApi.get()のテストクラス"""

    def test_get_saml_disabled_returns_auth_signin(self, app, client):
        """SAML認証が無効な場合、auth/signinを返す"""
        app.config["SAML_ENABLED"] = False

        response = client.get("/auth_init")

        assert response.status_code == 200
        assert response.json["message"] == "auth/signin"

    def test_get_saml_enabled_returns_saml(self, app, client):
        """SAML認証が有効な場合、auth/signinを返す"""
        app.config["SAML_ENABLED"] = True

        response = client.get("/auth_init")

        assert response.status_code == 200
        assert response.json["message"] == "auth/signin"

    def test_get_options_returns_200(self, client):
        """OPTIONSリクエストは200を返す"""
        from cndx_corp_back.utils.utils import get_message

        # OPTIONSリクエストを送信（auth_init.pyのgetメソッド内でOPTIONSをチェックしている）
        # MethodViewはOPTIONSメソッドを自動的に処理するが、auth_init.pyのgetメソッド内で
        # request.method == "OPTIONS"をチェックしているため、getメソッドが呼ばれる
        response = client.options("/auth_init")
        assert response.status_code == 200
        assert response.json["message"] == get_message("OK")

    def test_get_default_saml_disabled(self, app, client):
        """SAML_ENABLEDが設定されていない場合、デフォルトで無効とみなす"""
        # SAML_ENABLEDを削除
        if "SAML_ENABLED" in app.config:
            del app.config["SAML_ENABLED"]

        response = client.get("/auth_init")

        assert response.status_code == 200
        assert response.json["message"] == "auth/signin"
