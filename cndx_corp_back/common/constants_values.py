from enum import Enum


CRUDE_OIL_ENERGY_CONSUMPTION = 0.0258 #原油換算係数
CO2_EMISSION_CITY_GAS_COEFFICIENT = 2.05 #都市ガスCO2排出係数
CO2_EMISSION_OTHERS_COEFFICIENT = 0.0532 #熱CO2排出係数
CO2_EMISSION_ELECRIC_COEFFICIENT = 0.000551 #2013電力CO2排出係数
CO2_EMISSION_INDUSTRIAL_EXCEPT_COEFFICIENT_2013 = 0.057 #産業用以外の蒸気、温水、冷水
CO2_EMISSION_INDUSTRIAL_COEFFICIENT_2013 = 0.06 #産業用蒸気
HEAT_CONSUMPTION_CITY_GAS = 40

#エネルギーコード定数
ENERGY_CODE_CITY_GAS = '0100230000' #都市ガス
ENERGY_CODE_INDUSTRIAL_STEAM = '0300010000' #産業用蒸気
ENERGY_CODE_INDUSTRIAL_EXCEPT_STEAM = '0300020000' #産業用以外の蒸気
ENERGY_CODE_HOT_WATER = '0300030000' #温水
ENERGY_CODE_COLD_WATER = '0300040000' #冷水
ENERGY_CODE_ELECTRIC_POWER_2022 = '0200010001' #電力
ENERGY_CODE_ELECTRIC_POWER_2023 = '0200010011' #電力

#CN status by ZEB利用係数
#電気換算係数
HEAT_CONSUMPTION_ELECRIC_COEFFICIENT_2023 = 8.64
#産業用以外の蒸気、温水、冷水
HEAT_CONSUMPTION_INDUSTRIAL_EXCEPT_COEFFICIENT_2023 = 1.19
#産業用蒸気
HEAT_CONSUMPTION_INDUSTRIAL_COEFFICIENT_2023 = 1.17
#熱量換算係数データソース
HEAT_CONVERSION_COEFFICIENT_SOURCE = "EEGSマスタ（活動項目小分類（事業者））"
#CO2調整後排出係数データソース(電力以外)
CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC = "EEGSマスタ（活動項目小分類（事業者））"
#CO2調整後排出係数データソース
CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_ELECTRIC = "EEGSマスタ（電気事業者メニュー別）"
#CO2調整後排出係数データソース
CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_HEAT = "EEGSマスタ（熱供給事業者メニュー別）"
#CO2調整後排出係数データソース
CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_NFCFIT = "非化石証書定数マスタ"
#CO2調整後排出係数データソース
CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_HSM = "熱供給事業者メニュー別マスタ"
#電気名称
ELECTRIC_POWER_NAME = "電気"

#CO2調整後排出量単位
CO2_ADJUSTED_EMISSIONS_UNIT = "ｔ-CO2"
#熱量換算エネルギー使用量量単位
HEAT_CONVERTED_ENERGY_UNIT = "GJ"
# 熱量換算係数単位
HEAT_CONVERSION_COEFFICIENT_UNIT = "MJ"

BANK_ORGANIZATION_MARK = "BNK"

class ReportTypeValue(Enum):
    """レポート種別"""
    CN_REPORT_PDF = "1"
    """CNレポートPDF"""
    CN_REPORT_CSV = "2"
    """CNレポートCSV"""
    MISSING_DATA_PDF = "3"
    """データ欠損一覧PDF"""
    KPI_CSV = "4"
    """KPI一覧CSV"""
    POWER_VISUAL_PDF = "6"
    """電力見える化レポート"""

class ReportType(Enum):
    """レポート名英語"""
    CN_PROFILE = "cn_profile"
    ELEC_VIS = "elec_vis"

class FormatTypeCode(Enum):
    SIMPLE = "0"
    """簡易版"""
    STANTARD = "1"
    """標準版"""

class SiteSelectionType(Enum):
    ALL = "01"
    """企業全体"""
    GROUP = "02"
    """グループ"""
    SINGLE = "03"
    """単拠点"""

class CnProfileReportFormatName(Enum):
    STAGING_SINGLE = "CNカルテ_地銀&可視化_レポートテンプレート(単拠点)_postgre"
    """ステージング"""
    IT_SINGLE = "CNカルテ_地銀&可視化_レポートテンプレート(単拠点)_postgre_it"
    """総合"""
    PD_SINGLE = "CNカルテ_地銀&可視化_レポートテンプレート(単拠点)_postgre_pd"
    """本番"""
    STAGING_MULTIPLE = "CNカルテ_地銀&可視化_レポートテンプレート(複数拠点)_postgre"
    """ステージング"""
    IT_MULTIPLE = "CNカルテ_地銀&可視化_レポートテンプレート(複数拠点)_postgre_it"
    """総合"""
    PD_MULTIPLE = "CNカルテ_地銀&可視化_レポートテンプレート(複数拠点)_postgre_pd"
    """本番"""

class ElectricPowerReportFormatName(Enum):
    STAGING = "電力見える化_STEP3"
    """ステージング"""
    IT = "電力見える化_STEP3_it"
    """総合"""
    PD = "電力見える化_STEP3_pd"
    """本番"""

class CnProfileDataSourceName(Enum):
    STAGING = "bnk_datasouce_step3_postgre"
    """ステージング"""
    IT = "bnk_datasouce_step3_postgre_it"
    """総合"""
    PD = "bnk_datasouce_step3_postgre_pd"
    """本番"""

class ElectricPowerDataSourceName(Enum):
    STAGING_ROW = "electric_power_datasource_step3_row_postgre"
    """ステージング"""
    IT_ROW = "electric_power_datasource_step3_row_postgre_it"
    """総合"""
    PD_ROW = "electric_power_datasource_step3_row_postgre_pd"
    """本番"""
    STAGING_COL = "electric_power_datasource_step3_col_postgre"
    """ステージング"""
    IT_COL = "electric_power_datasource_step3_col_postgre_it"
    """総合"""
    PD_COL = "electric_power_datasource_step3_col_postgre_pd"
    """本番"""

class ReportStatus(Enum):
    WORKING = "0"
    """作成中"""
    DONE = "1"
    """作成済"""
    ERROR = "9"
    """作成エラー"""