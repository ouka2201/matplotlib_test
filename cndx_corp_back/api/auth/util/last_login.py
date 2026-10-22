"""
最終ログイン日時更新モジュール
"""

import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import scoped_session

from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.t_last_login_info import TLastLoginInfo


def update_last_login_datetime_by_user_id(
    db_session: scoped_session,
    user_id: str,
    session_id: str,
    use_db_timestamp: bool = False,
) -> None:
    """
    ユーザーIDで最終ログイン日時を更新（t_last_login_infoテーブルを更新）

    Args:
        db_session: データベースセッション
        user_id: ユーザーID
        session_id: セッションID（必須）
        use_db_timestamp: Trueの場合、データベースサーバーの時間を使用（デフォルト: False）
    """
    if use_db_timestamp:
        # データベースサーバーの時間を使用
        current_datetime = db_session.query(func.now()).scalar()
    else:
        # アプリケーションサーバーの時間を使用（JST）
        current_datetime = datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo"))

    # 既存レコードの存在確認
    existing_record = (
        db_session.query(TLastLoginInfo)
        .filter(TLastLoginInfo.user_id == user_id, TLastLoginInfo.delete_flg.is_(False))
        .scalar()
    )
    if existing_record is not None:
        # 既存レコードを更新
        existing_record.last_login_datetime = current_datetime
        existing_record.session_id = session_id
        existing_record.updated_by = user_id
        existing_record.updated_at = current_datetime
    else:
        # 新規レコードを作成
        new_last_login = TLastLoginInfo(
            user_id=user_id,
            last_login_datetime=current_datetime,
            session_id=session_id,
            delete_flg=False,
            created_by=user_id,
            created_at=current_datetime,
            # updated_atは新規作成時には設定しない（onupdateで自動設定される）
        )
        db_session.add(new_last_login)

    # コミットはsession_scopeが管理するため、ここではコミットしない


def update_last_login_datetime_by_email(
    db_session: scoped_session,
    email_address: str,
    session_id: str,
    use_db_timestamp: bool = True,
) -> None:
    """
    メールアドレスで最終ログイン日時を更新（t_last_login_infoテーブルを更新）

    Args:
        db_session: データベースセッション
        email_address: メールアドレス
        session_id: セッションID（必須）
        use_db_timestamp: Trueの場合、データベースサーバーの時間を使用（デフォルト: True）
    """
    # メールアドレスからuser_idを取得
    user = (
        db_session.query(MUser)
        .filter(MUser.email_address == email_address, MUser.delete_flg.is_(False))
        .first()
    )

    if not user:
        raise ValueError(
            f"メールアドレス '{email_address}' に対応するユーザーが見つかりません"
        )

    # user_idを使用して更新
    update_last_login_datetime_by_user_id(
        db_session,
        user.user_id,
        session_id=session_id,
        use_db_timestamp=use_db_timestamp,
    )
    # コミットはsession_scopeが管理するため、ここではコミットしない
