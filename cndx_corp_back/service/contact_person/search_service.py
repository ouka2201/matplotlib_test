"""営業担当検索APIの照会処理。"""

from sqlalchemy import text

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.logic.contact_person.search_validation_logic import (
    validate_manager_search,
)
from cndx_corp_back.query.contact_person_search_query import SELECT_HANDOVER_MANAGERS


def search_managers(data: dict, user_context: dict) -> list[dict]:
    params = validate_manager_search(data, user_context)
    with get_scoped_session() as session:
        rows = session.execute(text(SELECT_HANDOVER_MANAGERS), params).mappings().all()
        return [dict(row) for row in rows]
