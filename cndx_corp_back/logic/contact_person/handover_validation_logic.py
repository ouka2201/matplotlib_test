"""営業担当引継の入力・権限検証。"""

import re
from datetime import datetime

from cndx_corp_back.constant.handover_constants import (
    HANDOVER_ALLOWED_ROLES,
    HANDOVER_ID_PATTERNS,
    HANDOVER_INVALID_INPUT,
    HANDOVER_PERMISSION_DENIED,
    HANDOVER_REGISTRANT_MISMATCH,
    HANDOVER_TYPE_INDIVIDUAL,
)


def _validate_schedule(schedule: object) -> None:
    if not isinstance(schedule, str) or not re.fullmatch(r"[0-9]{8}", schedule):
        raise ValueError("handover_schedule_dateが不正です。")
    try:
        datetime.strptime(schedule, "%Y%m%d")
    except ValueError as error:
        raise ValueError("handover_schedule_dateが不正です。") from error


def _validate_company_numbers(numbers: object) -> list[str]:
    if not isinstance(numbers, list) or any(
        not isinstance(number, str) or not re.fullmatch(r"[0-9]{13}", number)
        for number in numbers
    ):
        raise ValueError("corp_number_listが不正です。")
    return list(dict.fromkeys(numbers))


def validate_handover(data: dict, user_context: dict, handover_type: str) -> list[str]:
    """入力を検証し、個別引継の重複を除いた法人番号を返す。"""
    if not isinstance(data, dict):
        raise ValueError(HANDOVER_INVALID_INPUT)
    if (
        not isinstance(user_context, dict)
        or (user_context.get("org_type_code"), str(user_context.get("role")))
        not in HANDOVER_ALLOWED_ROLES
    ):
        raise PermissionError(HANDOVER_PERMISSION_DENIED)
    for key, pattern in HANDOVER_ID_PATTERNS.items():
        if not isinstance(data.get(key), str) or not re.fullmatch(pattern, data[key]):
            raise ValueError(f"{key}が不正です。")
    if data["user_id"] != user_context.get("user_id") or data[
        "org_id"
    ] != user_context.get("org_id"):
        raise PermissionError(HANDOVER_REGISTRANT_MISMATCH)
    if data.get("handover_type") != handover_type:
        raise ValueError("handover_typeが不正です。")
    if not isinstance(data.get("report_data_flg"), bool):
        raise ValueError("report_data_flgが不正です。")
    _validate_schedule(data.get("handover_schedule_date"))
    if handover_type == HANDOVER_TYPE_INDIVIDUAL:
        return _validate_company_numbers(data.get("corp_number_list"))
    return []
