"""個別引継の企業検索と予定済み対象の取得。"""

import re

from sqlalchemy import bindparam, text

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.constant.handover_constants import (
    HANDOVER_ALLOWED_ROLES,
    HANDOVER_ID_PATTERNS,
    HANDOVER_PERMISSION_DENIED,
    HANDOVER_STATUS_PLANNED,
)
from cndx_corp_back.query.handover_query import (
    SELECT_INDIVIDUAL_HANDOVER_COMPANIES,
    SELECT_SCHEDULED_COMPANIES,
)


def _scope(user_context: dict) -> dict:
    org_type = user_context.get("org_type_code")
    org_id = user_context.get("org_id")
    if (org_type, str(user_context.get("role"))) not in HANDOVER_ALLOWED_ROLES:
        raise PermissionError(HANDOVER_PERMISSION_DENIED)
    if not isinstance(org_id, str) or not re.fullmatch(HANDOVER_ID_PATTERNS["org_id"], org_id):
        raise PermissionError(HANDOVER_PERMISSION_DENIED)
    if org_type == "02" and not re.match(r"BNK[0-9]{4}", org_id):
        raise PermissionError(HANDOVER_PERMISSION_DENIED)
    return {"is_ep_admin": org_type == "01", "bank_pattern": f"{org_id[:7]}%"}


def _id(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not re.fullmatch(HANDOVER_ID_PATTERNS[key], value):
        raise ValueError(f"{key}が不正です。")
    return value


def search_individual_companies(data: dict, user_context: dict) -> list[dict]:
    params = {**_scope(user_context), "from_user": _id(data, "handover_from_user_id")}
    for key, limit in (("company_name", 100), ("corporate_number", 13), ("company_address", 120)):
        value = data.get(key, "")
        if not isinstance(value, str) or len(value) > limit or "\x00" in value:
            raise ValueError(f"{key}が不正です。")
        if key == "corporate_number" and value and not re.fullmatch(r"[0-9]+", value):
            raise ValueError(f"{key}が不正です。")
        escaped = value.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        params[key] = f"%{escaped}%"
    with get_scoped_session() as session:
        rows = session.execute(text(SELECT_INDIVIDUAL_HANDOVER_COMPANIES), params).mappings().all()
        return [dict(row) for row in rows]


def select_scheduled_companies(data: dict, user_context: dict) -> list[str]:
    params = {
        **_scope(user_context),
        "to_org": _id(data, "handover_to_org_id"),
        "to_user": _id(data, "handover_to_user_id"),
        "status": HANDOVER_STATUS_PLANNED,
    }
    numbers = data.get("corp_number_list", [])
    if not isinstance(numbers, list) or any(
        not isinstance(number, str) or not re.fullmatch(r"[0-9]{13}", number)
        for number in numbers
    ):
        raise ValueError("corp_number_listが不正です。")
    if not numbers:
        return []
    params["numbers"] = list(dict.fromkeys(numbers))
    query = text(SELECT_SCHEDULED_COMPANIES).bindparams(bindparam("numbers", expanding=True))
    with get_scoped_session() as session:
        return list(session.execute(query, params).scalars().all())
