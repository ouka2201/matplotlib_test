"""担当者引継ぎ実行バッチで使用する定数。"""

HANDOVER_STATUS_PLANNED = "1"
HANDOVER_STATUS_DONE = "0"
HANDOVER_STATUS_ERROR = "3"

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
