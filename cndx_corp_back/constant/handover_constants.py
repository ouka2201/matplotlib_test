"""営業担当引継の業務コードとメッセージ。"""

HANDOVER_TYPE_INDIVIDUAL = "0"
HANDOVER_TYPE_BULK = "1"
HANDOVER_STATUS_PLANNED = "1"
HANDOVER_ALLOWED_ROLES = frozenset({("01", "0"), ("02", "9")})

HANDOVER_INVALID_INPUT = "入力値が不正です。"
HANDOVER_PERMISSION_DENIED = "利用権限がありません。"
HANDOVER_REGISTRANT_MISMATCH = "登録者情報がログイン情報と一致しません。"
HANDOVER_UNASSIGNED_COMPANY = "引継元担当者に紐づかない法人番号が含まれています。"
HANDOVER_ALREADY_PROCESSED = "実施済みの引継予定は変更できません。"
HANDOVER_SYSTEM_ERROR = "システムエラーが発生しました。"

HANDOVER_ID_PATTERNS = {
    "handover_from_org_id": r"[0-9A-Z]{1,20}",
    "handover_from_user_id": r"[0-9A-Z]{1,8}",
    "handover_to_org_id": r"[0-9A-Z]{1,20}",
    "handover_to_user_id": r"[0-9A-Z]{1,8}",
    "user_id": r"[0-9A-Z]{1,8}",
    "org_id": r"[0-9A-Z]{1,20}",
}
