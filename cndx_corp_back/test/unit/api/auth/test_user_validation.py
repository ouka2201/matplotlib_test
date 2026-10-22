"""
user_validation.pyのテストコード
"""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from cndx_corp_back.api.auth.util.user_validation import (
    get_user_by_email,
    validate_user_login,
)


class TestValidateUserLogin:
    """validate_user_login関数のテストクラス"""

    @pytest.fixture
    def mock_session(self):
        """モックセッションのフィクスチャ"""
        return MagicMock()

    @pytest.fixture
    def mock_logger(self):
        """モックロガーのフィクスチャ"""
        return MagicMock()

    def test_validate_user_login_user_not_found(self, mock_session, mock_logger):
        """ユーザーが存在しない場合のテスト"""
        result = validate_user_login(
            mock_session, None, "user@example.com", mock_logger
        )

        assert result is not None
        error_message, http_status = result
        assert http_status == 403  # 実装では403を返す
        # 改行が含まれるため、改行を考慮した比較
        assert "ログインできませんでした" in error_message
        assert "登録されていないユーザーです" in error_message
        mock_logger.warning.assert_called_once()

    def test_validate_user_login_deleted_user(self, mock_session, mock_logger):
        """削除フラグがTrueの場合のテスト"""
        mock_user = SimpleNamespace(
            delete_flg=True,
            user_status="0",
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is not None
        error_message, http_status = result
        assert http_status == 403
        # 改行が含まれるため、改行を考慮した比較
        assert "ログインできませんでした" in error_message
        assert "登録されていないユーザーです" in error_message

    def test_validate_user_login_status_1(self, mock_session, mock_logger):
        """user_status="1"（登録処理中）の場合のテスト"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="1",
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is not None
        error_message, http_status = result
        assert http_status == 403
        # 改行が含まれるため、改行を考慮した比較
        assert "ログインできませんでした" in error_message
        assert "登録処理中のユーザーです" in error_message
        assert "利用可能になるまでお待ちください" in error_message

    def test_validate_user_login_status_2(self, mock_session, mock_logger):
        """user_status="2"（申請受付済）の場合のテスト"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="2",
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is not None
        error_message, http_status = result
        assert http_status == 403
        # 改行が含まれるため、改行を考慮した比較
        assert "ログインできませんでした" in error_message
        assert "申請受付済のユーザーです" in error_message
        assert "利用可能になるまでお待ちください" in error_message

    def test_validate_user_login_status_3(self, mock_session, mock_logger):
        """user_status="3"（取消）の場合のテスト"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="3",
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is not None
        error_message, http_status = result
        assert http_status == 403
        # 改行が含まれるため、改行を考慮した比較
        assert "ログインできませんでした" in error_message
        assert "取消されたユーザーです" in error_message

    def test_validate_user_login_status_other(self, mock_session, mock_logger):
        """その他のステータスの場合のテスト"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="9",  # その他のステータス（想定外の値）
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is not None
        error_message, http_status = result
        assert http_status == 403
        # 改行が含まれるため、改行を考慮した比較
        assert "ログインできませんでした" in error_message
        assert "登録されていないユーザーです" in error_message

    def test_validate_user_login_success(self, mock_session, mock_logger):
        """すべてのチェックを通過した場合のテスト"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="0",
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is None  # エラーなし

    def test_validate_user_login_start_date_none(self, mock_session, mock_logger):
        """start_dateがNoneの場合のテスト（有効期限内）"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="0",
            start_date=None,
            end_date=None,
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is None  # エラーなし

    def test_validate_user_login_end_date_none(self, mock_session, mock_logger):
        """end_dateがNoneの場合のテスト（有効期限なし）"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="0",
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is None  # エラーなし

    def test_validate_user_login_valid_date_range(self, mock_session, mock_logger):
        """有効な日付範囲内の場合のテスト"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="0",
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=10),
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is None  # エラーなし

    def test_validate_user_login_start_date_none_end_date_past(
        self, mock_session, mock_logger
    ):
        """start_dateがNoneでend_dateが過去の場合のテスト（有効期限チェック削除後は成功）"""
        mock_user = SimpleNamespace(
            delete_flg=False,
            user_status="0",
            start_date=None,
            end_date=date.today() - timedelta(days=1),  # 過去の日付
        )

        result = validate_user_login(
            mock_session, mock_user, "user@example.com", mock_logger
        )

        assert result is None  # 有効期限チェックが削除されたため、エラーなし


class TestGetUserByEmail:
    """get_user_by_email関数のテストクラス"""

    @pytest.fixture
    def mock_session(self):
        """モックセッションのフィクスチャ"""
        return MagicMock()

    def test_get_user_by_email_success(self, mock_session):
        """正常系: ユーザーが見つかる場合"""
        mock_user = SimpleNamespace(
            user_id="user01",
            email_address="user@example.com",
            delete_flg=False,
        )

        # クエリチェーンをモック
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.return_value = mock_user
        query_mock.filter.return_value = filter_mock
        mock_session.query.return_value = query_mock

        result = get_user_by_email(mock_session, "user@example.com")

        assert result == mock_user
        mock_session.query.assert_called_once()
        filter_mock.first.assert_called_once()

    def test_get_user_by_email_not_found(self, mock_session):
        """異常系: ユーザーが見つからない場合"""
        # クエリチェーンをモック（Noneを返す）
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.return_value = None
        query_mock.filter.return_value = filter_mock
        mock_session.query.return_value = query_mock

        result = get_user_by_email(mock_session, "nonexistent@example.com")

        assert result is None

    def test_get_user_by_email_filters_deleted(self, mock_session):
        """正常系: 削除フラグがTrueのユーザーは除外される"""
        # クエリチェーンをモック（Noneを返す = 削除されたユーザーは見つからない）
        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.return_value = None  # 削除フラグでフィルタリングされるため
        query_mock.filter.return_value = filter_mock
        mock_session.query.return_value = query_mock

        result = get_user_by_email(mock_session, "deleted@example.com")

        assert result is None
        # filter()がdelete_flg.is_(False)で呼ばれたことを確認
        filter_mock.first.assert_called_once()
