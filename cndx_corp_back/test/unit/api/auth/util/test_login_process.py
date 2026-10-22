"""
ログイン処理共通関数のテスト
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from cndx_corp_back.api.auth.util.login_process import (
    complete_login_process,
    prepare_user_data,
    process_user_login,
)


@pytest.fixture
def mock_session():
    """モックセッション"""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_logger():
    """モックロガー"""
    return MagicMock()


@pytest.fixture
def mock_user():
    """モックユーザー"""
    return SimpleNamespace(
        user_id="user01",
        user_name="テストユーザ",
        org_id="ORG01",
        user_role="admin",
        user_password="correct_password",
        email_address="user@example.com",
        delete_flg=False,
        user_status="0",
    )


@pytest.fixture
def mock_auth_info():
    """モック権限情報"""
    return {
        "role": "admin",
        "org_type_code": "01",
        "org_name": "テスト組織",
        "authority_code_map": [(1, "A"), (2, "B")],
    }


@pytest.fixture
def mock_payload():
    """モックJWTペイロード"""
    return {
        "user_id": "user01",
        "org_id": "ORG01",
        "name": "テストユーザ",
        "role": "admin",
        "org_type_code": "01",
        "org_name": "テスト組織",
        "authority_code_map": [{"authority_id": 1, "authority_code": "A"}],
    }


# process_user_login関数のテスト
class TestProcessUserLogin:
    """process_user_login関数のテストクラス"""

    @patch("cndx_corp_back.api.auth.util.login_process.validate_user_login")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_by_email")
    def test_success_without_password(
        self,
        mock_get_user_by_email,
        mock_validate_user_login,
        mock_session,
        mock_logger,
        mock_user,
    ):
        """正常系: パスワードチェックなしでログイン成功"""
        mock_get_user_by_email.return_value = mock_user
        mock_validate_user_login.return_value = None

        login_user, error_info = process_user_login(
            mock_session,
            "user@example.com",
            mock_logger,
            password=None,
        )

        assert login_user == mock_user
        assert error_info is None
        mock_get_user_by_email.assert_called_once_with(mock_session, "user@example.com")
        mock_validate_user_login.assert_called_once_with(
            mock_session, mock_user, "user@example.com", mock_logger
        )

    @patch("cndx_corp_back.api.auth.util.login_process.validate_user_login")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_by_email")
    def test_success_with_correct_password(
        self,
        mock_get_user_by_email,
        mock_validate_user_login,
        mock_session,
        mock_logger,
        mock_user,
    ):
        """正常系: 正しいパスワードでログイン成功"""
        mock_get_user_by_email.return_value = mock_user
        mock_validate_user_login.return_value = None

        login_user, error_info = process_user_login(
            mock_session,
            "user@example.com",
            mock_logger,
            password="correct_password",
        )

        assert login_user == mock_user
        assert error_info is None

    @patch("cndx_corp_back.api.auth.util.login_process.validate_user_login")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_by_email")
    def test_failure_incorrect_password(
        self,
        mock_get_user_by_email,
        mock_validate_user_login,
        mock_session,
        mock_logger,
        mock_user,
    ):
        """異常系: パスワードが間違っている"""
        mock_get_user_by_email.return_value = mock_user
        mock_validate_user_login.return_value = None

        login_user, error_info = process_user_login(
            mock_session,
            "user@example.com",
            mock_logger,
            password="wrong_password",
        )

        assert login_user is None
        assert error_info is not None
        error_message, http_status, error_response = error_info
        assert error_message == "パスワードが間違っています。"
        assert http_status == 401
        assert error_response is None
        mock_logger.error.assert_called_once()

    @patch("cndx_corp_back.api.auth.util.login_process.validate_user_login")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_by_email")
    def test_failure_user_not_found(
        self,
        mock_get_user_by_email,
        mock_validate_user_login,
        mock_session,
        mock_logger,
    ):
        """異常系: ユーザーが見つからない"""
        mock_get_user_by_email.return_value = None
        mock_validate_user_login.return_value = (
            "ログインできませんでした。登録されていないユーザーです。",
            403,
        )

        login_user, error_info = process_user_login(
            mock_session,
            "nonexistent@example.com",
            mock_logger,
            password=None,
        )

        assert login_user is None
        assert error_info is not None
        error_message, http_status, error_response = error_info
        assert "ログインできませんでした" in error_message
        assert http_status == 403
        assert error_response is not None
        assert "message" in error_response

    @patch("cndx_corp_back.api.auth.util.login_process.validate_user_login")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_by_email")
    def test_failure_invalid_user_status(
        self,
        mock_get_user_by_email,
        mock_validate_user_login,
        mock_session,
        mock_logger,
        mock_user,
    ):
        """異常系: ユーザーステータスが無効"""
        mock_user.user_status = "1"  # 登録処理中
        mock_get_user_by_email.return_value = mock_user
        mock_validate_user_login.return_value = (
            "ログインできませんでした。登録処理中のユーザーです。利用可能になるまでお待ちください。",
            403,
        )

        login_user, error_info = process_user_login(
            mock_session,
            "user@example.com",
            mock_logger,
            password=None,
        )

        assert login_user is None
        assert error_info is not None
        error_message, http_status, error_response = error_info
        assert "登録処理中" in error_message
        assert http_status == 403

    @patch("cndx_corp_back.api.auth.util.login_process.validate_user_login")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_by_email")
    def test_failure_with_error_code(
        self,
        mock_get_user_by_email,
        mock_validate_user_login,
        mock_session,
        mock_logger,
        mock_user,
    ):
        """異常系: エラーコードが追加される（SAML認証の場合）"""
        mock_user.user_status = "1"  # 登録処理中
        mock_get_user_by_email.return_value = mock_user
        mock_validate_user_login.return_value = (
            "ログインできませんでした。登録処理中のユーザーです。利用可能になるまでお待ちください。",
            403,
        )

        login_user, error_info = process_user_login(
            mock_session,
            "user@example.com",
            mock_logger,
            password=None,
            add_error_code=True,
        )

        assert login_user is None
        assert error_info is not None
        error_message, http_status, error_response = error_info
        assert http_status == 403
        assert error_response is not None
        assert error_response["error_code"] == "USER_STATUS_REGISTERING"

    @patch("cndx_corp_back.api.auth.util.login_process.validate_user_login")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_by_email")
    def test_error_code_mapping(
        self,
        mock_get_user_by_email,
        mock_validate_user_login,
        mock_session,
        mock_logger,
        mock_user,
    ):
        """エラーコードマッピングのテスト"""
        status_map = {
            "1": "USER_STATUS_REGISTERING",
            "2": "USER_STATUS_APPLIED",
            "3": "USER_STATUS_CANCELLED",
            "4": "USER_STATUS_INVALIDATED",
            "5": "USER_STATUS_DELETED",
        }

        for status, expected_code in status_map.items():
            mock_user.user_status = status
            mock_get_user_by_email.return_value = mock_user
            mock_validate_user_login.return_value = ("エラーメッセージ", 403)

            _, error_info = process_user_login(
                mock_session,
                "user@example.com",
                mock_logger,
                password=None,
                add_error_code=True,
            )

            assert error_info is not None
            _, _, error_response = error_info
            assert error_response["error_code"] == expected_code


# prepare_user_data関数のテスト
class TestPrepareUserData:
    """prepare_user_data関数のテストクラス"""

    def test_prepare_user_data_success(self, mock_user):
        """正常系: ユーザーデータを正しく辞書に変換"""
        result = prepare_user_data(mock_user)

        assert result == {
            "user_id": "user01",
            "user_name": "テストユーザ",
            "org_id": "ORG01",
            "user_role": "admin",
        }


# complete_login_process関数のテスト
class TestCompleteLoginProcess:
    """complete_login_process関数のテストクラス"""

    @patch("cndx_corp_back.api.auth.util.login_process.create_jwt_payload")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_permissions")
    @patch(
        "cndx_corp_back.api.auth.util.login_process.update_last_login_datetime_by_user_id"
    )
    @patch("cndx_corp_back.api.auth.util.login_process.create_or_update_session_info")
    def test_success(
        self,
        mock_create_or_update_session_info,
        mock_update_last_login,
        mock_get_user_permissions,
        mock_create_jwt_payload,
        mock_session,
        mock_user,
        mock_auth_info,
        mock_payload,
    ):
        """正常系: ログイン処理が正常に完了"""
        session_id = "test-session-id-12345678901234567890123456789012"
        mock_create_or_update_session_info.return_value = session_id
        mock_get_user_permissions.return_value = mock_auth_info
        mock_create_jwt_payload.return_value = mock_payload

        result_session_id, result_payload = complete_login_process(
            mock_session,
            mock_user,
            use_db_timestamp=False,
        )

        assert result_session_id == session_id
        assert result_payload == mock_payload

        # 各関数が正しい引数で呼ばれたことを確認
        mock_create_or_update_session_info.assert_called_once_with(
            mock_session,
            "user01",
            use_db_timestamp=False,
        )
        mock_update_last_login.assert_called_once_with(
            mock_session,
            "user01",
            session_id,
            use_db_timestamp=False,
        )
        mock_get_user_permissions.assert_called_once_with(
            mock_session,
            "ORG01",
            "admin",
        )
        mock_create_jwt_payload.assert_called_once()

    @patch("cndx_corp_back.api.auth.util.login_process.create_jwt_payload")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_permissions")
    @patch(
        "cndx_corp_back.api.auth.util.login_process.update_last_login_datetime_by_user_id"
    )
    @patch("cndx_corp_back.api.auth.util.login_process.create_or_update_session_info")
    def test_success_with_db_timestamp(
        self,
        mock_create_or_update_session_info,
        mock_update_last_login,
        mock_get_user_permissions,
        mock_create_jwt_payload,
        mock_session,
        mock_user,
        mock_auth_info,
        mock_payload,
    ):
        """正常系: データベースタイムスタンプを使用する場合"""
        session_id = "test-session-id"
        mock_create_or_update_session_info.return_value = session_id
        mock_get_user_permissions.return_value = mock_auth_info
        mock_create_jwt_payload.return_value = mock_payload

        complete_login_process(
            mock_session,
            mock_user,
            use_db_timestamp=True,
        )

        # use_db_timestamp=Trueで呼ばれたことを確認
        mock_create_or_update_session_info.assert_called_once_with(
            mock_session,
            "user01",
            use_db_timestamp=True,
        )
        mock_update_last_login.assert_called_once_with(
            mock_session,
            "user01",
            session_id,
            use_db_timestamp=True,
        )

    @patch("cndx_corp_back.api.auth.util.login_process.create_jwt_payload")
    @patch("cndx_corp_back.api.auth.util.login_process.get_user_permissions")
    @patch(
        "cndx_corp_back.api.auth.util.login_process.update_last_login_datetime_by_user_id"
    )
    @patch("cndx_corp_back.api.auth.util.login_process.create_or_update_session_info")
    def test_failure_get_user_permissions_error(
        self,
        mock_create_or_update_session_info,
        mock_update_last_login,
        mock_get_user_permissions,
        mock_create_jwt_payload,
        mock_session,
        mock_user,
    ):
        """異常系: 権限情報取得でエラーが発生"""
        session_id = "test-session-id"
        mock_create_or_update_session_info.return_value = session_id
        mock_get_user_permissions.side_effect = ValueError(
            "利用者組織情報が存在しません"
        )

        with pytest.raises(ValueError, match="利用者組織情報"):
            complete_login_process(
                mock_session,
                mock_user,
                use_db_timestamp=False,
            )

        # セッション作成とログイン更新は実行される
        mock_create_or_update_session_info.assert_called_once()
        mock_update_last_login.assert_called_once()
        # 権限取得でエラーが発生する
        mock_get_user_permissions.assert_called_once()
        # JWTペイロード作成は実行されない
        mock_create_jwt_payload.assert_not_called()
