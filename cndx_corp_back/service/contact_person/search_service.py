"""営業担当検索APIの照会処理。"""

from sqlalchemy import text

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.logic.contact_person.search_validation_logic import (
    validate_manager_search,
)
from cndx_corp_back.query.contact_person_search_query import SELECT_HANDOVER_MANAGERS


def search_managers(data: dict, user_context: dict) -> list[dict]:
    """ログインユーザーが参照できる範囲で営業担当者を検索する。

    Args:
        data: 検索文字列、検索対象、検索者の所属・権限情報。
        user_context: 認証済みユーザーの所属組織と権限情報。

    Returns:
        担当者のID、氏名、メールアドレス、所属組織を含む辞書のリスト。
        該当する担当者がいない場合は空のリスト。

    Raises:
        PermissionError: 利用権限がない、または検索者情報が一致しない場合。
        ValueError: 検索タイプや検索文字列が不正な場合。
    """
    params = validate_manager_search(data, user_context)
    with get_scoped_session() as session:
        rows = session.execute(text(SELECT_HANDOVER_MANAGERS), params).mappings().all()
        return [dict(row) for row in rows]
