"""
認証APIテスト用の共通フィクスチャ
"""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask

from cndx_corp_back.common.load_master import mst_data


@pytest.fixture
def mock_user():
    """標準的なモックユーザー"""
    return SimpleNamespace(
        user_id="user01",
        user_name="テストユーザ",
        org_id="ORG01",
        user_role="admin",
        user_password="password123",
        email_address="user@example.com",
        delete_flg=False,
        user_status="0",
        start_date=date.today() - timedelta(days=1),
        end_date=None,
    )


@pytest.fixture
def mock_session():
    """モックセッション"""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """モックロガー"""
    return MagicMock()


@pytest.fixture
def mock_auth_info():
    """モック権限情報"""
    return {
        "role": "admin",
        "org_type_code": "01",
        "org_name": "組織",
        "authority_code_map": [(1, "A")],
    }


@pytest.fixture
def setup_mock_session_query(mock_session, mock_user):
    """モックセッションのクエリを設定するヘルパー"""
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = mock_user
    query_mock.filter.return_value = filter_mock

    # func.current_date()とfunc.now()のモック
    current_date_mock = MagicMock()
    current_date_mock.scalar.return_value = date.today()
    current_timestamp_mock = MagicMock()
    current_timestamp_mock.scalar.return_value = datetime.now()

    def query_side_effect(*args):
        from cndx_corp_back.entity.m_user_entity import MUser

        if args and args[0] is MUser:
            return query_mock
        elif (
            args and hasattr(args[0], "__name__") and args[0].__name__ == "current_date"
        ):
            return current_date_mock
        elif args and hasattr(args[0], "__name__") and args[0].__name__ == "now":
            return current_timestamp_mock
        else:
            return current_date_mock

    mock_session.query.side_effect = query_side_effect
    return mock_session, query_mock, filter_mock


@pytest.fixture
def mock_session_scope():
    """モックsession_scope"""
    return MagicMock()


@pytest.fixture
def setup_mock_session_scope(mock_session_scope, mock_session):
    """モックsession_scopeを設定するヘルパー"""
    mock_session_scope.return_value.__enter__.return_value = mock_session
    mock_session_scope.return_value.__exit__.return_value = False
    return mock_session_scope


@pytest.fixture(autouse=True)
def reset_mst_data():
    """各テスト前にmst_dataをリセット"""
    mst_data.clear()
    mst_data.update({"dummy": "value"})
    yield
    mst_data.clear()


@pytest.fixture
def auth_app():
    """認証API用のFlaskアプリケーションフィクスチャ"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret-key"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(hours=3)
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"
    app.config["JWT_REFRESH_COOKIE_NAME"] = "refresh_token_cookie"
    app.config["JWT_SESSION_COOKIE"] = False
    app.config["JWT_COOKIE_SECURE"] = False
    app.config["JWT_COOKIE_DOMAIN"] = None
    app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
    app.config["JWT_REFRESH_COOKIE_PATH"] = "/"
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # テストではCSRF保護を無効化
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"
    app.config["JWT_ACCESS_CSRF_HEADER_NAME"] = "X-CSRF-ACCESS"
    app.config["JWT_REFRESH_CSRF_HEADER_NAME"] = "X-CSRF-REFRESH"
    app.config["JWT_ACCESS_CSRF_FIELD_NAME"] = "csrf_token"
    app.config["JWT_REFRESH_CSRF_FIELD_NAME"] = "csrf_token"
    app.config["SAML_ENABLED"] = False
    app.config["SAML_SETTINGS_PATH"] = "/dummy/path"
    return app


@pytest.fixture
def saml_app():
    """SAML認証API用のFlaskアプリケーションフィクスチャ"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["JWT_SECRET_KEY"] = "test-jwt-secret-key"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 10800
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"
    app.config["JWT_REFRESH_COOKIE_NAME"] = "refresh_token_cookie"
    app.config["SAML_ENABLED"] = True
    app.config["SAML_SETTINGS_PATH"] = "/dummy/path"
    app.config["SAML_DEFAULT_REDIRECT_URL"] = "/"
    return app


@pytest.fixture
def create_mock_user():
    """モックユーザーを作成するヘルパー"""

    def _create(
        user_id="user@example.com",
        user_status="0",
        delete_flg=False,
        email_address="user@example.com",
    ):
        """モックユーザーを作成

        Args:
            user_id: ユーザーID
            user_status: ユーザーステータス
            delete_flg: 削除フラグ
            email_address: メールアドレス
        """
        return SimpleNamespace(
            user_id=user_id,
            user_name="テストユーザ",
            org_id="ORG01",
            user_role="admin",
            delete_flg=delete_flg,
            user_status=user_status,
            email_address=email_address,
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )

    return _create


@pytest.fixture
def setup_mock_session_with_user():
    """モックセッションとユーザークエリを設定するヘルパー"""

    def _setup(mock_user):
        """モックセッションとユーザークエリを設定

        Args:
            mock_user: モックユーザーオブジェクト
        """
        mock_session = MagicMock()
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.return_value = mock_user
        query_mock.filter.return_value = filter_mock

        # func.current_date()とfunc.now()のモック
        current_date_mock = MagicMock()
        current_date_mock.scalar.return_value = date.today()
        current_timestamp_mock = MagicMock()
        current_timestamp_mock.scalar.return_value = datetime.now()

        def query_side_effect(*args):
            from cndx_corp_back.entity.m_user_entity import MUser

            if args and args[0] is MUser:
                return query_mock
            elif (
                args
                and hasattr(args[0], "__name__")
                and args[0].__name__ == "current_date"
            ):
                return current_date_mock
            elif args and hasattr(args[0], "__name__") and args[0].__name__ == "now":
                return current_timestamp_mock
            else:
                return current_date_mock

        mock_session.query.side_effect = query_side_effect
        return mock_session, query_mock, filter_mock

    return _setup
