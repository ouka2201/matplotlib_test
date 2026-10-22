"""
セッション情報登録・更新モジュール
"""

import datetime
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import scoped_session

from cndx_corp_back.entity.t_session_info import TSessionInfo


def create_or_update_session_info(
    db_session: scoped_session, user_id: str, use_db_timestamp: bool = False
) -> str:
    """
    セッション情報を登録・更新する

    ①UUIDでSession_idを採番しレコードを作成
    ②新規登録レコード以外のuser_idに紐づくsession_infoレコードのis_activeをfalseに変更
    ③session_idを返却（cookieに含めるため）

    Args:
        db_session: データベースセッション
        user_id: ユーザーID
        use_db_timestamp: Trueの場合、データベースサーバーの時間を使用（デフォルト: False）

    Returns:
        str: 新規作成されたsession_id（UUIDv4形式）
    """
    if use_db_timestamp:
        # データベースサーバーの時間を使用
        current_datetime = db_session.query(func.now()).scalar()
    else:
        # アプリケーションサーバーの時間を使用（JST）
        current_datetime = datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo"))

    # ①UUIDでSession_idを採番
    new_session_id = str(uuid.uuid4())

    # ②新規登録レコード以外のuser_idに紐づくsession_infoレコードのis_activeをfalseに変更
    db_session.query(TSessionInfo).filter(
        TSessionInfo.user_id == user_id, TSessionInfo.delete_flg.is_(False)
    ).update(
        {"is_active": False, "updated_by": user_id, "updated_at": current_datetime},
        synchronize_session=False,
    )

    # ③新規レコードを作成（is_active=TRUE）
    new_session = TSessionInfo(
        session_id=new_session_id,
        user_id=user_id,
        is_active=True,
        delete_flg=False,
        created_by=user_id,
    )
    db_session.add(new_session)

    # コミットはsession_scopeが管理するため、ここではコミットしない

    # ④session_idを返却（cookieに含めるため）
    return new_session_id
