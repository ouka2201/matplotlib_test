"""
auth_api.pyのテストコード
"""

from unittest.mock import patch

import pytest

from cndx_corp_back.api.auth.auth_api import AuthApi, is_valid_email


@pytest.fixture()
def app(auth_app):
    """Flaskアプリケーションフィクスチャ"""
    view = AuthApi.as_view("auth_api")
    auth_app.add_url_rule("/login", view_func=view, methods=["POST", "OPTIONS"])
    return auth_app


@pytest.fixture()
def client(app):
    """テストクライアントフィクスチャ"""
    return app.test_client()


# is_valid_email関数のテスト
class TestIsValidEmail:
    """is_valid_email関数のテストクラス"""

    def test_valid_email_addresses(self):
        """有効なメールアドレス"""
        assert is_valid_email("user@example.com") is True
        assert is_valid_email("test.user@example.co.jp") is True
        assert is_valid_email("user+tag@example.com") is True
        assert is_valid_email("user_name@example-domain.com") is True

    def test_invalid_email_format(self):
        """無効なメールアドレス形式"""
        assert is_valid_email("invalid@email") is False  # TLDなし
        assert is_valid_email("@example.com") is False  # ローカル部なし
        assert is_valid_email("user@") is False  # ドメインなし
        assert is_valid_email("user@.com") is False  # ドメインが空

    def test_invalid_with_forbidden_characters(self):
        """禁止文字を含む場合は無効"""
        assert is_valid_email("user@example.日本語") is False
        assert is_valid_email("ユーザー@example.com") is False
        assert is_valid_email("user@example.ｺﾑ") is False

    def test_invalid_empty_string(self):
        """空文字列は無効"""
        assert is_valid_email("") is False

    def test_invalid_none(self):
        """Noneは無効"""
        assert is_valid_email(None) is False


# AuthApi.post()のテスト
class TestAuthApiPost:
    """AuthApi.post()のテストクラス"""

    @patch("cndx_corp_back.api.auth.auth_api.create_auth_response")
    @patch("cndx_corp_back.api.auth.auth_api.complete_login_process")
    @patch("cndx_corp_back.api.auth.auth_api.process_user_login")
    @patch("cndx_corp_back.api.auth.auth_api.session_scope")
    def test_post_success(
        self,
        mock_session_scope,
        mock_process_user_login,
        mock_complete_login_process,
        mock_create_auth_response,
        client,
        app,
        mock_user,
        mock_auth_info,
        setup_mock_session_query,
        create_mock_auth_response,
    ):
        """ログインが成功する場合のテスト"""
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
        mock_create_auth_response.return_value = create_mock_auth_response(app)

        response = client.post(
            "/login",
            json={"email_address": "user@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        assert response.json["status"] == "ok"
        assert response.json["token"] == "access-token"
        assert response.json["refreshToken"] == "refresh-token"

        # process_user_loginが呼ばれたことを確認
        mock_process_user_login.assert_called_once_with(
            mock_session,
            "user@example.com",
            app.logger,
            password="password123",
            use_db_timestamp=False,
        )
        # complete_login_processが呼ばれたことを確認
        mock_complete_login_process.assert_called_once_with(
            mock_session, mock_user, use_db_timestamp=False
        )
        # create_auth_responseにsession_idが渡されたことを確認
        mock_create_auth_response.assert_called_once()
        call_args = mock_create_auth_response.call_args
        assert call_args[1]["session_id"] == session_id
        assert mock_session_scope.return_value.__exit__.called

    def test_post_options_returns_200(self, app):
        """OPTIONSリクエストは200を返す"""
        from cndx_corp_back.utils.utils import get_message

        with app.test_request_context("/login", method="OPTIONS"):
            api = AuthApi()
            # controllerデコレータをバイパスして直接メソッドを呼び出す
            response = api.post()
            assert response[1] == 200
            assert response[0].json["message"] == get_message("OK")

    @patch("cndx_corp_back.api.auth.auth_api.process_user_login")
    @patch("cndx_corp_back.api.auth.auth_api.session_scope")
    def test_post_invalid_credentials_returns_401(
        self,
        mock_session_scope,
        mock_process_user_login,
        client,
        mock_user,
        setup_mock_session_query,
    ):
        """パスワードが間違っている場合のテスト"""
        mock_session, _, _ = setup_mock_session_query
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session_scope.return_value.__exit__.return_value = False

        # パスワードエラーをモック
        mock_process_user_login.return_value = (
            None,
            ("パスワードが間違っています。", 401, None),
        )

        response = client.post(
            "/login",
            json={"email_address": "user@example.com", "password": "wrong_password"},
        )

        assert response.status_code == 401
        mock_process_user_login.assert_called_once()

    @patch("cndx_corp_back.api.auth.auth_api.process_user_login")
    @patch("cndx_corp_back.api.auth.auth_api.session_scope")
    def test_post_user_not_found_returns_403(
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

        response = client.post(
            "/login",
            json={
                "email_address": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 403
        assert (
            "ログインできませんでした。登録されていないユーザーです。"
            in response.json["message"]
        )
        mock_process_user_login.assert_called_once()

    def test_post_missing_data_returns_401(self, client):
        """リクエストデータが不足している場合のテスト"""
        response = client.post(
            "/login",
            json={"email_address": "user@example.com"},  # passwordが不足
        )

        assert response.status_code == 401

    def test_post_empty_data_returns_401(self, client):
        """空のリクエストデータの場合のテスト"""
        response = client.post("/login", json={})
        assert response.status_code == 401

    def test_post_invalid_email_format_returns_400(self, client):
        """メールアドレス形式が不正な場合のテスト"""
        response = client.post(
            "/login",
            json={"email_address": "invalid-email", "password": "password123"},
        )

        assert response.status_code == 400
        assert "メールアドレス" in response.json["message"]

    @patch("cndx_corp_back.api.auth.auth_api.complete_login_process")
    @patch("cndx_corp_back.api.auth.auth_api.process_user_login")
    @patch("cndx_corp_back.api.auth.auth_api.session_scope")
    def test_post_value_error_returns_500(
        self,
        mock_session_scope,
        mock_process_user_login,
        mock_complete_login_process,
        client,
        mock_user,
        setup_mock_session_query,
    ):
        """complete_login_process()でValueErrorが発生した場合のテスト"""
        mock_session, _, _ = setup_mock_session_query
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session_scope.return_value.__exit__.return_value = False

        mock_process_user_login.return_value = (mock_user, None)
        # complete_login_process内でget_user_permissionsがValueErrorを発生させる
        mock_complete_login_process.side_effect = ValueError(
            "利用者組織情報が存在しません"
        )

        response = client.post(
            "/login",
            json={"email_address": "user@example.com", "password": "password123"},
        )

        assert response.status_code == 500
        # ValueErrorはexcept ValueErrorでキャッチされ、「権限情報取得エラー」というメッセージになる
        # または、Exceptionとしてキャッチされ「ログイン処理中にエラーが発生しました」になる
        assert "エラー" in response.json["message"]
        assert mock_session_scope.return_value.__exit__.called

    @patch("cndx_corp_back.api.auth.auth_api.create_auth_response")
    @patch("cndx_corp_back.api.auth.auth_api.complete_login_process")
    @patch("cndx_corp_back.api.auth.auth_api.process_user_login")
    @patch("cndx_corp_back.api.auth.auth_api.session_scope")
    def test_post_general_exception_returns_500(
        self,
        mock_session_scope,
        mock_process_user_login,
        mock_complete_login_process,
        mock_create_auth_response,
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
        mock_create_auth_response.side_effect = Exception("JWT生成エラー")

        response = client.post(
            "/login",
            json={"email_address": "user@example.com", "password": "password123"},
        )

        assert response.status_code == 500
        assert response.json["message"] == "ログイン処理中にエラーが発生しました。"
        assert mock_session_scope.return_value.__exit__.called

    @patch("cndx_corp_back.api.auth.auth_api.process_user_login")
    @patch("cndx_corp_back.api.auth.auth_api.session_scope")
    def test_post_deleted_user_returns_403(
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

        response = client.post(
            "/login",
            json={"email_address": "user@example.com", "password": "password123"},
        )

        assert response.status_code == 403
        mock_process_user_login.assert_called_once()
