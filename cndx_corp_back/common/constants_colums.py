from enum import Enum

######### エネルギー種類日本名用マップ
energy_name_jp_map = {
    'HEAVY_OIL_A':'Ａ重油',
    'HEAVY_OIL_BC':'Ｂ・Ｃ重油',
    'LIGHT_OIL':'軽油',
    'KEROSENE':'灯油',
    'GASOLINE':'揮発油',
    'CITY_GAS':'都市ガス',
    'LPG':'液化石油ガス（LPG）',
    'INDUSTRIAL_STEAM':'産業用蒸気',
    'INDUSTRIAL_EXCEPT_STEAM':'産業用以外の蒸気',
    'WARM_WATER':'温水',
    'COLD_WATER':'冷水',
    'CRUDE_OIL_CONDENSATE_EXCEPT':'原油（コンデンセート除く）',
    'CRUDE_OIL_CONDENSATE':'原油のうちコンデンセート(NGL)',
    'NAPHTHA':'ナフサ',
    'PETROLEUM_ASPHALT':'石油アスファルト',
    'PETROLEUM_COKE':'石油コークス',
    'PETROLEUM_COKE':'石油コークス又はFCCコーク（流動接触分解で使⽤された触媒に析出する炭素）',
    'LNG':'LNG',
    'PETROLEUM_HYDROCARBON_GAS':'石油系炭化水素ガス',
    'OTHER_FLAMMABLE_NATURAL_GAS':'その他可燃性天然ガス',
    'COAL_COKE':'石炭コークス',
    'COAL_TAR':'コールタール',
    'COKE_OVEN_GAS':'コークス炉ガス',
    'BLAST_FURNACE_GAS':'高炉ガス',
    'CONVERTER_GAS':'転炉ガス',
    'JET_FUEL':'ジェット燃料油',
    'ELECTRIC_POWER':'電気',
    'SUPPLY_INDUSTRIAL_WATER':'水道および工業用水',
    'IMPORTED_COKING_COAL':'輸入原料炭',
    'COKING_COAL':'コークス用原料炭',
    'PCI_COAL':'吹込用原料炭',
    'IMPORT_ORDINARY_CHARCOAL':'輸入一般炭',
    'DOMESTIC_STANDARD_COAL':'国産一般炭',
    'IMPORT_SMOKELESS_COAL':'輸入無煙炭',
    'FCC_COKE':'FCCコーク',
    'CRUDE_OIL_CONDENSATE_NGL':'コンデンセート（NGL）',
    # 'CRUDE_OIL_CONDENSATE_EXCEPT':'原油',
    'LUBRICATING_OIL':'潤滑油',
    'LPG':'液化石油ガス（LPG）',
    'LNG':'液化天然ガス（LNG）',
    'POWER_GENERATION_BLAST_FURNACE_GAS':'発電用高炉ガス',
    'SELF_CONSUMED_RENEWABLE_ENERGY':'再エネ発電（自家消費）',
    'CREDIT_ELECTRICITY_CERTIFICATE':'電力証書・クレジット',
    'CREDIT_HEAT_CERTIFICATE':'熱証書・クレジット',
    'CREDIT_OTHERS_CERTIFICATE':'その他の証書・クレジット'

}
######### Excelの読み込みの際に値を入り替える用
convert_mapping = {
    # '金融機関コード（4桁・半角数字）':'BANK_CODE',
    # '支店コード（3桁・半角数字）':'BRANCH_CODE',
    # '対象年度（4桁・半角数字）':'FISCAL_YEAR',
    # '登録回数':'REGISTRATION_SEQ',
    # '金融機関名':'BANK_NAME',
    # '支店・部署名':'DEPARTMENT_BRANCH_NAME',
    # '氏名':'CONTACT_PERSON_NAME_LOCAL_BANK',
    # '電話番号（半角数字・ハイフン不要）':'PHONE_NUMBER_LOCAL_BANK',
    # 'メールアドレス（「@」必須）':'EMAIL_ADDRESS_LOCAL_BANK',
    # 'ご担当者さま氏名':'CONTACT_PERSON_NAME_CORPORATE',
    # 'ご担当者さま電話番号（半角数字・ハイフン不要）':'PHONE_NUMBER_CORPORATE',
    # 'データ利用承諾日（8桁・半角数字　例：20240401）':'UTILIZATION_APPROVAL_DATE_CORPORATE',
    'お客さま名':'CORPORATE_NAME',
    '法人番号（13桁・半角数字）':'CORPORATE_NUMBER',
    '本社所在地（都道府県・プルダウンから選択）':'ADDRESS_PREFECTURE',
    '本社所在地（市区町村以降）':'ADDRESS_CITY',
    '拠点数（半角数字）':'BUSINESS_OFFICE_COUNT',
    '産業分類（大分類・プルダウンから選択）':'INDUSTRY_CLASS_MAJOR_NAME',
    '産業分類（中分類・プルダウンから選択）':'INDUSTRY_CLASS_MIDDLE_NAME',
    '産業分類（小分類・プルダウンから選択）':'INDUSTRY_CLASS_MINOR_NAME',
    '産業分類（細分類・プルダウンから選択）':'INDUSTRY_CLASS_DETAIL_NAME',
    '産業分類（大分類・自動入力）':'INDUSTRY_CLASS_MAJOR_NAME',
    '産業分類（中分類・自動入力）':'INDUSTRY_CLASS_MIDDLE_NAME',
    '産業分類符号（細分類・自動入力）':'INDUSTRY_DETAIL_CLASSIFICATION_MARK',
    '拠点・エネルギー情報登録期間　開始年月（6桁・半角数字　例：202404）':'REPORT_PERIOD_START_YEAR_MONTH',
    '拠点・エネルギー情報登録期間　終了年月（自動入力）':'REPORT_PERIOD_END_YEAR_MONTH',
    # 'エリアID':'AREA_ID',
    '拠点名':'BUILDING_NAME',
    '建物ID':'BUILDING_ID',
    # '建物名':'BUILDING_NAME',
    '拠点所在地（都道府県・プルダウンから選択）':'BUILDING_ADDRESS_PREFECTURE',
    '拠点所在地（市区町村以降）':'BUILDING_ADDRESS_CITY',
    '延床面積（半角数字）':'GROSS_FLOOR_AREA',
    '契約先電気事業者（プルダウンから選択）':'ELECTRIC_POWER_CORPORATE_NAME',
    '契約先電気事業者登録番号（自動入力）':'ELECTRIC_COMPANY_REG_NO',
    '契約先電気料金メニュー':'MENU_NM',
    '事業所コード（3桁・半角数字）':'EP_CUSTOMER_NUMBER',
    'お客さま番号（13桁・半角数字）':'CUSTOMER_NUMBER_EP',
    '供給地点特定番号（22桁・半角数字）':'SUPPLY_POINT_NUMBER',
    '契約先都市ガス供給事業者':'CITY_GAS_CORPORATE_NAME',
    '契約先都市ガス供給事業者登録番号（自動入力）':'CITY_GAS_REG_NO',
    '契約先熱供給事業者':'HEATING_SUPPLIER',
    '契約先熱供給事業者登録番号（自動入力）':'HEAT_SUPPLY_REG_NO',
    # '建物竣工年（西暦4桁・半角数字）':'BUILDING_COMPLETION_YEAR',
    # '建物耐震基準（プルダウンから選択）':'EARTHQUAKE_RESISTANCE_STANDARDS',
    # '契約先電気事業者登録番号（自動入力）':'ELECTRIC_COMPANY_REG_NO',
    # '契約電力（半角数字）':'CONTRACTED_POWER',
    # '電力量料金（夏季）（半角数字）':'ELECTRICITY_USAGE_FEE_SUMMER',
    # '電力量料金（その他季）（半角数字）':'ELECTRICITY_USAGE_FEE_OTHER_SEASONS',
    # '燃料費調整額（半角数字）':'FUEL_COST_ADJUSTMENT',
    # '再エネ賦課金（半角数字）':'RENEWABLE_ENERGY_SURCHARGE',
    # '従業員数（半角数字）':'EMPLOYEES',
    # '年間稼働日数（半角数字）':'ANNUAL_WORKING_DAYS',
    # '1日の稼働時間（半角数字）':'WORKING_HOURS_ONE_DAY',
    # '給湯用（プルダウンから選択）':'GAS_WATER_HEATING',
    # '生産用（プルダウンから選択）':'GAS_PRODUCTION_USE',
    # '空調用（プルダウンから選択）':'GAS_AIR_CONDITIONING_USE',
    # '発電設備（プルダウンから選択）':'POWER_GENERATION_FACILITIES',
    # '再エネ電力（プルダウンから選択）':'RENEWABLE_ENERGY_POWER',
    # '環境証書（プルダウンから選択）':'ENVIRONMENTAL_CERTIFICATE',
    # '屋根面積（半角数字）':'ROOF_AREA',
    # '駐車場面積（半角数字）':'PARKING_AREA',
    # '空調方式（プルダウンから選択）':'AIR_CONDITIONING_SYSTEM',
    # '空調入れ替え有無（プルダウンから選択）':'NEED_AIR_CONDITIONING_REPLACEMENT',
    # '空調入れ替え年（西暦4桁・半角数字）':'YEAR_AIR_CONDITIONING_REPLACEMENT',
    # '蛍光灯割合':'FLUORESCENT_LIGHTS_PERCENTAGE',
    # 'LED割合':'LED_LIGHTS_PERCENTAGE',
    '輸入原料炭': 'IMPORTED_COKING_COAL', 
    'コークス用原料炭': 'COKING_COAL', 
    '吹込用原料炭': 'PCI_COAL', 
    '輸入一般炭': 'IMPORT_ORDINARY_CHARCOAL', 
    '国産一般炭': 'DOMESTIC_STANDARD_COAL', 
    '輸入無煙炭': 'IMPORT_SMOKELESS_COAL', 
    '石炭コークス': 'COAL_COKE', 
    '石油コークス': 'PETROLEUM_COKE', 
    'FCCコーク': 'FCC_COKE', 
    'コールタール': 'COAL_TAR',
    '石油アスファルト': 'PETROLEUM_ASPHALT',
    'コンデンセート（NGL）': 'CRUDE_OIL_CONDENSATE_NGL', 
    '原油（コンデンセート除く）': 'CRUDE_OIL_CONDENSATE_EXCEPT', 
    '揮発油': 'GASOLINE', 
    'ナフサ': 'NAPHTHA', 
    'ジェット燃料油': 'JET_FUEL', 
    '灯油': 'KEROSENE', 
    '軽油': 'LIGHT_OIL', 
    'Ａ重油': 'HEAVY_OIL_A', 
    'Ｂ・Ｃ重油': 'HEAVY_OIL_BC', 
    '潤滑油': 'LUBRICATING_OIL', 
    '液化石油ガス（LPG）': 'LPG',
    '石油系炭化水素ガス': 'PETROLEUM_HYDROCARBON_GAS', 
    '液化天然ガス（LNG）': 'LNG', 
    'その他可燃性天然ガス': 'OTHER_FLAMMABLE_NATURAL_GAS',
    'コークス炉ガス': 'COKE_OVEN_GAS', 
    '高炉ガス': 'BLAST_FURNACE_GAS', 
    '発電用高炉ガス': 'POWER_GENERATION_BLAST_FURNACE_GAS',
    '転炉ガス': 'CONVERTER_GAS', 
    '都市ガス': 'CITY_GAS', 
    '産業用蒸気': 'INDUSTRIAL_STEAM', 
    '産業用以外の蒸気': 'INDUSTRIAL_EXCEPT_STEAM',
    '温水': 'WARM_WATER', 
    '冷水': 'COLD_WATER',
    '電気': 'ELECTRIC_POWER',
    '再エネ発電（自家消費）':'SELF_CONSUMED_RENEWABLE_ENERGY',
    '電力証書・クレジット':'CREDIT_ELECTRICITY_CERTIFICATE',
    '熱証書・クレジット':'CREDIT_HEAT_CERTIFICATE',
    'その他の証書・クレジット':'CREDIT_OTHERS_CERTIFICATE'
    # '原油のうちコンデンセート(NGL)': 'CRUDE_OIL_CONDENSATE', 
    # 'ガソリン': 'GASOLINE',
    # 'LPG': 'LPG', 
    # '液化天然ガス（LNG）': 'LNG', 
    # '原料炭': 'RAW_CHARCOAL', 
    # '一般炭': 'ORDINARY_CHARCOAL', 
    # '無煙炭': 'SMOKELESS_COAL', 
    # '水道および工業用水': 'SUPPLY_INDUSTRIAL_WATER', 
    # '公共下水道': 'PUBLIC_SEWAGE_SYSTEM',
    # '原油': 'CRUDE_OIL_CONDENSATE_EXCEPT', 
    # 'その他可燃性天然ガス': 'NATURAL_GAS', 
    # '✓': '1',
    # '-': '0',
    # '導入済み':'2',
    # '導入なし(意向なし)':'0',
    # '導入なし(意向あり)':'1',
    # '使用済み':'2',
    # '使用なし(意向なし)':'0',
    # '使用なし(意向あり)':'1',
    # 'セントラル空調':'0',
    # '個別':'1',
    # '有':'1',
    # '無':'0'
}

enery_code_mapping = {
    '輸入原料炭': '0100020000', 
    'コークス用原料炭': '0100310000', 
    '吹込用原料炭': '0100320000', 
    '輸入一般炭': '0100010000', 
    '国産一般炭': '0100330000', 
    '輸入無煙炭': '0100030000', 
    '石炭コークス': '0100070000', 
    '石油コークス': '0100080000', 
    'FCCコーク': '0100350000', 
    'コールタール': '0100170000',
    '石油アスファルト': '0100160000',
    'コンデンセート（NGL）': '6800030000', 
    '原油（コンデンセート除く）': '0100150000', 
    '揮発油': '0100090000', 
    'ナフサ': '0100180000', 
    'ジェット燃料油': '0100300000', 
    '灯油': '0100100000', 
    '軽油': '0100110000', 
    'Ａ重油': '0100120000', 
    'Ｂ・Ｃ重油': '0100130000', 
    '潤滑油': '0100360000', 
    '液化石油ガス（LPG）': '0100190000', 
    '石油系炭化水素ガス': '0100200000', 
    '液化天然ガス（LNG）': '0100210000', 
    'その他可燃性天然ガス': '0100220000',
    'コークス炉ガス': '0100240000', 
    '高炉ガス': '0100250000', 
    '発電用高炉ガス': '0100340000',
    '転炉ガス': '0100260000', 
    '都市ガス': '0100230000', 
    '産業用蒸気': '0300010000', 
    '産業用以外の蒸気': '0300020000',
    '温水': '0300030000', 
    '冷水': '0300040000',
    '電気': '0200010011',
    '再エネ発電（自家消費）':'9900010001',
    '電力証書・クレジット':'9900011002',
    '熱証書・クレジット':'9900011006',
    'その他の証書・クレジット':'9900011009'
    # '再エネ発電（自家消費）':'RENEWABLE_ENERGY_GENERATION',
    # '電力証書・クレジット':'ELECTRICITY_CERTIFICATE',
    # '熱証書・クレジット':'THERMAL_ENERGY_CERTIFICATE',
    # 'その他の証書・クレジット':'OTHER_CERTIFICATES'
        # '原油のうちコンデンセート(NGL)': '0100140000', 
    # '原料炭': '0100020000', 
    # '一般炭': '0100010000', 
    # '無煙炭': '0100030000', 
    # '原油': '0100150000', 
}

# 入力情報
caitbl_columns = (
    "CORPORATE_NUMBER",
    "AGREEMENT_CATEGORY",
    "ORG_ID",
    "FISCAL_YEAR",
    "REGISTRATION_SEQ",
    "COMPANY_NAME",
    "ENTRY_DRAFT_FLAG",
    "GHG_SYSTEM_COMPANY_NAME",
    "INDUSTRY_CLASS_MAJOR_CODE",
    "INDUSTRY_CLASS_MIDDLE_CODE",
    "INDUSTRY_CLASS_MINOR_CODE",
    "INDUSTRY_CLASS_DETAIL_CODE",
    "INDUSTRY_CLASS_MAJOR_NAME",
    "INDUSTRY_CLASS_MIDDLE_NAME",
    "INDUSTRY_CLASS_MINOR_NAME",
    "INDUSTRY_CLASS_DETAIL_NAME",
    "BUSINESS_OFFICE_COUNT",
    "ENERGY_BENCHMARK_TARGET_INDUSTRY",
    "ENERGY_BENCHMARK_INDICATOR",
    "ENERGY_BENCHMARK_YEAR",
    "ADDRESS_PREFECTURE",
    "ADDRESS_CITY",
    "REPORT_PERIOD_START_YEAR_MONTH",
    "REPORT_PERIOD_END_YEAR_MONTH",
    "COMPETITOR_INDUSTRY_CO2_AVG",
    "ENERGY_SAVING_DENOMINATOR",
    "KPI_TARGET_ENERGY_SAVING_RATE",
    "KPI_TARGET_ELECTRIFICATION_RATE",
    "KPI_TARGET_ENERGY_CREATION",
    "KPI_TARGET_RENEWABLE_NETWORK_RATE",
    "DELETE_FLG",
    "CREATED_BY",
    "CREATED_AT",
    "UPDATED_BY",
    "UPDATED_AT"
)

# テーブル t_building_info
bditbl_columns = (
    "CORPORATE_NUMBER",
    "AGREEMENT_CATEGORY",
    "ORG_ID",
    "BUILDING_ID",
    "NUMBER_REGISTRATIONS",
    "FISCAL_YEAR",
    "ENTRY_DRAFT_FLAG",
    "LOCATION_IDENTIFIER_NAME",
    "ZIP_CODE",
    "MUNICIPALITY_CODE",
    "ADDRESS_PREFECTURE",
    "ADDRESS_CITY",
    "INDUSTRY_CLASS_MAJOR_CODE",
    "INDUSTRY_CLASS_MIDDLE_CODE",
    "INDUSTRY_CLASS_MINOR_CODE",
    "INDUSTRY_CLASS_DETAIL_CODE",
    "INDUSTRY_CLASS_MAJOR_NAME",
    "INDUSTRY_CLASS_MIDDLE_NAME",
    "INDUSTRY_CLASS_MINOR_NAME",
    "INDUSTRY_CLASS_DETAIL_NAME",
    "ENERGY_BENCHMARK_TARGET_INDUSTRY",
    "ENERGY_BENCHMARK_INDICATOR",
    "ENERGY_BENCHMARK_YEAR",
    "GROSS_FLOOR_AREA",
    "ELECTRICITY_SUPPLIER_NO",
    "ELECTRICITY_SUPPLIER_NAME",
    "ELECTRICITY_CONTRACT_MENU",
    "EP_OFFICE_CODE",
    "EP_CUSTOMER_NUMBER",
    "SUPPLY_POINT_NUMBER",
    "CITY_GAS_SUPPLIER_NO",
    "CITY_GAS_SUPPLIER_NAME",
    "HEAT_SUPPLIER_NO",
    "HEAT_SUPPLIER_NAME",
    "HEAT_CONTRACT_MENU"
)


# 入力情報
caitbl_hive_columns = (
    "BRANCH_CODE",
    "REGISTRATION_SEQ",
    "BANK_NAME",
    "DEPARTMENT_BRANCH_NAME",
    "CONTACT_PERSON_NAME_LOCAL_BANK",
    "CONTACT_PERSON_NAME_CORPORATE",
    "PHONE_NUMBER_CORPORATE",
    "UTILIZATION_APPROVAL_DATE_CORPORATE",
    "CORPORATE_NAME",
    "OFFICE_ADDRESS",
    "NUMBER_OFFICES",
    "INDUSTRY_BROAD_CATEGORIZATION",
    "INDUSTRY_INTERMEDIATE_CLASSIFICATION",
    "REPORT_PERIOD_START_YEAR_MONTH",
    "REPORT_PERIOD_END_YEAR_MONTH",
    "AREA_ID",
    "AREA_INFORMATION",
    "BUILDING_NAME",
    "INDUSTRY_CATEGORY_SMALL",
    "SUPPLY_POINT_NUMBER",
    "EP_CUSTOMER_NUMBER",
    "CUSTOMER_NUMBER_EP",
    "ADDRESS",
    "GROSS_FLOOR_AREA",
    "ELECTRIC_COMPANY_REG_NO",
    "ELECTRIC_POWER_CORPORATE_NAME",
    "CONTRACTED_POWER",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG",
)

# レポート格納情報
rsitbl_columns = (
    "CORPORATE_NUMBER",
    "AGREEMENT_CATEGORY",
    "ORG_ID",
    "BUILDING_ID",
    "FISCAL_YEAR",
    "REPORT_CLASSIFY",
    "REGISTRATION_SEQ",
    "TARGET_MONTH",
    "ENTRY_DRAFT_FLAG",
    "COMPANY_NAME",
    "FILE_ID",
    "REPORT_SAVE_PATH",
    "REPORT_STATUS",
    "REPORT_SELECTION_PERIOD_FROM",
    "FORMAT_TYPE",
    "SITE_SELECTION_TYPE",
    "REPORT_CREATED_AT",
    "REPORT_CREATED_BY",
    "DELETE_FLG",
    "CREATED_BY",
    "CREATED_AT",
    "UPDATED_BY",
    "UPDATED_AT"
)

# 簡易診断設定シート入力項目
roadmap_setting = {
    "基準年":"BASE_YEAR",
    "熱源照明更新周期":"HEAT_SOURCE_LIGHTING_RENEWAL_CYCLE",
    "その他対策周期":"OTHER_MEASURES_CYCLE",
    "対策考慮区分":"CONSIDERATION_OF_MEASURES",
    "省エネ努力目標":"ENERGY_SAVING_TARGET",
    "電力CO2排出係数パターン":"ELECTRICITY_CO2_EMISSIONS_COEFFICIENT_PATTERN",
    "証書購入基準年～2030年":"BASE_YEAR_FOR_CERTIFICATE_PURCHASE_TO_2030",
    "証書購入2030～2050年":"CERTIFICATE_PURCHASE_FROM_2030_TO_2050",
    "太陽光導入年":"SOLAR_INTRODUCTION_YEAR",
    "竣工年記載無の代替":"ALTERNATIVE_FOR_NON-CONSTRUCTION_YEAR_INDICATION",
    "中央個別判断":"CENTRAL_INDIVIDUAL_JUDGMENT",
    "太陽光発電設置可能比率":"SOLAR_POWER_INSTALLATION_POSSIBLE_RATE",
    "新耐震区分け年数":"NEW_SEISMIC_ZONING_YEARS",
    "太陽光発電":"SOLAR_POWER_GENERATION",
    "太陽光発電発電量":"SOLAR_POWER_GENERATION_AMOUNT",
    "建物用途区分":"BUILDING_USAGE"
}
corporate_column = [
    'CORPORATE_NAME',
    'CORPORATE_NUMBER',
    'ADDRESS_PREFECTURE',
    'ADDRESS_CITY',
    'BUSINESS_OFFICE_COUNT',
    'INDUSTRY_MAJOR_CATEGORY',
    'INDUSTRY_MIDDLE_CATEGORY',
    'INDUSTRY_MINOR_CATEGORY',
    'INDUSTRY_DETAIL_CATEGORY',
    'INDUSTRY_MAJOR_CODE',
    'INDUSTRY_MIDDLE_CODE',
    'INDUSTRY_MINOR_CODE',
    'INDUSTRY_DETAIL_CODE',
    'INDUSTRY_DETAIL_CLASSIFICATION_MARK',
    'REPORT_PERIOD_START_YEAR_MONTH',
    'REPORT_PERIOD_END_YEAR_MONTH',
    'FISCAL_YEAR'
]

building_column = [
    'BUILDING_NAME',
    'BUILDING_ID',
    # '建物名':'BUILDING_NAME',
    'BUILDING_ADDRESS_PREFECTURE',
    'BUILDING_ADDRESS_CITY',
    'GROSS_FLOOR_AREA',
    'ELECTRIC_POWER_CORPORATE_NAME',
    'ELECTRIC_COMPANY_REG_NO',
    'ENERGY_BENCHMARK_TARGET_INDUSTRY',
    'MENU_NO',
    'MENU_NM',
    'EP_CUSTOMER_NUMBER',
    'CUSTOMER_NUMBER_EP',
    'SUPPLY_POINT_NUMBER',
    'CITY_GAS_CORPORATE_NAME',
    'CITY_GAS_REG_NO',
    'HEATING_SUPPLIER',
    'HEAT_SUPPLY_REG_NO',
    'INDUSTRY_CLASS_MAJOR_NAME',
    'INDUSTRY_CLASS_MIDDLE_NAME',
    'INDUSTRY_CLASS_MINOR_NAME',
    'INDUSTRY_CLASS_DETAIL_NAME',
    'INDUSTRY_CLASS_MAJOR_CODE',
    'INDUSTRY_CLASS_MIDDLE_CODE',
    'INDUSTRY_CLASS_MINOR_CODE',
    'INDUSTRY_CLASS_DETAIL_CODE',
    'INDUSTRY_DETAIL_CLASSIFICATION_MARK'
]
# エネルギー情報のコラム作成
energy_column = [
    'BUILDING_ID',
    'BUILDING_NAME',
    'ENERGY_CODE',
    'CATEGORY',
    'ENERGY_NAME',
    'ENERGY_NAME_JP',
    'YEAR',
    'MONTH',
    'FISCAL_YEAR',
    'ENERGY_QUANTITY',
    'UNIT_ORIGIN',
    # 追加
    'location_identifier_code',
    # 'energy_name_for_coefficient_matching',
    'supplier_name',
    'day_category',
    'year_month',
    "HEAT_CONVERTED_ENERGY_UNIT",
    "HEAT_CONVERTED_ENERGY_USAGE_MONTHLY",
    "CO2_BASE_EMISSIONS_UNIT",
    "CO2_BASE_EMISSIONS",
    "CO2_ADJUSTED_EMISSIONS_UNIT",
    "CO2_ADJUSTED_EMISSIONS",
    "HEAT_CONVERSION_COEFFICIENT_UNIT",
    "HEAT_CONVERSION_COEFFICIENT",
    "CO2_BASE_EMISSION_FACTOR_UNIT",
    "CO2_BASE_EMISSION_FACTOR",
    "CO2_ADJUSTED_EMISSION_FACTOR_UNIT",
    "CO2_ADJUSTED_EMISSION_FACTOR"
]

# 必須チェック用項目格納用配列
CORPORATE_REQUIRED_COLUMNS = [
    'CORPORATE_NUMBER',
    'BUSINESS_OFFICE_COUNT',
    'INDUSTRY_MAJOR_CATEGORIZATION',
    'INDUSTRY_MIDDLE_CLASSIFICATION',
    'INDUSTRY_MINOR_CATEGORIZATION',
    'INDUSTRY_DETAIL_CLASSIFICATION',
    'REPORT_PERIOD_START_YEAR_MONTH'
]

BUILDING_REQUIRED_COLUMNS = [
    'INDUSTRY_MINOR_CATEGORIZATION',
    'INDUSTRY_DETAIL_CLASSIFICATION',
    'GROSS_FLOOR_AREA',
    'SUPPLY_POINT_NUMBER'
]

NEITHER_REQUIRED_COLUMNS = [
    "CORPORATE_NUMBER",
    "EP_CUSTOMER_NUMBER",
    "CUSTOMER_NUMBER_EP"
]

# マスタテーブル
class MasterTable(Enum):
    """
    マスタテーブル名列挙
        業種マスタ
        排出係数マスタ
        電力換算係数マスタ
        建物群マスタ
        区分マスタ
        活動項目小分類マスタ
        日本標準産業分類マスタ
        電力会社の換算係数マスタ
    """        
    JICMST = "M_JP_ST_INDUSTRY_CLASSIFICATION"
    CCMST = "ACTIVITY_MINOR_CATEGORY_MST"
    ECMST = "M_ELECTRICITY_CONVERSION_FACTOR"
    AIMST = "M_AREA_INFO"
    KBNMST = "KUBUN_MST"
    ECDMST = "ENERGY_CONSUMPTION_DESTINATION_MST"
    ECEMST = "ELECTRICITY_CO2_EMISSION_MST"
    BECRMST = "BASE_ENERGY_CONSUMPTION_RATE_MST"
    CMST = "COUNTERMEASURE_MST"	
    CALMST = "M_CALCULATION_LOGIC"
    AMCMST = "ACTIVITY_MINOR_CATEGORY_MST"
    MJSIC = "M_JP_ST_INDUSTRY_CLASSIFICATION"
    MECF = "M_ELECTRICITY_CONVERSION_FACTOR"
    MUMST = "M_USER"


# 業務テーブル
class BusinessTable(Enum):
    """
    業務用テーブル名列挙
        エネルギー集計情報
        エネルギー集計月別情報
        年度別法人エネルギー集計情報
        月別法人エネルギー集計情報
        入力情報
        ファイルステータス
    """        
    EATBL = "T_ANNUAL_BUILDING_ENERGY_AGGREGATION"
    EAMTBL = "T_MONTHLY_BUILDING_ENERGY_AGGREGATION"
    ACEATBL = "T_ANNUAL_CORPORATE_ENERGY_AGGREGATION"
    MCEATBL = "T_MONTHLY_CORPORATE_ENERGY_AGGREGATION"
    CAITBL = "T_CN_APPLICATION_INFO"
    CBBITBL = "M_CUSTOMER_BANK_BASIC_INFO"
    BBITBL = "M_BANK_BRANCH_INFO"
    BSITBL = "M_BANK_STAFF_INFO"
    CBITBL = "M_CORPORATE_BASIC_INFO"
    RSITBL = "T_REPORT_STORAGE_INFO"
    BDITBL = "T_BUILDING_INFO"


class ExcelExtension(Enum):
    """Excelファイル拡張子列挙"""
    XLSX = ".xlsx"
    XLS = ".xls"
    XLSM = ".xlsm"
    CSV = ".csv"

class FileProcessStatus(Enum):
    """ファイル処理ステータス"""
    ERROR = "0"
    COMPELETED = "1"
    PENDING = "2"

class StringOfExcelFile(Enum):
    """Excelファイル内容特定文字列"""
    OFFICE = "拠点"
    INPUT_SHEET = "基本情報"
    ENERGY_INFO = "エネルギー使用量（半角数字）"
    INPUT_SPECS= "入力（TEPCO用）諸元"
    SETTING= "設定"

class NumberingStartValue(Enum):
    """採番用スタート番号用"""
    THREE_NUMBER = "001"
    SIX_NUMBER = "000001"

class SpecialChars(Enum):
    """特殊文字列用列挙"""
    COLON = ":"
    DOT = "."
    COMMA = ","
    UNDERSCORE = "_"
    SPACE = " "
    HATENA = "?"
    BLANK = ""
    HYPHEN = "-"
    LINUX_PATH_DELIMITER = "/"
    WINDOWS_PATH_DELIMITER = "\\"

class RunMode(Enum):
    """実行モード"""
    DEV = "dev"
    STG = "staging"
    PROD = "product"
    S2_PROD = "s2_product"

class EncodingMethod(Enum):
    """エンコーディング方法"""
    UTF8 = "utf-8"
    SJIS = "sjis"
    UTF8BOM = "utf-8-sig"

class TableauReport(Enum):
    """Tableauに表示するレポート"""
    KARTE = "企業カルテ"
    ABATEMENT = "アベイトメントカーブ"
    ROADMAP = "簡易診断ツール"
    COMMON = "企業カルテ_ロードマップ"

class InputFileIndentify(Enum):
    """Tableauに表示するレポート"""
    KARTE = "行員向け入力シート"
    ABATEMENT = "CNアベイトメントカーブ"
    ROADMAP = "CNロードマップ"

class HqlConditonOperators(Enum):
    """hql条件文操作子列挙"""
    EQUAL = '='
    NOT_EQUAL = '<>'
    GREATER_THAN = '>'
    LESS_THAN = '<'
    GREATER_THAN_OR_EQUAL = '>='
    LESS_THAN_OR_EQUAL = '<='
    LIKE = 'LIKE'
    NOT_LIKE = 'NOT_LIKE'
    IN = 'IN'
    NOT_IN = 'NOT IN'
    IS_NULL = 'IS NULL'
    IS_NOT_NULL = 'IS NOT NULL'

class EEGSMasterSheetName(Enum):
    """EEGSマスタシート名"""
    AMCMST_SHEET_NAME = "活動項目小分類（事業者）"
    MJSIC_SHEET_NAME = "産業分類"
    MECF_SHEET_NAME = "電気事業者メニュー別"
    MUMST_SHEET_NAME = "ユーザ登録・変更・削除申請表"

class UserApplicationKbn(Enum):
    ADD = "追加"
    UPDATE = "変更"
    DELETE = "削除"

# 業種マスタカラム情報
JICMST_COLUMNS = (
    "CLASSFICATION_ID",
    "LARGE_CATEGORY_CODE",
    "MEDIUM_CATEGORY_CODE", 
    "SMALL_CATEGORY_CODE",
    "DETAIL_CATEGORY_CODE",
    "INDUSTRY_NAME",
    "LARGE_CATEGORY_NAME",
    "MEDIUM_CATEGORY_NAME",
    "START_DATE",
    "END_DATE",
    "CREATION_DATETIME",
    "CREATOR",
    "update_datetime",
    "updateor",
    "delete_flg"
)

# 算定ロジックマスタカラム情報
CALMST_COLUMNS = (
    "LOGIC_ID",
    "NAME",
    "FORMULA",
    "VARIABLES",
    "DESCRIPTION"
)

# 換算係数マスタカラム情報            
CCMST_COLUMNS = (
    "REPORT_YEAR",
    "MAJOR_CATEGORY_ID",
    "MIDDLE_CATEGORY_ID",
    "MINOR_CATEGORY_ID",
    "CONVERSION_COEF",
    "ENERGY_CO2_EMISSION_COEF",
    "UNIT"
)

# 活動項目小分類マスタカラム情報            
AMCMST_COLUMNS = (
    "REPORT_YEAR",
    "MAJOR_CATEGORY_ID",
    "MIDDLE_CATEGORY_ID",
    "MINOR_CATEGORY_ID",
    "MINOR_CATEGORY_NM",
    "UNIT",
    "CONVERSION_COEF",
    "NON_FOSSIL_CONV_COEF",
    "NON_FOSSIL_WEIGHT_COEF",
    "ELECTRIC_DEMAND_OPT_COEF",
    "ENERGY_CO2_EMISSION_COEF",
    "NON_ENERGY_CO2_EMISSION_COEF",
    "CH4_EMISSION_COEF",
    "N2O_EMISSION_COEF",
    "HFC_EMISSION_COEF",
    "PFC_EMISSION_COEF",
    "SF6_EMISSION_COEF",
    "NF3_EMISSION_COEF",
    "CONVERSION_VALUE1",
    "CONVERSION_VALUE2",
    "NON_ENERGY_KBN",
    "GLOBAL_WARMING_LAW_FLAG",
    "ENERGY_EFFICIENCY_LAW_FLAG",
    "ACTIVITY_ITEM_SCREEN_FLAG",
    "SUPPORT_SCREEN_KBN",
    "UNIT_INPUT_ENABLED_FLAG",
    "CONVERSION_COEF_INPUT_FLAG",
    "USAGE_INPUT_ENABLED_FLAG",
    "BY_PRODUCT_INPUT_ENABLED_FLAG",
    "UNUSED_HEAT_INPUT_ENABLED_FLAG",
    "ACTIVITY_MAX_LIMIT",
    "ACTIVITY_MIN_LIMIT",
    "ACTIVITY_ITEM_COMMENT",
    "HEAT_SUPPORT_SCREEN_FLAG",
    "ELECTRICITY_SUPPORT_SCREEN_FLAG",
    "NON_FOSSIL_KBN",
    "SELF_GENERATION_SCREEN_FLAG",
    "DISPLAY_ORDER",
    "START_DATE",
    "END_DATE",
    "CREATED_AT",
    "CREATED_BY",
    "UPDATED_AT",
    "UPDATED_BY",
    "DELETE_FLAG",
)

# 日本標準産業分類マスタカラム情報            
MJSIC_COLUMNS = (
    "DIVISION_CODE",
    "MAJOR_GROUP_CODE",
    "GROUP_CODE",
    "INDUSTRY_CODE",
    "DIVISION_NAME",
    "MAJOR_GROUP_NAME",
    "GROUP_NAME",
    "INDUSTRY_NAME",
    "START_DATE",
    "END_DATE",
    "CREATED_AT",
    "CREATED_BY",
    "UPDATED_AT",
    "UPDATED_BY",
    "DELETE_FLAG",
)

# 電力会社の換算係数マスタカラム情報
MECF_COLUMNS = (
    "ELECTRIC_COMPANY_REG_NO",
    "ELECTRICITY_SUPPLIER_NAME",
    "FISCAL_YEAR",
    "ADJUSTED_EMISSION_FACTOR",
    "START_DATE",
    "END_DATE",
    "CREATION_DATETIME",
    "CREATE_BY",
    "UPDATE_DATETIME",
    "UPDATE_BY",
    "DELETE_FLG",
)

# ユーザ
MUMST_COLUMNS = (
    "USER_MAIL",
    "USER_NAME",
    "COMPANY_NAME",
    "DEPARTMENT_ID",
    "DEPARTMENT_NAME",
    "USER_PASSWORD",
    "USER_ROLE",
    "START_DATE",
    "END_DATE",
    "CREATION_DATETIME",
    "CREATE_BY",
    "UPDATE_DATETIME",
    "UPDATE_BY",
    "DELETE_FLG",
)

# 排出係数マスタカラム情報
ECMST_COLUMNS = (
    "ELECTRIC_COMPANY_REG_NO",
    "ELECTRICITY_SUPPLIER_NAME",
    "FISCAL_YEAR",
    "ADJUSTED_EMISSION_FACTOR"
)

# エリアマスタカラム情報
AIMST_COLUMNS = (
    "AREA_ID",
    "PARENT_AREA_ID",
    "CORPORATE_NUMBER",
    "BUILDING_ID",
    "AREA_NAME",
    "CORPORATE_NAME",
    "BUILDING_NAME",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
)

# エリアマスタカラム情報
FPSTBL_COLUMNS = (
    "FILE_NAME",
    "FILE_PATH",
    "FILE_TYPE",
    "STATUS",
    "CREATION_DATETIME",
    "CREATOR"
)

# エリアマスタカラム情報
KBNMST_COLUMNS = (
    "CATEGORY_CD",
    "CATEGORY_NAME",
    "KBN_CD",
    "KBN_NAME",
    "KBN_SORT",
    "CREATION_DATETIME",
    "CREATOR"
)

ECDMST_COLUMNS = (
    "BUILDING_USAGE",
    "FISCAL_YEAR",
    "ENERGY_CATEGORY_DIV",
    "ENERGY_CATEGORY_NAME",
    "ENERGY_SUB_DIV",
    "ENERGY_SUB_NAME",
    "VALUE",
    "CREATION_DATETIME",
    "CREATOR"
)

ECEMST_COLUMNS =(
    "FISCAL_YEAR",
    "FIXED_PATTERN",
    "ELECTRIC_POWER_2030_PATTERN",
    "CUSTOM_SETTING_PATTERN",
    "NATIONAL_AVERAGE_PATTERN",
    "CREATION_DATETIME",
    "CREATOR"
)

BECRMST_COLUMNS =(			
    "FISCAL_YEAR",
    "MENU_NUM",
    "MENU_ITEM",
    "ENERGY_CONSUMPTION_CATEGORY",
    "CORRECTION_CATEGORY_USAGE",
    "CORRECTION_CATEGORY_RANGE",
    "BASE_ENERGY_CONSUMPTION_RATE",
    "CREATION_DATETIME",
    "CREATOR"
)

CMST_COLUMNS = (
    "FISCAL_YEAR",
    "MENU_NUM",
    "MENU_ITEM",
    "COUNTERMEASURE_MENU",
    "COUNTERMEASURE_FLAG",
    "CREATION_DATETIME",
    "CREATOR"
)

# CN対策実施申込パーティション情報
PARTITION_COLUMNS_CAITBL = (
    "BANK_CODE",
    "CORPORATE_NUMBER",
    "BUILDING_ID",
    "FISCAL_YEAR"
    # "PART_ELECTRIC_COMPANY_REG_NO",
)

PARTITION_COMPANY_COLUMNS = (
    "BANK_CODE",
    "CORPORATE_NUMBER",
    "FISCAL_YEAR"
)

# パーティション情報
SELECT_COLUMNS = (
    "REGISTRATION_SEQ"
)

#計算用DATA
MONTH_DATA =[
    "BANK_CODE",                            #金融機関コード
    "CORPORATE_NUMBER",                     #法人番号
    "BUILDING_NAME",                          #事業所名
    "ENERGY_NAME",                          #エネルギー名称
    "YEAR",                                 #年
    "MONTH",                                #月
    "ENERGY_CONSUMPTION"                    #エネルギー使用量
]

CONSIDERATION_OF_MEASURES_dict ={
    'する' :'0',    
    'しない':'1'
}

officeMonthly_columns = [
    "BANK_CODE",
    "CORPORATE_NUMBER",
    "BUILDING_ID",
    "FISCAL_YEAR",
    "MONTH",
    "ENERGY_CODE",
    "ENERGY_SCOPE",
    "REGISTRATION_SEQ",
    "AREA_ID",
    "AREA_INFORMATION",
    "BUILDING_NAME",
    "YEAR",
    "ENERGY_NAME",
    "ENERGY_CATEGORY",
    "ENERGY_UNITS",
    "ENERGY_CONSUMPTION",
    "CO2_EMISSIONS",
    "CO2_EMISSIONS_AREA_UNIT",
    "CALORIFIC_ENERGY_CONSUMPTION",
    "CALORIFIC_ENERGY_CONSUMPTION_UNIT",
    "CRUDE_OIL_ENERGY_CONSUMPTION",
    "CRUDE_OIL_ENERGY_CONSUMPTION_UNIT",
    "ELECTRIC_CONSUMPTION_UNIT",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

officeYearly_columns = [
    "BANK_CODE",
    "CORPORATE_NUMBER",
    "BUILDING_ID",
    "FISCAL_YEAR",
    "ENERGY_CODE",
    "REGISTRATION_SEQ",
    "AREA_ID",
    "AREA_INFORMATION",
    "BUILDING_NAME",
    "ENERGY_NAME",
    "ENERGY_CATEGORY",
    "ENERGY_UNITS",
    "ENERGY_CONSUMPTION",
    "CO2_EMISSIONS",
    "CO2_EMISSIONS_AREA_UNIT",
    "CALORIFIC_ENERGY_CONSUMPTION",
    "CALORIFIC_ENERGY_CONSUMPTION_UNIT",
    "CRUDE_OIL_ENERGY_CONSUMPTION",
    "CRUDE_OIL_ENERGY_CONSUMPTION_UNIT",
    "ELECTRIC_CONSUMPTION_UNIT",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

corporateMonthly_columns = [
    "BANK_CODE",
    "CORPORATE_NUMBER",
    "FISCAL_YEAR",
    "MONTH",
    "ENERGY_CODE",
    "REGISTRATION_SEQ",
    "YEAR",
    "ENERGY_NAME",
    "ENERGY_CATEGORY",
    "ENERGY_UNITS",
    "ENERGY_CONSUMPTION",
    "CO2_EMISSIONS",
    "CO2_EMISSIONS_AREA_UNIT",
    "CALORIFIC_ENERGY_CONSUMPTION",
    "CALORIFIC_ENERGY_CONSUMPTION_UNIT",
    "CRUDE_OIL_ENERGY_CONSUMPTION",
    "CRUDE_OIL_ENERGY_CONSUMPTION_UNIT",
    "ELECTRIC_CONSUMPTION_UNIT",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

corporateYearly_columns = [
    "BANK_CODE",
    "CORPORATE_NUMBER",
    "FISCAL_YEAR",
    "ENERGY_CODE",
    "REGISTRATION_SEQ",
    "ENERGY_NAME",
    "ENERGY_CATEGORY",
    "ENERGY_UNITS",
    "ENERGY_CONSUMPTION",
    "CO2_EMISSIONS",
    "CO2_EMISSIONS_AREA_UNIT",
    "CALORIFIC_ENERGY_CONSUMPTION",
    "CALORIFIC_ENERGY_CONSUMPTION_UNIT",
    "CRUDE_OIL_ENERGY_CONSUMPTION",
    "CRUDE_OIL_ENERGY_CONSUMPTION_UNIT",
    "ELECTRIC_CONSUMPTION_UNIT",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

#####以下はSTEP2リソース#####
#契約先金融機関基本情報マスタ
mCustomerBankBasicInfo_colums = [
    "BANK_CODE",
    "START_DATE",
    "END_DATE",
    "BANK_NAME",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

#支店マスタ
mBankBranchInfo_colums = [
    "BANK_CODE",
    "BRANCH_CODE",
    "START_DATE",
    "END_DATE",
    "BANK_NAME",
    "DEPARTMENT_BRANCH_NAME",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

#金融機関担当者マスタ
mBankStaffInfo_colums = [
    "USER_CD",
    "BANK_CODE",
    "BRANCH_CODE",
    "CONTACT_PERSON_NAME_LOCAL_BANK",
    "START_DATE",
    "END_DATE",
    "BANK_NAME",
    "DEPARTMENT_BRANCH_NAME",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

#企業基本情報マスタ
mCorporateBasicInfo_colums = [
    "CORPORATE_NUMBER",
    "START_DATE",
    "END_DATE",
    "CORPORATE_NAME",
    "OFFICE_ADDRESS",
    "NUMBER_OFFICES",
    "INDUSTRY_BROAD_CATEGORIZATION_NAME",
    "INDUSTRY_INTERMEDIATE_CLASSIFICATION_NAME",
    "INDUSTRY_BROAD_CATEGORIZATION",
    "INDUSTRY_INTERMEDIATE_CLASSIFICATION",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

#レポート格納情報
reportStorageInfo_colums = [
    "BANK_CODE",
    "BRANCH_CODE",
    "CORPORATE_NUMBER",
    "BUILDING_ID",
    "FISCAL_YEAR",
    "REPORT_TYPE",
    "REGISTRATION_SEQ",
    "FILE_ID",
    "REPORT_LOCATION",
    "STATUS",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

officeMonthly_hive_columns = [
    "MONTH",
    "ENERGY_CODE",
    "REGISTRATION_SEQ",
    "AREA_ID",
    "AREA_INFORMATION",
    "BUILDING_NAME",
    "YEAR",
    "ENERGY_NAME",
    "ENERGY_CATEGORY",
    "ENERGY_UNITS",
    "ENERGY_CONSUMPTION",
    "CO2_EMISSIONS",
    "CO2_EMISSIONS_AREA_UNIT",
    "CALORIFIC_ENERGY_CONSUMPTION",
    "CALORIFIC_ENERGY_CONSUMPTION_UNIT",
    "CRUDE_OIL_ENERGY_CONSUMPTION",
    "CRUDE_OIL_ENERGY_CONSUMPTION_UNIT",
    "ELECTRIC_CONSUMPTION_UNIT",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

officeYearly_hive_columns = [
    "ENERGY_CODE",
    "REGISTRATION_SEQ",
    "AREA_ID",
    "AREA_INFORMATION",
    "BUILDING_NAME",
    "ENERGY_NAME",
    "ENERGY_CATEGORY",
    "ENERGY_UNITS",
    "ENERGY_CONSUMPTION",
    "CO2_EMISSIONS",
    "CO2_EMISSIONS_AREA_UNIT",
    "CALORIFIC_ENERGY_CONSUMPTION",
    "CALORIFIC_ENERGY_CONSUMPTION_UNIT",
    "CRUDE_OIL_ENERGY_CONSUMPTION",
    "CRUDE_OIL_ENERGY_CONSUMPTION_UNIT",
    "ELECTRIC_CONSUMPTION_UNIT",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

corporateMonthly_hive_columns = [
    "MONTH",
    "ENERGY_CODE",
    "REGISTRATION_SEQ",
    "YEAR",
    "ENERGY_NAME",
    "ENERGY_CATEGORY",
    "ENERGY_UNITS",
    "ENERGY_CONSUMPTION",
    "CO2_EMISSIONS",
    "CO2_EMISSIONS_AREA_UNIT",
    "CALORIFIC_ENERGY_CONSUMPTION",
    "CALORIFIC_ENERGY_CONSUMPTION_UNIT",
    "CRUDE_OIL_ENERGY_CONSUMPTION",
    "CRUDE_OIL_ENERGY_CONSUMPTION_UNIT",
    "ELECTRIC_CONSUMPTION_UNIT",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

corporateYearly_hive_columns = [
    "ENERGY_CODE",
    "REGISTRATION_SEQ",
    "ENERGY_NAME",
    "ENERGY_CATEGORY",
    "ENERGY_UNITS",
    "ENERGY_CONSUMPTION",
    "CO2_EMISSIONS",
    "CO2_EMISSIONS_AREA_UNIT",
    "CALORIFIC_ENERGY_CONSUMPTION",
    "CALORIFIC_ENERGY_CONSUMPTION_UNIT",
    "CRUDE_OIL_ENERGY_CONSUMPTION",
    "CRUDE_OIL_ENERGY_CONSUMPTION_UNIT",
    "ELECTRIC_CONSUMPTION_UNIT",
    "CREATION_DATETIME",
    "CREATOR",
    "UPDATE_DATETIME",
    "UPDATEOR",
    "DELETE_FLG"
]

# エネルギーマッピング
basic_unit_map = {
    "kg": "t",
    "L": "kl",
    "l": "kl",
    "m3": "千m3",
    "kwh": "千kWh",
    "kWh": "千kWh",
    "1000kwh": "千kWh",
    "1000kWh": "千kWh"
}

# 熱エネルギー優先順位
heat_energy_priority = {
    "GJ": 3,
    "MJ": 2,
    "Mcal": 1
}

#ガス優先順位
mass_volume_priority = {
    "t": 3,
    "kg": 2,
    "m3": 1
}

#ガス対象エネルギーコード
gas_energy_code = {
    "0100190000"
}

# 変換係数の表
conversion_data = [
    ("kg", "t", 0.001),
    ("L", "kl", 0.001),
    ("l", "kl", 0.001),
    ("m3", "千m3", 0.001),
    ("kwh", "千kWh", 0.001),
    ("kWh", "千kWh", 0.001),
    ("MJ", "GJ", 0.001),
    ("Mcal", "GJ", 0.00418),
    ("m3", "t", 0.00218),
    ("kg-gas", "t", None),
    ("m3", "kg", 2.18),
    ("kg", "m3", 1/2.18),
    ("Mcal", "MJ", 4.18),

    ("t", "t", 1),
    ("kl", "kl", 1),
    ("千m3", "千m3", 1),
    ("GJ", "GJ", 1),
    ("千kwh", "千kWh", 1),
    ("千kWh", "千kWh", 1),
    ("1000kwh", "千kWh", 1),
    ("1000kWh", "千kWh", 1),
    ("1000kWh", "1000kWh", 1),

    ("kg", "kg", 1),
    ("m3", "m3", 1),
    ("MJ", "MJ", 1),
    ("Mcal", "Mcal", 1),
    ("L", "L", 1),
    ("l", "l", 1),
    ("kwh", "kWh", 1),
    ("kWh", "kWh", 1),
    
    # ("kg", "kg", 1),
    
    ("1000m3", "千m3", 1),
    ("t", "kg", 1000),
]

propane_conversion_data = [
    ("m3", "t", 0.00199),
]