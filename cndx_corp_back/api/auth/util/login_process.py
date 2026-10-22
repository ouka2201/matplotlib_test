"""
ログイン処理の共通関数
"""

from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import scoped_session

from cndx_corp_back.entity.m_user_entity import MUser

from .jwt_token import create_jwt_payload
from .last_login import update_last_login_datetime_by_user_id
from .session_info import create_or_update_session_info
from .user_permissions import get_user_permissions
from .user_validation import get_user_by_email, validate_user_login


def process_user_login(
    session: scoped_session,
    email_address: str,
    logger,
    password: Optional[str] = None,
    use_db_timestamp: bool = False,
    add_error_code: bool = False,
) -> Tuple[Optional[MUser], Optional[Tuple[str, int, Optional[Dict[str, str]]]]]:
    """
    ユーザーログイン処理の共通関数

    Args:
        session: データベースセッション
        email_address: メールアドレス
        logger: ロガー
        password: パスワード（オプション、提供された場合は検証）
        use_db_timestamp: データベースタイムスタンプを使用するか
        add_error_code: エラーレスポンスにerror_codeを追加するか

    Returns:
        tuple: (login_user, error_info)
            - login_user: ログイン成功時のユーザーエンティティ、エラー時はNone
            - error_info: エラー時の (error_message, http_status, error_response_dict)、成功時はNone
    """
    # ユーザーを検索
    login_user = get_user_by_email(session, email_address)

    # ユーザーのログイン可否を検証
    validation_error = validate_user_login(session, login_user, email_address, logger)
    if validation_error:
        error_message, http_status = validation_error
        logger.warning(f"ユーザーバリデーション失敗: {error_message}")

        error_response = {"message": error_message}

        # エラーコードを追加（SAML認証の場合など）
        if add_error_code and login_user:
            user_status = login_user.user_status
            status_map = {
                "1": "USER_STATUS_REGISTERING",
                "2": "USER_STATUS_APPLIED",
                "3": "USER_STATUS_CANCELLED",
                "4": "USER_STATUS_INVALIDATED",
                "5": "USER_STATUS_DELETED",
            }
            error_response["error_code"] = status_map.get(
                user_status, "USER_STATUS_INVALID"
            )

        return None, (error_message, http_status, error_response)

    # パスワードチェック（提供された場合）
    if password is not None:
        if login_user.user_password != password:
            logger.error(f"パスワードが間違っています: {email_address}")
            return None, ("パスワードが間違っています。", 401, None)

    return login_user, None


def prepare_user_data(login_user: MUser) -> Dict[str, str]:
    """
    ユーザーデータを準備

    Args:
        login_user: ユーザーエンティティ

    Returns:
        dict: ユーザーデータ辞書
    """
    return {
        "user_id": login_user.user_id,
        "email_address": login_user.email_address,
        "user_name": login_user.user_name,
        "org_id": login_user.org_id,
        "user_role": login_user.user_role,
    }


def complete_login_process(
    session: scoped_session, login_user: MUser, use_db_timestamp: bool = False
) -> Tuple[str, Dict[str, Any]]:
    """
    ログイン処理を完了（セッション作成、ログイン更新、権限取得、JWTペイロード作成）

    Args:
        session: データベースセッション
        login_user: ユーザーエンティティ
        use_db_timestamp: データベースタイムスタンプを使用するか

    Returns:
        tuple: (session_id, payload)
    """
    # ユーザーデータを準備
    user_data = prepare_user_data(login_user)

    # セッション情報を登録・更新（session_idを生成）
    session_id = create_or_update_session_info(
        session, login_user.user_id, use_db_timestamp=use_db_timestamp
    )

    # 最終ログイン日時を更新
    update_last_login_datetime_by_user_id(
        session, login_user.user_id, session_id, use_db_timestamp=use_db_timestamp
    )

    # 権限情報を取得
    auth_info = get_user_permissions(session, login_user.org_id, login_user.user_role)

    # JWTペイロードを作成
    payload = create_jwt_payload(user_data, auth_info)

    return session_id, payload
