from cndx_corp_back.logic.building.common.calculating_process import (
    get_calculation_result,
)

# 共通アルゴリズムクラス


# calorieConvert = lambda energyData, calorificCoefficient : float(energyData)*float(calorificCoefficient)/1000
# calorieConvert = lambda energyData, calorificCoefficient : float(energyData)*float(calorificCoefficient)
calorieConvert = (
    lambda calmst, energyData, calorificCoefficient: get_calculation_result(
        1,
        {
            "EnergyUsage": safe_float(energyData),
            "UnitCalorificValue": safe_float(calorificCoefficient),
        },
        calmst,
    )
)
"""
関数名：熱量換算アルゴリズム
パラメータ1:エネルギーデータ
パラメータ2:発熱量換算係数
リターン値:熱量
"""

# crudeOilConvert = lambda energyData,calorificCoefficient,crudeOilCoefficient : float(energyData)*float(calorificCoefficient)*float(crudeOilCoefficient)/1000
# crudeOilConvert = lambda energyData,calorificCoefficient,crudeOilCoefficient : float(energyData)*float(calorificCoefficient)*float(crudeOilCoefficient)
crudeOilConvert = lambda calmst, energyData, calorificCoefficient, crudeOilCoefficient: get_calculation_result(
    2,
    {
        "HeatConverting": safe_float(energyData) * float(calorificCoefficient),
        "CrudeOilConverting": safe_float(crudeOilCoefficient),
    },
    calmst,
)
"""
関数名：原油換算アルゴリズム
パラメータ1:エネルギーデータ
パラメータ2:発熱量換算係数
パラメータ3:原油換算係数
リターン値:原油使用量
"""

# co2EmissionsConvert = lambda calmst, energyData,co2Coefficient : float(energyData)*float(co2Coefficient)
co2EmissionsConvert = lambda calmst, energyData, co2Coefficient: get_calculation_result(
    3,
    {
        "TotalEnergyUsage": safe_float(energyData),
        "Co2Converting": safe_float(co2Coefficient),
    },
    calmst,
)
"""
CRUDE_OIL
関数名 : 電力外CO2排出量換算アルゴリズム
パラメータ1:エネルギーデータ
パラメータ2:CO2排出量換算係数(電力の場合、電力会社の排出係数で計算)
リターン値:CO2排出量
"""

co2ElectricExceptCoefficient = (
    lambda calmst, unitCalorificValue, carbonDischargeFactor: get_calculation_result(
        5,
        {
            "UnitCalorificValue": safe_float(unitCalorificValue),
            "CarbonDischargeFactor": safe_float(carbonDischargeFactor),
        },
        calmst,
    )
)
"""
関数名 : 電力外CO2排出量係数取得
パラメータ1:計算マスタ
パラメータ2:エネルギー使用量
パラメータ3:CO2換算係数
リターン値:CO2排出量係数
"""

co2ElectricCoefficient = (
    lambda calmst, energyUsage, carbonDischargeFactor: get_calculation_result(
        4,
        {
            "MonthlyEnergyUsage": safe_float(energyUsage),
            "MonthlyDischarge": safe_float(carbonDischargeFactor),
        },
        calmst,
    )
)
"""
関数名 : 電力CO2排出量換算アルゴリズム
パラメータ1:計算マスタ
パラメータ2:エネルギー使用量
パラメータ3:CO2換算係数
リターン値:CO2排出量係数
"""


def safe_float(val):
    if val in (None, "None", ""):
        return 0.0
    return float(val)
