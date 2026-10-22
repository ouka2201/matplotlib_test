from enum import Enum


class DBoperation(Enum):
    """
    DB操作を定義するEnumクラス。

    - NONE: 検索不要の場合。
    - FETCHALL: 全件検索の場合。
    - FETCHONE: 1件検索の場合。
    """

    NONE = ""
    FETCHALL = "fetchall"
    FETCHONE = "fetchone"


class DBURL(Enum):
    """
    DB接続のモードを定義するEnumクラス。

    - DB_CONNECTOR_DEV_URL: 開発環境のURLを表します。
    """

    DB_CONNECTOR_IT_URL = "conf/postgre_config_for_it.json"
    DB_CONNECTOR_MAINT_URL = "conf/postgre_config_for_maint.json"
    DB_CONNECTOR_PROD_URL = "conf/postgre_config_for_prod.json"
    DB_CONNECTOR_TEST_URL = "conf/postgre_config_for_test.json"
    DB_CONNECTOR_DEV_URL = "conf/postgre_config_for_dev.json"
    DB_CONNECTOR_LOCAL_URL = "conf/postgre_config_for_local.json"


class RunMode(Enum):
    """
    実行環境のモードを定義するEnumクラス。

    - DEV: 開発環境を表します。
    - STG: ステージング環境を表します。
    - PROD: 本番環境を表します。
    """

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class EncodingMethod(Enum):
    """エンコーディング方法"""

    UTF8 = "utf-8"
    SJIS = "sjis"
    UTF8BOM = "utf-8-sig"


class MstTable(Enum):
    """マスタテーブル"""

    JP_INDUSTRY = "DB_COMMON.M_JP_ST_INDUSTRY_CLASSIFICATION"
    MINOR_CATE = "DB_COMMON.ACTIVITY_MINOR_CATEGORY_MST"
    CALC_LOGIC = "DB_CORP.M_CALCULATION_LOGIC"
    ELEC_FCTR = "DB_CORP.M_ELECTRICITY_CONVERSION_COEFFICIENT"
    USER = "DB_CORP.M_USER"
    # PREFECTURE = "DB_CORP.M_PREFECTURE"
    MCODE = "DB_CORP.M_CORP_CODE_INFO"


MST_LIST: dict[str, list[str]] = {
    MstTable.JP_INDUSTRY.value: [
        "DIVISION_CODE",
        "MAJOR_GROUP_CODE",
        "GROUP_CODE",
        "INDUSTRY_CODE",
        "DIVISION_NAME",
        "MAJOR_GROUP_NAME",
        "GROUP_NAME",
        "INDUSTRY_NAME",
    ],
    # MstTable.MINOR_CATE.value: [
    #     "REPORT_YEAR",
    #     "MAJOR_CATEGORY_ID",
    #     "MIDDLE_CATEGORY_ID",
    #     "MINOR_CATEGORY_ID",
    #     "MINOR_CATEGORY_NM",
    #     "UNIT",
    #     "CONVERSION_COEF",
    #     "ENERGY_CO2_EMISSION_COEF",
    # ],
    # MstTable.CALC_LOGIC.value: [
    #     "LOGIC_ID",
    #     "NAME",
    #     "FORMULA",
    #     "VARIABLES",
    #     "TARGET_YEAR",
    # ],
    # MstTable.USER.value: [
    #     "USER_ID",
    #     "USER_NAME",
    #     "COMPANY_NAME",
    #     "DEPARTMENT_ID",
    #     "DEPARTMENT_NAME",
    #     "USER_PASSWORD",
    #     "ORG_ID",
    #     "USER_ROLE",
    # ],
    # MstTable.ELEC_FCTR.value: [
    #     "REGISTRATION_NUMBER",
    #     "FISCAL_YEAR",
    #     "START_DATE",
    #     "END_DATE",
    #     "ADJUSTED_EMISSION_FACTOR",
    # ],
    # MstTable.PREFECTURE.value: [
    #     "PREF_CD",
    #     "PREF_NM",
    # ],
    # MstTable.MCODE.value: [
    #     "CODE_TYPE",
    #     "CODE",
    #     "TARGET_YEAR",
    #     "JP_CODE_NAME",
    # ],
}
"""格納対象のマスタデータリスト"""

ENERGY_CODE_TO_ENG = {
    "0100020000": "import_raw_charcoal",
    "0100310000": "coking_coal",
    "0100320000": "pci_coal",
    "0100010000": "import_ordinary_charcoal",
    "0100330000": "domestic_standard_coal",
    "0100030000": "import_smokeless_coal",
    "0100070000": "coal_coke",
    "0100080000": "petroleum_coke",
    "0100350000": "fcc_coke",
    "0100170000": "coal_tar",
    "0100160000": "petroleum_asphalt",
    "0100140000": "crude_oil_condensate",
    "0100150000": "crude_oil_condensate_except",
    "0100090000": "gasoline",
    "0100180000": "naphtha",
    "0100300000": "jet_fuel",
    "0100100000": "kerosene",
    "0100110000": "light_oil",
    "0100120000": "heavy_oil_a",
    "0100130000": "heavy_oil_bc",
    "0100360000": "lubricating_oil",
    "0100190000": "lpg",
    "0100200000": "petroleum_hydrocarbon_gas",
    "0100210000": "lng",
    "0100220000": "natural_gas",
    "0100240000": "coke_oven_gas",
    "0100250000": "blast_furnace_gas",
    "0100340000": "power_generation_blast_furnace_gas",
    "0100260000": "converter_gas",
    "0100230000": "city_gas",
    "0300010000": "industrial_steam",
    "0300020000": "industrial_except_steam",
    "0300030000": "warm_water",
    "0300040000": "cold_water",
    "0200010001": "electric_power",
    "0200010011": "electric_power",
    "6800030000": "crude_oil_condensate_ngl",
}
"""エネルギーコードから物理名に変換"""

building_columns = [
    "corporate_number",
    "org_id",
    "agreement_category",
    "building_id",
    "building_name",
    "location_identifier_name",
    "building_address_prefecture",
    "building_address_city",
    "industry_code",
    "industry_name",
    "ep_customer_number",
    "supply_point_number",
    "benchmark_denom",
    "benchmark_val",
    "building_consent_flag",
    "delete_flg",
]

corporate_details_columns = ["corporate_number", "org_id", "agreement_category"]
