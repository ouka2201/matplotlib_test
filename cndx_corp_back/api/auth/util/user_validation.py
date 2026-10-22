"""
ユーザー認証・バリデーション関連のユーティリティ関数
"""

import re

from sqlalchemy.orm import scoped_session

from cndx_corp_back.entity.m_user_entity import MUser


def get_user_by_email(session: scoped_session, email_address: str):
    """
    メールアドレスでユーザーを検索

    Args:
        session: データベースセッション
        email_address: メールアドレス

    Returns:
        MUser: ユーザーエンティティ（見つからない場合はNone）
    """
    if not is_email(email_address):
        return (
            session.query(MUser)
            .filter(MUser.user_id == email_address, MUser.delete_flg.is_(False))
            .first()
        )
    return (
        session.query(MUser)
        .filter(MUser.email_address == email_address, MUser.delete_flg.is_(False))
        .first()
    )


def is_email(value: str) -> bool:
    return re.match(r"^[^@]+@[^@]+\.[^@]+$", value) is not None


def _add_line_breaks(message: str) -> str:
    """
    メッセージ内の「。」の後に改行を追加

    Args:
        message: 元のメッセージ

    Returns:
        改行が追加されたメッセージ
    """
    # 「。」の後に改行文字を追加（最後の改行は削除）
    return message.replace("。", "。\n").rstrip("\n")


def validate_user_login(session, login_user, name_id, logger):
    """
    ユーザーのログイン可否を検証

    Args:
        session: データベースセッション
        login_user: MUserエンティティ（Noneの可能性あり）
        name_id: メールアドレスまたはユーザーID（ログ用）
        logger: ロガー

    Returns:
        tuple: (error_message, http_status) のタプル。エラーがない場合はNoneを返す
    """
    # メールアドレスがユーザー情報に存在しない場合
    if not login_user:
        logger.warning(f"ユーザーが見つかりません: {name_id}")
        return (
            _add_line_breaks(
                "ログインできませんでした。登録されていないユーザーです。"
            ),
            403,
        )

    # 削除フラグがTrueの場合
    if login_user.delete_flg:
        logger.warning(f"削除されたユーザーがログインを試みました: {name_id}")
        return (
            _add_line_breaks(
                "ログインできませんでした。登録されていないユーザーです。"
            ),
            403,
        )

    # user_statusのチェック
    # ステータス定義:
    # "0": 有効
    # "1": 登録処理中
    # "2": 申請受付済
    # "3": 取消
    # "4": 失効中（強制ログアウト）
    # "5": 削除ステータス
    user_status = login_user.user_status
    if user_status == "0":
        # 有効なステータス - チェックを通過
        pass
    elif user_status == "1":
        logger.warning(f"登録処理中のユーザーがログインを試みました: {name_id}")
        return (
            _add_line_breaks(
                "ログインできませんでした。登録処理中のユーザーです。利用可能になるまでお待ちください。"
            ),
            403,
        )
    elif user_status == "2":
        logger.warning(f"申請受付済のユーザーがログインを試みました: {name_id}")
        return (
            _add_line_breaks(
                "ログインできませんでした。申請受付済のユーザーです。利用可能になるまでお待ちください。"
            ),
            403,
        )
    elif user_status == "3":
        logger.warning(f"取消されたユーザーがログインを試みました: {name_id}")
        return (
            _add_line_breaks("ログインできませんでした。取消されたユーザーです。"),
            403,
        )
    elif user_status == "4":
        logger.warning(f"失効中のユーザーがログインを試みました: {name_id}")
        return (
            _add_line_breaks("ログインできませんでした。失効中のユーザーです。"),
            403,
        )
    elif user_status == "5":
        logger.warning(f"削除されたユーザーがログインを試みました: {name_id}")
        return (
            _add_line_breaks("ログインできませんでした。削除されたユーザーです。"),
            403,
        )
    else:
        # その他のステータスの場合（想定外の値）
        logger.warning(
            f"無効なステータスのユーザーがログインを試みました: {name_id}, status: {user_status}"
        )
        return (
            _add_line_breaks(
                "ログインできませんでした。登録されていないユーザーです。"
            ),
            403,
        )

    # すべてのチェックを通過した場合
    return None
