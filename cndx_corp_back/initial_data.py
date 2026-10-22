from datetime import datetime

# 共通項目
COMMON_ITEMS = {
    "deleteFlag": 0,
    "insertName": "SYSTEM",
    "insertDatetime": datetime.now(),
    "updateName": "SYSTEM",
    "updateDatetime": datetime.now(),
}

# システム制御マスタ
INITIAL_SYSTEM_CONTROL_MST = [
    {
        "itemCd": "001",
        "itemName": "対象年度",
        "itemValue": "2024",
        **COMMON_ITEMS,
    },
    {
        "itemCd": "002",
        "itemName": "電気事業者公表回数",
        "itemValue": "2",
        **COMMON_ITEMS,
    },
]

# 電気事業者エリアマスタ
INITIAL_ELECTRIC_AREA_MST = [
    {
        "areaCode": "01",
        "areaName": "北海道",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "02",
        "areaName": "東北",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "03",
        "areaName": "東京",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "04",
        "areaName": "北陸",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "05",
        "areaName": "中部",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "06",
        "areaName": "関西",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "07",
        "areaName": "中国",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "08",
        "areaName": "四国",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "09",
        "areaName": "九州",
        **COMMON_ITEMS,
    },
    {
        "areaCode": "10",
        "areaName": "沖縄",
        **COMMON_ITEMS,
    },
]

# 電気事業者マスタ
INITIAL_COMPANY_MST = [
    {
        "companyId": "01",
        "companyNm": "東京電力ホールディングス株式会社",
        "companyNmAbbr": "HD",
        "legalPersonNumber": "1234567890001",
        "companyEngNm": "Tokyo Electric Power Holdings, Inc.",
        **COMMON_ITEMS,
    },
    {
        "companyId": "02",
        "companyNm": "東京電力フュエル＆パワー株式会社",
        "companyNmAbbr": "FP",
        "legalPersonNumber": "1234567890002",
        "companyEngNm": "Tokyo Electric Power Fuel & Power Co., Ltd.",
        **COMMON_ITEMS,
    },
    {
        "companyId": "03",
        "companyNm": "東京電力パワーグリッド株式会社",
        "companyNmAbbr": "PG",
        "legalPersonNumber": "1234567890003",
        "companyEngNm": "Tokyo Electric Power Power Grid Co., Ltd.",
        **COMMON_ITEMS,
    },
    {
        "companyId": "04",
        "companyNm": "東京電力エナジーパートナー株式会社",
        "companyNmAbbr": "EP",
        "legalPersonNumber": "1234567890004",
        "companyEngNm": "Tokyo Electric Power Energy Partners Co., Ltd.",
        **COMMON_ITEMS,
    },
    {
        "companyId": "05",
        "companyNm": "東京電力リニューアブルパワー株式会社",
        "companyNmAbbr": "RP",
        "legalPersonNumber": "1234567890005",
        "companyEngNm": "Tokyo Electric Power Renewable Power Co., Ltd.",
        **COMMON_ITEMS,
    },
]


MONTH_ENERGY_USAGE = [
    {
        "buildingEnergyInfoId": "dummy",
        "reportTargetYear": 2024,
        "targetMonth": "01",
        "activityItemLargeCategoryId": "99",
        "activityItemMediamCategoryId": "9999",
        "activityItemSmallCategoryId": "9999",
        "branchNumber": "00",
        "usageAmt": 1.12,
        "soldByProductAmt": 1.12,
        "boughtUnusedHeatAmt": 1.12,
        "supplyUsageAmt": 1.12,
        "insertName": "test",
        "insertDatetime": "2024/01/01T00:00:00",
        "updateName": None,
        "updateDatetime": None,
    },
]
