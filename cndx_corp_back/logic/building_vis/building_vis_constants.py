from enum import Enum
from types import SimpleNamespace

# シート名列挙
class SheetName(Enum):
    INFO = "情報"
    BUILDING_INFO = "物件情報"
    ENERGY_USAGE_BY_TYPE = "種別ごとエネルギー使用量"
    HEAT_CONVERSION_VALUE_BY_TYPE = "種別ごと熱量換算値"
    BASE_CO2_EMISSIONS_BY_TYPE = "種別ごとCO2基礎排出量"
    ADJUSTED_CO2_EMISSIONS_BY_TYPE = "種別ごとCO2調整後排出量"
    HEAT_CONVERSION_FACTOR = "熱量換算係数"
    BASE_CO2_EMISSION_FACTOR = "CO2基礎排出係数"
    ADJUSTED_CO2_EMISSION_FACTOR = "CO2調整後排出係数"
    COMPANY_INFO = "企業情報"
    LOCATION_INFO = "拠点情報"
    CREDITS_INFO = "証書・クレジット"
    UNIT_DENOMINATOR_INFO = "（任意）原単位分母"
    UNIT_INFO = "原単位分母"

class BuildingSheetName(Enum):
    AGGREMENT_DOC = "同意書"
    ATTACHMENT = "別紙"

# シート毎のマッピング設定用
sheet_mapping = {
    SheetName.BUILDING_INFO.value: {
        "row_attr":"LOCATION_IDENTIFIER_CODE", # 拠点識別番号
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            "郵便番号": "ZIP_CODE",
            "都道府県": "ADDRESS_PREFECTURE",
            "自治体コード": "MUNICIPALITY_CODE",
            "市区町村番地": "ADDRESS_CITY",
            "建物名": "BUILDING_NAME",
            "延床面積(m2)": "GROSS_FLOOR_AREA",
        }

    },
    SheetName.UNIT_INFO.value: {
        "row_attr":"site_gross_floor_area", # 拠点延床面積
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "原単位分母名": "UNIT_DENO_NAME",
        }

    },
    SheetName.ENERGY_USAGE_BY_TYPE.value: {
        "row_attr": "unit_origin",       # row の属性名
        "unit_col": "unit_origin",      # energy_df の単位カラム
        # "value_col": "energy_usage_monthly",    # energy_df の値カラム
        "value_col": "energy_quantity", 
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            # "エネルギー分類": "energy_name_for_coefficient_matching",
            "エネルギー分類": "energy_name_jp",
            "供給会社": "supplier_name",
            "区分": "day_category",
            # "単位": "energy_unit_original",
            "単位": "unit_origin",
            "お客様番号": "ep_customer_number",
        },
    },
    SheetName.HEAT_CONVERSION_VALUE_BY_TYPE.value: {
        "row_attr":"HEAT_CONVERTED_ENERGY_UNIT",  # row の属性名
        "unit_col": "HEAT_CONVERTED_ENERGY_UNIT",  # energy_df の単位カラム
        "value_col": "HEAT_CONVERTED_ENERGY_USAGE_MONTHLY",  # energy_df の値カラム
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            # "エネルギー分類": "energy_name_for_coefficient_matching",
            "エネルギー分類": "energy_name_jp",
            "供給会社": "supplier_name",
            "区分": "day_category",
            "単位": "HEAT_CONVERTED_ENERGY_UNIT",
        },
    },
    SheetName.BASE_CO2_EMISSIONS_BY_TYPE.value: {
        "row_attr":"CO2_BASE_EMISSIONS_UNIT",
        "unit_col": "CO2_BASE_EMISSIONS_UNIT",
        "value_col": "CO2_BASE_EMISSIONS",
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            # "エネルギー分類": "energy_name_for_coefficient_matching",
            "エネルギー分類": "energy_name_jp",
            "供給会社": "supplier_name",
            "区分": "day_category",
            "単位": "CO2_BASE_EMISSIONS_UNIT",
            # 熱量換算係数データソース	HEAT_CONVERSION_COEFFICIENT_SOURCE
        },
    },
    SheetName.ADJUSTED_CO2_EMISSIONS_BY_TYPE.value: {
        "row_attr":"CO2_ADJUSTED_EMISSIONS_UNIT",
        "unit_col": "CO2_ADJUSTED_EMISSIONS_UNIT",
        "value_col": "CO2_ADJUSTED_EMISSIONS",
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            # "エネルギー分類": "energy_name_for_coefficient_matching",
            "エネルギー分類": "energy_name_jp",
            "供給会社": "supplier_name",
            "区分": "day_category",
            "単位": "CO2_ADJUSTED_EMISSIONS_UNIT",
        },
    },
    SheetName.HEAT_CONVERSION_FACTOR.value: {
        "row_attr":"HEAT_CONVERSION_COEFFICIENT_UNIT",
        "unit_col": "HEAT_CONVERSION_COEFFICIENT_UNIT",
        "value_col": "HEAT_CONVERSION_COEFFICIENT",
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            # "エネルギー分類": "energy_name_for_coefficient_matching",
            "エネルギー分類": "energy_name_jp",
            "供給会社": "supplier_name",
            "区分": "day_category",
            "単位": "HEAT_CONVERSION_COEFFICIENT_UNIT",
        },
    },
    SheetName.BASE_CO2_EMISSION_FACTOR.value: {
        "row_attr":"CO2_BASE_EMISSION_FACTOR_UNIT",
        "unit_col": "CO2_BASE_EMISSION_FACTOR_UNIT",
        "value_col": "CO2_BASE_EMISSION_FACTOR",
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            # "エネルギー分類": "energy_name_for_coefficient_matching",
            "エネルギー分類": "energy_name_jp",
            "供給会社": "supplier_name",
            "区分": "day_category",
            "単位": "CO2_BASE_EMISSION_FACTOR_UNIT",
        },
    },
    SheetName.ADJUSTED_CO2_EMISSION_FACTOR.value: {
        "row_attr":"CO2_ADJUSTED_EMISSION_FACTOR_UNIT",
        "unit_col": "CO2_ADJUSTED_EMISSION_FACTOR_UNIT",
        "value_col": "CO2_ADJUSTED_EMISSION_FACTOR",
        "column_mapping": {
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            # "エネルギー分類": "energy_name_for_coefficient_matching",
            "エネルギー分類": "energy_name_jp",
            "供給会社": "supplier_name",
            "区分": "day_category",
            "単位": "CO2_ADJUSTED_EMISSION_FACTOR_UNIT",
            # CO2調整後排出係数データソース	CO2_ADJUSTED_EMISSION_FACTOR_SOURCE
        },
    },

    SheetName.LOCATION_INFO.value: {
        "column_mapping": {
            "会社名": "company_name",
            "法人番号": "corp_number",
            "拠点識別番号※GHG排出量算定システムに登録の番号": "location_identifier_code",
            "拠点識別名※GHG排出量算定システムに登録の名称": "location_identifier_name",
            "住所": "building_address_city",
            "供給地点特定番号(22桁)": "supply_point_number",
            "店所番号(3桁)": "ep_office_code",
            "お客さま番号(13桁）": "ep_customer_number",
            "延床面積": "gross_floor_area",
            "大分類": "building_industry_class_major_name",
            "中分類": "building_industry_class_middle_name",
            "小分類": "building_industry_class_minor_name",
            "細分類": "building_industry_class_detail_name",
            "原単位分母（単位）": "benchmark_denom",
            "原単位分母（数値）": "benchmark_val",
            "省エネ法ベンチマーク制度対象業種": "building_energy_benchmark_target_industry",
            "省エネ法ベンチマーク指標": "building_energy_benchmark_indicator",
            "省エネ率": "kpi_target_energy_saving_rate",
            "電化率": "kpi_target_electrification_rate",
            "創エネ": "kpi_target_energy_creation",
            "再エネ・ネットワーク率": "kpi_target_renewable_network_rate"
        },
    },

    SheetName.CREDITS_INFO.value: {
        "column_mapping": {
            "会社名": "company_name",
            "法人番号": "corp_number",
            "拠点識別番号※GHG排出量算定システムに登録の番号": "location_identifier_code",
            "拠点名※GHG排出量算定システムに登録の名称": "location_identifier_name",
            "証書・クレジット名※「その他」の場合は備考欄にデータ種別と単位をご記載ください": "certificate_credit_name"
        },
    },

    SheetName.UNIT_DENOMINATOR_INFO.value: {
        "column_mapping": {
            "会社名": "company_name",
            "法人番号": "corp_number",
            "拠点識別番号※GHG排出量算定システムに登録の番号": "location_identifier_code",
            "拠点識別名※GHG排出量算定システムに登録の名称": "location_identifier_name",
            "原単位分母": "unit_denominator_unit",
            "その他（自由記入欄）※単位もご記入ください": "other_unit_denominator_unit"
        },
    },
}


# 可視化エネルギー情報Inputシート名
# SHEET_NAME_LIST = [
#     { "name": name, "skiprows": 2 if name == "情報" else 3 }
#     for name in [
#         "情報", "物件情報", "種別ごとエネルギー使用量", "種別ごと熱量換算値",
#         "種別ごとCO2基礎排出量", "種別ごとCO2調整後排出量",
#         "熱量換算係数", "CO2基礎排出係数", "CO2調整後排出係数"
#     ]
# ]
    
SHEET_KEYWORDS = {
    SheetName.INFO.value: SimpleNamespace(
        company_name = "企業名",
        base_year_month = "基準年月",
        output_year_num = "出力年数"
    )
}

# ヒアリングシート企業情報項目名
HEARING_ITEM_NAMES = {
    SheetName.COMPANY_INFO.value: SimpleNamespace(
        company_name = "企業名",
        corp_num = "法人番号",
        ghg_system_company_name = "GHG排出量算定システム会社名",
        company_industry_class_major_name = "日本産業分類（大分類）",
        company_industry_class_middle_name = "日本産業分類（中分類）",
        company_industry_class_minor_name = "日本産業分類（小分類）",
        company_industry_class_detail_name = "日本産業分類（細分類）",
        company_industry_class_detail_code = "日本産業分類（細分類番号）",
        company_energy_benchmark_target_industry = "【対象の場合のみ】省エネ法ベンチマーク対象業種",
        company_energy_benchmark_indicator = "【対象の場合のみ】省エネ法ベンチマーク指標",
        company_energy_benchmark_year = "省エネ法ベンチマーク指標年度",
    )
}

# 解析対象シート
SHEET_NAME_LIST = [
    { "name": name, 
    "skiprows": 2 if name == SheetName.INFO.value else 3,
    "validation": {
        "sheet_required": True,
        "header_check": True,
        "data_check": True 
    } 
    }
    for name in [
        "情報", "物件情報", "種別ごとエネルギー使用量", "種別ごと熱量換算値",
        "種別ごとCO2基礎排出量", "種別ごとCO2調整後排出量", "原単位分母", 
        "熱量換算係数", "CO2基礎排出係数", "CO2調整後排出係数"
    ]
]

# ヒアリングシート解析対象シート
HEARING_SHEET_NAME_LIST = [
    { "name": name, 
    "skiprows": 1 if name == "企業情報" else 2,
    "validation": {
        "sheet_required": True,
        "header_check": True,
        "data_check": True 
    } 
    }
    for name in [
        "企業情報", "拠点情報", "証書・クレジット","（任意）原単位分母"
    ]
]

BUILDING_SHEET_NAME_LIST = [
    { "name": name, 
    "skiprows": 1 if name == "同意書" else 2,
    "validation": {
        "sheet_required": True,
        "header_check": True,
        "data_check": True 
    } 
    }
    for name in [
        "同意書", "別紙"
    ]
]

required_sheet_names: tuple[str, ...] = [
    "情報", "物件情報", 
    "種別ごとエネルギー使用量", "種別ごと熱量換算値", 
    "種別ごとCO2調整後排出量", 
    "原単位分母", 
    "熱量換算係数", "CO2基礎排出係数", "CO2調整後排出係数"];

energy_required_sheet_names: tuple[str, ...] = [
    "情報", "物件情報", "種別ごとエネルギー使用量", "種別ごと熱量換算値", 
    "種別ごとCO2基礎排出量", "種別ごとCO2調整後排出量", "原単位分母", "熱量換算係数", "CO2基礎排出係数", "CO2調整後排出係数"];

hearing_required_sheet_names: tuple[str, ...] = [
    "企業情報", "拠点情報", "証書・クレジット", "（任意）原単位分母"];

building_required_sheet_names: tuple[str, ...] = ["同意書", "別紙"];

building_sheet_mapping = {
    BuildingSheetName.ATTACHMENT.value: {
        "column_mapping": {
            "法人番号": "CORPORATE_NUMBER",
            "物件番号": "LOCATION_IDENTIFIER_CODE",
            "物件名": "LOCATION_IDENTIFIER_NAME",
            "所在地（都道府県）": "BUILDING_ADDRESS_PREFECTURE",
            "所在地（市区町村番地）": "BUILDING_ADDRESS_CITY",
            "供給地点特定番号(22桁）※任意": "SUPPLY_POINT_NUMBER",
            "供給地点特定番号（22桁）　　※任意": "SUPPLY_POINT_NUMBER",
            "店所番号（3桁）": "EP_OFFICE_CODE",
            "お客さま番号(13桁）　　※任意": "EP_CUSTOMER_NUMBER"
        }

    },
}

# 共通エネルギー情報セットカラムリスト
VIS_COMMON_COLUMNS = [
    # 企業情報
    # "ghg_system_company_name",
    "company_industry_class_major_code",
    "company_industry_class_major_name",
    "company_industry_class_middle_code",
    "company_industry_class_middle_name",
    "company_industry_class_minor_code",
    "company_industry_class_minor_name",
    "company_industry_class_detail_code",
    "company_industry_class_detail_name",
    "company_energy_benchmark_target_industry",
    "company_energy_benchmark_indicator",
    "company_energy_benchmark_year",

    # お客さま情報
    "input_supplier_name", # 企業情報の企業名から取得
    "supply_point_number",
    "ep_office_code",
    "ep_customer_number",
    "gross_floor_area",
    "location_identifier_code",
    "location_identifier_name",

    # 産業分類
    "site_industry_class_major_code",
    "site_industry_class_major_name",
    "site_industry_class_middle_code",
    "site_industry_class_middle_name",
    "site_industry_class_minor_code",
    "site_industry_class_minor_name",
    "site_industry_class_detail_code",
    "site_industry_class_detail_name",

    # 省エネ法ベンチマーク指標
    "site_energy_benchmark_target_industry",
    "site_energy_benchmark_indicator",
    "site_energy_benchmark_year",

    # 原単位分母
    "unit_denominator_year",

    # KPI情報
    "kpi_target_energy_saving_rate",
    "kpi_target_electrification_rate",
    "kpi_target_energy_creation",
    "kpi_target_renewable_network_rate",

    # 拠点情報
    "site_industry_class_major_code",
    "site_industry_class_middle_code",
    "site_industry_class_minor_code",
    "site_industry_class_detail_code",
    "site_industry_class_major_name",
    "site_industry_class_middle_name",
    "site_industry_class_minor_name",
    "site_industry_class_detail_name",
    "site_energy_benchmark_target_industry",
    "site_energy_benchmark_indicator",
    "site_energy_benchmark_year"
]

# ---------------------------
# 1. 電気以外のマッピング辞書
# ---------------------------
energy_mapping = {
    "LPガス": ("LPガス", "液化石油ガス（LPG）"),
    "液化石油ガス（ＬＰＧ）": ("液化石油ガス（LPG）", "液化石油ガス（LPG）"),
    "液化天然ガス": ("液化石油ガス", "液化天然ガス（LNG）"),
    "一次エネルギー": ("一次エネルギー", "冷水"),
    "蒸気": ("蒸気", "産業用以外の蒸気"),
    "冷温水蒸気": ("冷温水蒸気", "冷水"),
    "揮発油（ガソリン）": ("揮発油（ガソリン）", "揮発油"),
    "重油（A重油）": ("A重油", "Ａ重油"),
    "重油（B重油）": ("B重油", "Ｂ・Ｃ重油"),
    "重油（C重油）": ("C重油", "Ｂ・Ｃ重油"),
    "コンデンセート（NGL）": ("コンデンセート（NGL）", "コンデンセート"),
    "石油コークス": ("石油コークス", "石油コークス"),
    "石油コークス又はFCCコーク（流動接触分解で使⽤された触媒に析出する炭素）": ("石油コークス", "石油コークス"),
    "原油のうちコンデンセート（NGL)": ("原油のうちコンデンセート（NGL)", "原油のうちコンデンセート（NGL)"),
    "原油（コンデンセート（NGL）を除く。）": ("原油（コンデンセート（NGL）を除く。）", "原油（コンデンセート除く）"),
    "天然ガス（液化天然ガス（LNG）を除く。）": ("天然ガス（液化天然ガス（LNG）を除く。）", "その他可燃性天然ガス"),
}

# ---------------------------
# 2. 電気の supplier_name マッピング辞書
# ---------------------------
electric_supplier_map = {
    "上記以外の自己託送（非化石電力・重み付けなし）": ("電気", "自己託送（その他非化石電気）"),
    "上記以外の自己託送（化石電力・重み付けなし）": ("電気", "自己託送（化石電気）"),
    "自己託送（非燃料由来の非化石電気・再エネ）": ("電気", "他事業所からの供給（自営線）（非燃料由来の非化石電気）"),
    "自家発電（風力）": ("電気", "風力発電"),
    "自家発電（地熱）": ("電気", "地熱発電"),
    "自家発電（太陽光）": ("電気", "太陽光発電"),
    "自家発電（水力）": ("電気", "水力発電"),
    "自家発電（その他＜非燃料由来の非化石＞）": ("電気", "その他（非燃料由来の非化石電気）"),
    "自家発電（その他＜燃料＞・非化石電力）": ("電気", "その他（燃料）非化石"),
    "自家発電（その他＜燃料＞・化石電力）": ("電気", "その他（燃料）化石"),
    "自家発電（その他＜熱＞・非化石電力）": ("電気", "その他（熱）非化石"),
    "自家発電（その他＜熱＞・化石電力）": ("電気", "その他（熱）化石"),
    "オフサイトPPA（再エネ電力・重み付けなし）": ("電気", "オフサイトPPA（重み付けなし）"),
    "オフサイトPPA（再エネ電力・重み付けあり）": ("電気", "オフサイトPPA（重み付けあり）"),
}

heat_credit = (
    "9900011006",
    "9900011008",
    # "9900011009",
    # "9900011010",
    # "9900011011",
    # "9900011012",
)

no_elec_credit = (
    "9900011009",
    "9900011010",
    "9900011011",
    "9900011012"
)

benchmark_industry_dict = {
    "通常コンビニエンスストア業": "7A",
    "小型コンビニエンスストア業": "7B",
    "通常コンビニエンスストア": "7A",
    "小型コンビニエンスストア": "7B",
    "ホテル業": "8",
    "百貨店業": "9",
    "食料品スーパー業": "10",
    "食品スーパー業": "10",
    "大学": "13",
    "パチンコホール業": "14",
    "データセンター業": "16",
}

pref_check_list = (
    "01:北海道",
    "02:青森県",
    "03:岩手県",
    "04:宮城県",
    "05:秋田県",
    "06:山形県",
    "07:福島県",
    "08:茨城県",
    "09:栃木県",
    "10:群馬県",
    "11:埼玉県",
    "12:千葉県",
    "13:東京都",
    "14:神奈川県",
    "15:新潟県",
    "16:富山県",
    "17:石川県",
    "18:福井県",
    "19:山梨県",
    "20:長野県",
    "21:岐阜県",
    "22:静岡県",
    "23:愛知県",
    "24:三重県",
    "25:滋賀県",
    "26:京都府",
    "27:大阪府",
    "28:兵庫県",
    "29:奈良県",
    "30:和歌山県",
    "31:鳥取県",
    "32:島根県",
    "33:岡山県",
    "34:広島県",
    "35:山口県",
    "36:徳島県",
    "37:香川県",
    "38:愛媛県",
    "39:高知県",
    "40:福岡県",
    "41:佐賀県",
    "42:長崎県",
    "43:熊本県",
    "44:大分県",
    "45:宮崎県",
    "46:鹿児島県",
    "47:沖縄県"
)