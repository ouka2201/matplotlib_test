"""担当者引継ぎ実行バッチで使用する定数。"""

HANDOVER_STATUS_DONE = "0"  # 完了
HANDOVER_STATUS_PLANNED = "1"  # 予定
HANDOVER_STATUS_CANCELLED = "2"  # 引継中止
HANDOVER_STATUS_ERROR = "3"  # 登録エラー

HANDOVER_TYPE_INDIVIDUAL = "0"  # 個別
HANDOVER_TYPE_BULK = "1"  # 一括

HANDOVER_DATA_QUERY_FILES = {
    "monthly_building": "update_handover_monthly_building.sql",
    "annual_building": "update_handover_annual_building.sql",
    "monthly_corporate": "update_handover_monthly_corporate.sql",
    "annual_corporate": "update_handover_annual_corporate.sql",
    "report_storage": "update_handover_report_storage.sql",
    "building": "update_handover_building.sql",
    "cn_application": "update_handover_cn_application.sql",
    "building_info": "update_handover_building_info.sql",
}
