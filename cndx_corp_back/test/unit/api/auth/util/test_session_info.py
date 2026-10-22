"""
セッション情報登録・更新モジュールのテスト
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from cndx_corp_back.api.auth.util.session_info import create_or_update_session_info
from cndx_corp_back.entity.t_session_info import TSessionInfo


@pytest.fixture
def mock_session():
    """モックセッション"""
    return MagicMock(spec=Session)


@patch("cndx_corp_back.api.auth.util.session_info.uuid")
@patch("cndx_corp_back.api.auth.util.session_info.datetime")
def test_create_or_update_session_info_app_timestamp(
    mock_datetime, mock_uuid, mock_session
):
    """アプリケーションサーバーの時間を使用してセッション情報を作成できる"""
    # モックの現在時刻を設定
    mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    mock_datetime.datetime.now.return_value = mock_now

    # UUIDをモック
    mock_uuid.uuid4.return_value.hex = (
        "test-session-id-12345678901234567890123456789012"
    )
    mock_uuid.uuid4.return_value.__str__ = (
        lambda x: "test-session-id-12345678901234567890123456789012"
    )

    # 既存セッション情報がない場合（新規作成）
    mock_session.query.return_value.filter.return_value.update.return_value = None
    mock_session.query.return_value.filter.return_value.first.return_value = None

    # テスト実行
    session_id = create_or_update_session_info(
        mock_session, "user01", use_db_timestamp=False
    )

    # 検証
    assert session_id == "test-session-id-12345678901234567890123456789012"
    # updateが呼ばれたことを確認（既存セッションを非アクティブ化）
    mock_session.query.return_value.filter.return_value.update.assert_called_once()
    # addが呼ばれたことを確認（新規セッション作成）
    mock_session.add.assert_called_once()
    added_session = mock_session.add.call_args[0][0]
    assert isinstance(added_session, TSessionInfo)
    assert (
        added_session.session_id == "test-session-id-12345678901234567890123456789012"
    )
    assert added_session.user_id == "user01"
    assert added_session.is_active is True
    assert added_session.delete_flg is False
    # コミットはsession_scopeが管理するため、ここではコミットしない
    mock_session.commit.assert_not_called()


def test_create_or_update_session_info_db_timestamp(mock_session):
    """データベースサーバーの時間を使用してセッション情報を作成できる"""
    # func.now()のモック
    mock_scalar = MagicMock()
    mock_scalar.scalar.return_value = datetime(2024, 1, 1, 12, 0, 0)
    mock_session.query.return_value.scalar.return_value = datetime(2024, 1, 1, 12, 0, 0)

    # UUIDをモック
    with patch("cndx_corp_back.api.auth.util.session_info.uuid") as mock_uuid:
        mock_uuid.uuid4.return_value.__str__ = lambda x: "test-session-id-db-timestamp"

        # 既存セッション情報がない場合（新規作成）
        mock_session.query.return_value.filter.return_value.update.return_value = None

        # テスト実行
        session_id = create_or_update_session_info(
            mock_session, "user01", use_db_timestamp=True
        )

        # 検証
        assert session_id == "test-session-id-db-timestamp"
        # func.now()が呼ばれたことを確認
        assert mock_session.query.call_count >= 1
        # updateが呼ばれたことを確認
        mock_session.query.return_value.filter.return_value.update.assert_called_once()
        # addが呼ばれたことを確認
        mock_session.add.assert_called_once()
        # コミットはsession_scopeが管理するため、ここではコミットしない
        mock_session.commit.assert_not_called()


@patch("cndx_corp_back.api.auth.util.session_info.uuid")
@patch("cndx_corp_back.api.auth.util.session_info.datetime")
def test_create_or_update_session_info_deactivates_existing(
    mock_datetime, mock_uuid, mock_session
):
    """既存のセッション情報を非アクティブ化できる"""
    # モックの現在時刻を設定
    mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
    mock_datetime.datetime.now.return_value = mock_now

    # UUIDをモック
    mock_uuid.uuid4.return_value.__str__ = lambda x: "new-session-id"

    # 既存セッション情報がある場合
    existing_session = MagicMock()
    existing_session.session_id = "old-session-id"
    existing_session.user_id = "user01"
    existing_session.is_active = True

    # テスト実行
    session_id = create_or_update_session_info(
        mock_session, "user01", use_db_timestamp=False
    )

    # 検証
    assert session_id == "new-session-id"
    # updateが呼ばれて既存セッションが非アクティブ化されたことを確認
    update_call = mock_session.query.return_value.filter.return_value.update.call_args
    assert update_call[1]["synchronize_session"] is False
    assert "is_active" in update_call[0][0]
    assert update_call[0][0]["is_active"] is False
    # 新規セッションが追加されたことを確認
    mock_session.add.assert_called_once()
