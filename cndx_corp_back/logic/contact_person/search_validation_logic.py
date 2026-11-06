"""営業担当検索の入力と認証済み検索範囲を検証する。"""

import re

from cndx_corp_back.constant.handover_constants import (
    HANDOVER_ALLOWED_ROLES,
    HANDOVER_ID_PATTERNS,
    HANDOVER_PERMISSION_DENIED,
)


def validate_manager_search(data: dict, user_context: dict) -> dict:
    """検索条件と権限を検証し、SQLに渡す検索パラメータを作る。

    検索範囲は認証済みの所属・権限から決定する。検索文字列に含まれる
    LIKEのワイルドカードは、通常の文字として検索できるように処理する。

    Args:
        data: 検索文字列、検索対象、検索者の所属・権限情報。
        user_context: 認証済みユーザーの所属組織と権限情報。

    Returns:
        検索パターン、検索対象、組織の検索範囲を指定する辞書。

    Raises:
        PermissionError: 利用権限や所属が不正、または検索者情報が一致しない場合。
        ValueError: 検索タイプや検索文字列が不正な場合。
    """
    org_type = user_context.get("org_type_code")
    role = str(user_context.get("role"))
    if (org_type, role) not in HANDOVER_ALLOWED_ROLES:
        raise PermissionError(HANDOVER_PERMISSION_DENIED)
    org_id = user_context.get("org_id")
    if not isinstance(org_id, str) or not re.fullmatch(
        HANDOVER_ID_PATTERNS["org_id"], org_id
    ):
        raise PermissionError(HANDOVER_PERMISSION_DENIED)
    # クライアントが送る権限情報は認可には使わず、ログイン情報との一致を確認する。
    expected = {"org_id": org_id, "org_type_code": org_type, "user_role": role}
    if any(data.get(key) != value for key, value in expected.items()):
        raise PermissionError("検索者情報がログイン情報と一致しません。")
    search_type = data.get("search_type")
    if search_type not in ("email_address", "all"):
        raise ValueError("検索タイプが不正です。")
    query = data.get("search_query", "")
    if not isinstance(query, str) or "\x00" in query:
        raise ValueError("検索文字列が不正です。")
    bank_prefix = ""
    if org_type == "02":
        if not re.match(r"BNK[0-9]{4}", org_id):
            raise PermissionError(HANDOVER_PERMISSION_DENIED)
        bank_prefix = org_id[:7]
    # LIKEのワイルドカードも入力文字として検索する。
    escaped = query.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return {
        "pattern": f"%{escaped}%",
        "search_all": search_type == "all",
        "is_ep_admin": org_type == "01",
        "bank_pattern": f"{bank_prefix}%",
    }
