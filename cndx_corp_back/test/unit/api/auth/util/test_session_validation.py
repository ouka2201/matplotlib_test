"""
セッション検証モジュールのテスト
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from sqlalchemy import func
from sqlalchemy.orm import Session

from cndx_corp_back.api.auth.util.session_validation import validate_and_update_session
from cndx_corp_back.entity.t_last_login_info import TLastLoginInfo
from cndx_corp_back.entity.t_session_info import TSessionInfo


@pytest.fixture
def app():
    """Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SESSION_TIMEOUT"] = timedelta(hours=3)
    return app


@pytest.fixture
def mock_session():
    """モックセッション"""
    return MagicMock(spec=Session)


def test_validate_and_update_session_no_session_id(mock_session):
    """session_idが提供されていない場合のテスト"""
    result = validate_and_update_session(mock_session, "", use_db_timestamp=True)

    assert result is not None
    error_message, http_status, error_code = result
    assert http_status == 401
    assert error_code == "SESSION_ID_MISSING"
    assert error_message == "セッションIDが提供されていません。"


def test_validate_and_update_session_not_found(mock_session):
    """セッションが見つからない場合のテスト"""
    mock_session.query.return_value.filter.return_value.first.return_value = None

    result = validate_and_update_session(
        mock_session, "invalid-session-id", use_db_timestamp=True
    )

    assert result is not None
    error_message, http_status, error_code = result
    assert http_status == 401
    assert error_code == "SESSION_NOT_FOUND"
    assert error_message == "セッションが見つかりません。再度ログインしてください。"


def test_validate_and_update_session_inactive(mock_session):
    """is_activeがfalseの場合のテスト（シングルログイン違反）"""
    mock_session_info = MagicMock()
    mock_session_info.is_active = False
    mock_session.query.return_value.filter.return_value.first.return_value = (
        mock_session_info
    )

    result = validate_and_update_session(
        mock_session, "session-id", use_db_timestamp=True
    )

    assert result is not None
    error_message, http_status, error_code = result
    assert http_status == 401
    assert error_code == "SINGLE_LOGIN_VIOLATION"
    assert "別のデバイスまたはブラウザでログインされたため" in error_message


@patch(
    "cndx_corp_back.api.auth.util.session_validation.update_last_login_datetime_by_user_id"
)
def test_validate_and_update_session_success_no_last_login(
    mock_update_last_login, mock_session, app
):
    """最終ログイン情報が存在しない場合のテスト（正常）"""
    from cndx_corp_back.entity.m_user_entity import MUser

    with app.app_context():
        mock_session_info = MagicMock()
        mock_session_info.is_active = True
        mock_session_info.user_id = "user01"

        # ユーザー情報（有効なステータス）
        mock_user = MagicMock()
        mock_user.user_id = "user01"
        mock_user.delete_flg = False
        mock_user.user_status = "0"  # 有効なステータス

        # セッション情報のクエリ
        session_query_mock = MagicMock()
        session_filter_mock = MagicMock()
        session_filter_mock.first.return_value = mock_session_info
        session_query_mock.filter.return_value = session_filter_mock

        # ユーザー情報のクエリ
        user_query_mock = MagicMock()
        user_filter_mock = MagicMock()
        user_filter_mock.first.return_value = mock_user
        user_query_mock.filter.return_value = user_filter_mock

        # 最終ログイン情報のクエリ（Noneを返す）
        last_login_query_mock = MagicMock()
        last_login_filter_mock = MagicMock()
        last_login_filter_mock.first.return_value = None
        last_login_query_mock.filter.return_value = last_login_filter_mock

        def query_side_effect(*args):
            if args and args[0] is TSessionInfo:
                return session_query_mock
            elif args and args[0] is MUser:
                return user_query_mock
            elif args and args[0] is TLastLoginInfo:
                return last_login_query_mock
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        result = validate_and_update_session(
            mock_session, "session-id", use_db_timestamp=True
        )

        # 正常な場合はNoneを返す
        assert result is None
        # update_last_login_datetime_by_user_idが呼ばれたことを確認
        mock_update_last_login.assert_called_once_with(
            mock_session, "user01", session_id="session-id", use_db_timestamp=True
        )


@patch(
    "cndx_corp_back.api.auth.util.session_validation.update_last_login_datetime_by_user_id"
)
@patch("cndx_corp_back.api.auth.util.session_validation.datetime")
def test_validate_and_update_session_success_with_last_login(
    mock_datetime, mock_update_last_login, mock_session, app
):
    """最終ログイン情報が存在し、タイムアウトしていない場合のテスト（正常）"""
    from cndx_corp_back.entity.m_user_entity import MUser

    with app.app_context():
        mock_session_info = MagicMock()
        mock_session_info.is_active = True
        mock_session_info.user_id = "user01"

        # ユーザー情報（有効なステータス）
        mock_user = MagicMock()
        mock_user.user_id = "user01"
        mock_user.delete_flg = False
        mock_user.user_status = "0"  # 有効なステータス

        # 最終ログイン情報（1時間前）
        last_login_datetime = datetime.now(tz=ZoneInfo("Asia/Tokyo")) - timedelta(
            hours=1
        )
        mock_last_login_info = MagicMock()
        mock_last_login_info.last_login_datetime = last_login_datetime

        # セッション情報のクエリ
        session_query_mock = MagicMock()
        session_filter_mock = MagicMock()
        session_filter_mock.first.return_value = mock_session_info
        session_query_mock.filter.return_value = session_filter_mock

        # ユーザー情報のクエリ
        user_query_mock = MagicMock()
        user_filter_mock = MagicMock()
        user_filter_mock.first.return_value = mock_user
        user_query_mock.filter.return_value = user_filter_mock

        # 最終ログイン情報のクエリ
        last_login_query_mock = MagicMock()
        last_login_filter_mock = MagicMock()
        last_login_filter_mock.first.return_value = mock_last_login_info
        last_login_query_mock.filter.return_value = last_login_filter_mock

        def query_side_effect(*args):
            if args and args[0] is TSessionInfo:
                return session_query_mock
            elif args and args[0] is MUser:
                return user_query_mock
            elif args and args[0] is TLastLoginInfo:
                return last_login_query_mock
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        # 現在時刻をモック
        mock_datetime.datetime.now.return_value = datetime.now(
            tz=ZoneInfo("Asia/Tokyo")
        )

        result = validate_and_update_session(
            mock_session, "session-id", use_db_timestamp=False
        )

        # 正常な場合はNoneを返す
        assert result is None
        # update_last_login_datetime_by_user_idが呼ばれたことを確認
        mock_update_last_login.assert_called_once_with(
            mock_session, "user01", session_id="session-id", use_db_timestamp=False
        )


@patch("cndx_corp_back.api.auth.util.session_validation.datetime")
def test_validate_and_update_session_timeout(mock_datetime, mock_session, app):
    """最終ログイン情報が存在し、タイムアウトしている場合のテスト"""
    from cndx_corp_back.entity.m_user_entity import MUser

    with app.app_context():
        mock_session_info = MagicMock()
        mock_session_info.is_active = True
        mock_session_info.user_id = "user01"

        # ユーザー情報（有効なステータス）
        mock_user = MagicMock()
        mock_user.user_id = "user01"
        mock_user.delete_flg = False
        mock_user.user_status = "0"  # 有効なステータス

        # 最終ログイン情報（4時間前、タイムアウト）
        last_login_datetime = datetime.now(tz=ZoneInfo("Asia/Tokyo")) - timedelta(
            hours=4
        )
        mock_last_login_info = MagicMock()
        mock_last_login_info.last_login_datetime = last_login_datetime

        # セッション情報のクエリ
        session_query_mock = MagicMock()
        session_filter_mock = MagicMock()
        session_filter_mock.first.return_value = mock_session_info
        session_query_mock.filter.return_value = session_filter_mock

        # ユーザー情報のクエリ
        user_query_mock = MagicMock()
        user_filter_mock = MagicMock()
        user_filter_mock.first.return_value = mock_user
        user_query_mock.filter.return_value = user_filter_mock

        # 最終ログイン情報のクエリ
        last_login_query_mock = MagicMock()
        last_login_filter_mock = MagicMock()
        last_login_filter_mock.first.return_value = mock_last_login_info
        last_login_query_mock.filter.return_value = last_login_filter_mock

        def query_side_effect(*args):
            if args and args[0] is TSessionInfo:
                return session_query_mock
            elif args and args[0] is MUser:
                return user_query_mock
            elif args and args[0] is TLastLoginInfo:
                return last_login_query_mock
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        # 現在時刻をモック
        mock_datetime.datetime.now.return_value = datetime.now(
            tz=ZoneInfo("Asia/Tokyo")
        )

        result = validate_and_update_session(
            mock_session, "session-id", use_db_timestamp=False
        )

        # タイムアウトエラーが返される
        assert result is not None
        error_message, http_status, error_code = result
        assert http_status == 401
        assert error_code == "SESSION_TIMEOUT"
        assert "セッションがタイムアウトしました" in error_message
        assert "4.0時間経過" in error_message or "4時間経過" in error_message


@patch(
    "cndx_corp_back.api.auth.util.session_validation.update_last_login_datetime_by_user_id"
)
def test_validate_and_update_session_db_timestamp(
    mock_update_last_login, mock_session, app
):
    """データベースサーバーの時間を使用する場合のテスト"""
    from cndx_corp_back.entity.m_user_entity import MUser

    with app.app_context():
        mock_session_info = MagicMock()
        mock_session_info.is_active = True
        mock_session_info.user_id = "user01"

        # ユーザー情報（有効なステータス）
        mock_user = MagicMock()
        mock_user.user_id = "user01"
        mock_user.delete_flg = False
        mock_user.user_status = "0"  # 有効なステータス

        # 最終ログイン情報（1時間前、naive datetime）
        from datetime import timezone as tz
        from zoneinfo import ZoneInfo

        naive_datetime = datetime.now(ZoneInfo("Asia/Tokyo")) - timedelta(hours=1)
        from types import SimpleNamespace

        mock_last_login_info = SimpleNamespace(
            last_login_datetime=naive_datetime.replace(
                tzinfo=None
            )  # naive datetimeとして設定
        )

        # func.now()のモック（データベースサーバーの時間）
        # 現在時刻を1時間後として設定（タイムアウトしないように）
        current_datetime = datetime.now(ZoneInfo("Asia/Tokyo"))
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = current_datetime.replace(
            tzinfo=None
        )  # naive datetimeとして返す

        # セッション情報のクエリ
        session_query_mock = MagicMock()
        session_filter_mock = MagicMock()
        session_filter_mock.first.return_value = mock_session_info
        session_query_mock.filter.return_value = session_filter_mock

        # ユーザー情報のクエリ
        user_query_mock = MagicMock()
        user_filter_mock = MagicMock()
        user_filter_mock.first.return_value = mock_user
        user_query_mock.filter.return_value = user_filter_mock

        # 最終ログイン情報のクエリ
        last_login_query_mock = MagicMock()
        last_login_filter_mock = MagicMock()
        last_login_filter_mock.first.return_value = mock_last_login_info
        last_login_query_mock.filter.return_value = last_login_filter_mock

        def query_side_effect(*args):
            if args and args[0] is TSessionInfo:
                return session_query_mock
            elif args and args[0] is MUser:
                return user_query_mock
            elif args and args[0] is TLastLoginInfo:
                return last_login_query_mock
            elif args and hasattr(args[0], "__name__") and args[0].__name__ == "now":
                return mock_scalar
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        result = validate_and_update_session(
            mock_session, "session-id", use_db_timestamp=True
        )

        # 正常な場合はNoneを返す
        assert result is None
        # update_last_login_datetime_by_user_idが呼ばれたことを確認
        mock_update_last_login.assert_called_once_with(
            mock_session, "user01", session_id="session-id", use_db_timestamp=True
        )
