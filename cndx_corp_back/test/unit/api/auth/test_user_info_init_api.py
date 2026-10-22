"""
user_info_init.pyのテストコード
"""

from unittest.mock import MagicMock, patch

import pytest

from cndx_corp_back.api.auth.user_info_init import UserInfoInitApi


@pytest.fixture()
def app(auth_app):
    """ユーザー情報初期化API用のFlaskアプリケーションフィクスチャ"""
    view = UserInfoInitApi.as_view("user_info_init_api")
    auth_app.add_url_rule("/user_info_init", view_func=view, methods=["GET"])
    return auth_app


@pytest.fixture()
def client(app):
    """テストクライアントフィクスチャ"""
    return app.test_client()


# UserInfoInitApi.get()のテスト
class TestUserInfoInitApi:
    """UserInfoInitApi.get()のテストクラス"""

    @patch("cndx_corp_back.api.auth.user_info_init.create_refresh_token")
    @patch("cndx_corp_back.api.auth.user_info_init.create_access_token")
    @patch("cndx_corp_back.api.auth.user_info_init.complete_login_process")
    @patch("cndx_corp_back.api.auth.user_info_init.process_user_login")
    @patch("cndx_corp_back.api.auth.user_info_init.session_scope")
    def test_get_success(
        self,
        mock_session_scope,
        mock_process_user_login,
        mock_complete_login_process,
        mock_create_access_token,
        mock_create_refresh_token,
        client,
        app,
        mock_user,
        mock_auth_info,
        setup_mock_session_query,
    ):
        """ユーザー情報初期化が正常に処理される"""
        mock_session, _, _ = setup_mock_session_query
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session_scope.return_value.__exit__.return_value = False

        # session_idとpayloadをモック
        session_id = "test-session-id-12345678901234567890123456789012"
        mock_payload = {
            "user_id": "user01",
            "org_id": "ORG01",
            "name": "テストユーザ",
            "role": "admin",
        }
        mock_complete_login_process.return_value = (session_id, mock_payload)
        mock_process_user_login.return_value = (mock_user, None)
        mock_create_access_token.return_value = "access-token"
        mock_create_refresh_token.return_value = "refresh-token"

        # Flask sessionにname_idを設定（email_addressと一致させる）
        with client.session_transaction() as sess:
            sess["saml_name_id"] = mock_user.email_address

        response = client.get("/user_info_init")

        assert response.status_code == 200
        assert response.json["status"] == "ok"
        assert response.json["token"] == "access-token"
        assert response.json["refreshToken"] == "refresh-token"
        assert response.json["session_id"] == session_id

        # process_user_loginが呼ばれたことを確認
        mock_process_user_login.assert_called_once()
        call_args = mock_process_user_login.call_args
        assert call_args[0][0] == mock_session
        assert call_args[0][1] == mock_user.email_address
        assert call_args[1]["password"] is None
        assert call_args[1]["use_db_timestamp"] is True
        assert call_args[1]["add_error_code"] is True
        # complete_login_processが呼ばれたことを確認
        mock_complete_login_process.assert_called_once_with(
            mock_session, mock_user, use_db_timestamp=True
        )
        assert mock_session_scope.return_value.__exit__.called

    def test_get_missing_name_id_returns_401(self, client):
        """Flask sessionにname_idが存在しない場合のテスト"""
        # sessionにname_idを設定しない

        response = client.get("/user_info_init")

        assert response.status_code == 401
        assert "認証情報が見つかりません" in response.json["message"]

    @patch("cndx_corp_back.api.auth.user_info_init.process_user_login")
    @patch("cndx_corp_back.api.auth.user_info_init.session_scope")
    def test_get_user_not_found_returns_403(
        self,
        mock_session_scope,
        mock_process_user_login,
        client,
        setup_mock_session_query,
    ):
        """ユーザーが存在しない場合のテスト"""
        mock_session, _, _ = setup_mock_session_query
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session_scope.return_value.__exit__.return_value = False

        # ユーザーが見つからないエラーをモック
        mock_process_user_login.return_value = (
            None,
            ("ログインできませんでした。登録されていないユーザーです。", 403, None),
        )

        # Flask sessionにname_idを設定
        with client.session_transaction() as sess:
            sess["saml_name_id"] = "nonexistent_user"

        response = client.get("/user_info_init")

        assert response.status_code == 403
        assert (
            "ログインできませんでした。登録されていないユーザーです。"
            in response.json["message"]
        )

    @patch("cndx_corp_back.api.auth.user_info_init.process_user_login")
    @patch("cndx_corp_back.api.auth.user_info_init.session_scope")
    def test_get_deleted_user_returns_403(
        self,
        mock_session_scope,
        mock_process_user_login,
        client,
        mock_user,
        setup_mock_session_query,
    ):
        """削除されたユーザーがログインを試みた場合のテスト"""
        mock_session, _, _ = setup_mock_session_query
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session_scope.return_value.__exit__.return_value = False

        # 削除されたユーザーエラーをモック
        mock_process_user_login.return_value = (
            None,
            ("ログインできませんでした。登録されていないユーザーです。", 403, None),
        )

        # Flask sessionにname_idを設定
        with client.session_transaction() as sess:
            sess["saml_name_id"] = mock_user.email_address

        response = client.get("/user_info_init")

        assert response.status_code == 403
        mock_process_user_login.assert_called_once()

    @patch("cndx_corp_back.api.auth.user_info_init.create_refresh_token")
    @patch("cndx_corp_back.api.auth.user_info_init.create_access_token")
    @patch("cndx_corp_back.api.auth.user_info_init.complete_login_process")
    @patch("cndx_corp_back.api.auth.user_info_init.process_user_login")
    @patch("cndx_corp_back.api.auth.user_info_init.session_scope")
    def test_get_general_exception_returns_500(
        self,
        mock_session_scope,
        mock_process_user_login,
        mock_complete_login_process,
        mock_create_access_token,
        mock_create_refresh_token,
        client,
        mock_user,
        setup_mock_session_query,
    ):
        """予期しないエラーが発生した場合のテスト"""
        mock_session, _, _ = setup_mock_session_query
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session_scope.return_value.__exit__.return_value = False

        mock_process_user_login.return_value = (mock_user, None)
        mock_complete_login_process.return_value = (
            "test-session-id",
            {"user_id": "user01"},
        )
        mock_create_access_token.side_effect = Exception("JWT生成エラー")

        # Flask sessionにname_idを設定（email_addressと一致させる）
        with client.session_transaction() as sess:
            sess["saml_name_id"] = mock_user.email_address

        response = client.get("/user_info_init")

        assert response.status_code == 500
        assert "ユーザー情報初期化エラー" in response.json["message"]
        assert mock_session_scope.return_value.__exit__.called
