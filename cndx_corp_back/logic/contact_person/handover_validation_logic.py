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
    """実施予定日が8桁の文字列で、実在する日付かを確認する。

    Args:
        schedule: YYYYMMDD形式の実施予定日。

    Raises:
        ValueError: 形式が不正、または存在しない日付の場合。
    """
    if not isinstance(schedule, str) or not re.fullmatch(r"[0-9]{8}", schedule):
        raise ValueError("handover_schedule_dateが不正です。")
    try:
        datetime.strptime(schedule, "%Y%m%d")
    except ValueError as error:
        raise ValueError("handover_schedule_dateが不正です。") from error


def _validate_company_numbers(numbers: object) -> list[str]:
    """法人番号の形式を検証し、入力順を保って重複を除く。

    Args:
        numbers: 13桁の半角数字で表した法人番号のリスト。

    Returns:
        重複を除いた法人番号のリスト。空のリストはそのまま返す。

    Raises:
        ValueError: リスト以外が渡された、または法人番号の形式が不正な場合。
    """
    if not isinstance(numbers, list) or any(
        not isinstance(number, str) or not re.fullmatch(r"[0-9]{13}", number)
        for number in numbers
    ):
        raise ValueError("corp_number_listが不正です。")
    return list(dict.fromkeys(numbers))


def validate_handover(data: dict, user_context: dict, handover_type: str) -> list[str]:
    """引継登録の入力と利用権限を検証する。

    Args:
        data: 引継元・引継先、実施予定日、登録者などの入力情報。
        user_context: 認証済みユーザーのID、所属組織、権限情報。
        handover_type: 呼び出されたAPIの引継区分。個別は「0」、一括は「1」。

    Returns:
        個別引継の場合は重複を除いた法人番号のリスト。一括引継の場合は
        空のリストを返し、対象企業の取得は登録処理で行う。

    Raises:
        PermissionError: 利用権限がない、または登録者情報が一致しない場合。
        ValueError: ID、引継区分、日付などの入力値が不正な場合。
    """
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
