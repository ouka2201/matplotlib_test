"""
セッション検証モジュール
"""

import datetime
from zoneinfo import ZoneInfo

from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import scoped_session

from cndx_corp_back.api.auth.util.last_login import (
    update_last_login_datetime_by_user_id,
)
from cndx_corp_back.api.auth.util.user_validation import validate_user_login
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.t_last_login_info import TLastLoginInfo
from cndx_corp_back.entity.t_session_info import TSessionInfo


def validate_and_update_session(
    db_session: scoped_session, session_id: str, use_db_timestamp: bool = True
) -> tuple[str, int, str] | None:
    """
    セッションIDを検証し、有効な場合は最終ログイン日時を更新

    Args:
        db_session: データベースセッション
        session_id: セッションID
        use_db_timestamp: Trueの場合、データベースサーバーの時間を使用（デフォルト: True）

    Returns:
        tuple[str, int, str] | None: エラーの場合 (エラーメッセージ, HTTPステータスコード, エラーコード)、
                                    正常な場合はNone
    """
    if not session_id:
        return ("セッションIDが提供されていません。", 401, "SESSION_ID_MISSING")

    print(f"session_id: {session_id}")
    # セッション情報を取得
    session_info = (
        db_session.query(TSessionInfo)
        .filter(
            TSessionInfo.session_id == session_id, TSessionInfo.delete_flg.is_(False)
        )
        .first()
    )

    if not session_info:
        return (
            "セッションが見つかりません。再度ログインしてください。",
            401,
            "SESSION_NOT_FOUND",
        )

    # is_activeがfalseの場合（シングルログイン違反）
    if session_info.is_active is False:
        return (
            "別のデバイスまたはブラウザでログインされたため、このセッションは無効になりました。再度ログインしてください。",
            401,
            "SINGLE_LOGIN_VIOLATION",
        )

    # ユーザー情報を取得してuser_statusをチェック
    user = (
        db_session.query(MUser)
        .filter(MUser.user_id == session_info.user_id, MUser.delete_flg.is_(False))
        .first()
    )

    if not user:
        return (
            "ログインできませんでした。登録されていないユーザーです。",
            404,
            "USER_NOT_FOUND",
        )

    # user_statusのチェック（ログイン後もステータス変更を検知）
    # validate_user_login関数を使用してステータスチェック
    # ロガーはcurrent_appから取得
    logger = current_app.logger
    validation_error = validate_user_login(
        db_session, user, session_info.user_id, logger
    )

    if validation_error:
        error_message, http_status = validation_error
        # エラーコードを追加（user_statusに基づいて決定）
        user_status = user.user_status

        # セッション検証用のメッセージに変換（「ログインできませんでした。」を削除）
        modified_message = error_message.replace(
            "ログインできませんでした。", ""
        ).strip()

        if user_status == "1":
            error_code = "USER_STATUS_REGISTERING"
        elif user_status == "2":
            error_code = "USER_STATUS_APPLIED"
        elif user_status == "3":
            error_code = "USER_STATUS_CANCELLED"
        elif user_status == "4":
            error_code = "USER_STATUS_INVALIDATED"
        elif user_status == "5":
            error_code = "USER_STATUS_DELETED"
        else:
            error_code = "USER_STATUS_INVALID"

        return (modified_message, http_status, error_code)

    # 最終ログイン情報を取得
    last_login_info = (
        db_session.query(TLastLoginInfo)
        .filter(
            TLastLoginInfo.user_id == session_info.user_id,
            TLastLoginInfo.delete_flg.is_(False),
        )
        .first()
    )

    if last_login_info:
        # 現在時刻を取得
        if use_db_timestamp:
            current_datetime = db_session.query(func.now()).scalar()
        else:
            current_datetime = datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo"))

        # タイムゾーンを統一（データベースの時刻がnaiveの場合、JSTに変換）
        if last_login_info.last_login_datetime.tzinfo is None:
            # naive datetimeの場合はJSTとして扱う
            last_login_datetime = last_login_info.last_login_datetime.replace(
                tzinfo=ZoneInfo("Asia/Tokyo")
            )
        else:
            last_login_datetime = last_login_info.last_login_datetime

        if current_datetime.tzinfo is None:
            current_datetime = current_datetime.replace(tzinfo=ZoneInfo("Asia/Tokyo"))

        # セッションタイムアウト時間を取得（環境変数から、デフォルト3時間）
        session_timeout = current_app.config.get(
            "SESSION_TIMEOUT", datetime.timedelta(hours=3)
        )

        # 最終ログイン日時から経過時間を計算
        elapsed_time = current_datetime - last_login_datetime

        # セッションタイムアウト時間を超えている場合
        if elapsed_time > session_timeout:
            return (
                f"セッションがタイムアウトしました（最終アクセスから{elapsed_time.total_seconds() / 3600:.1f}時間経過）。再度ログインしてください。",
                401,
                "SESSION_TIMEOUT",
            )

    # is_activeがtrueかつタイムアウトしていない場合、最終ログイン日時を更新
    update_last_login_datetime_by_user_id(
        db_session,
        session_info.user_id,
        session_id=session_id,
        use_db_timestamp=use_db_timestamp,
    )

    # 正常な場合はNoneを返す
    return None
