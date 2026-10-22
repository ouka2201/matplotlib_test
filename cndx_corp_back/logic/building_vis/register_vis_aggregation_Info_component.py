import decimal
import math
import time
import unicodedata
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from time import perf_counter

import numpy as np
import pandas as pd
from flask import abort
from sqlalchemy import Column, MetaData, String, Table, inspect, text, tuple_
from werkzeug.exceptions import HTTPException

import cndx_corp_back.common.constants_colums as constants_colums
import cndx_corp_back.common.constants_values as constants_values
import cndx_corp_back.common.log as log
import cndx_corp_back.common.utils as utils
import cndx_corp_back.logic.building.common.common_energy_algorithms as ceas
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.common.hql_processor import insert_data
from cndx_corp_back.entity.activity_minor_category_mst_entity import (
    ActivityMinorCategoryMst,
)
from cndx_corp_back.entity.electric_supplier_menu_mst import ElectricSupplierMenuMst

# from cndx_corp_back.entity.city_gas_heating_value_mst import CityGasHeatingValueMst
from cndx_corp_back.entity.heat_supplier_menu_mst import HeatSupplierMenuMst
from cndx_corp_back.entity.m_calculation_logic_entity import MCalculationLogic
from cndx_corp_back.entity.m_competitor_industry import MCompetitorIndustry
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.m_weather_data_info_entity import MWeatherDataInfo
from cndx_corp_back.entity.non_fossil_cert_constant_mst_entity import (
    NonFossilCertConstantMst,
)
from cndx_corp_back.entity.non_fossil_energy_type_mst_entity import (
    NonFossilEnergyTypeMst,
)
from cndx_corp_back.entity.t_annual_building_energy_aggregation_entity import (
    TAnnualBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_annual_corporate_energy_aggregation_entity import (
    TAnnualCorporateEnergyAggregation,
)
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_energy_storage_common_for_visualization import (
    TEnergyStorageCommonForVisualization,
)
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_monthly_corporate_energy_aggregation_entity import (
    TMonthlyCorporateEnergyAggregation,
)
from cndx_corp_back.logic.building_vis.building_vis_utils import nan_to_none
from cndx_corp_back.logic.building_vis.master_loader import MasterLoader
from cndx_corp_back.utils.utils import get_message

DOT = constants_colums.SpecialChars.DOT.value
BLANK = constants_colums.SpecialChars.BLANK.value

# log用instance
logger = log.CorpLogger()


# @log_time
def register_energy_aggregation_info(
    conn,
    basic_df,
    df_generalInfo,
    df_buildingInfo,
    df_energyInfo,
    target_years,
    logger=None,
):
    """
    関数名：企業カルテエネルギー集計結果登録
        :params df_generalInfo: 企業基本情報
        :params df_buildingInfo: 事業所情報
        :params df_energyInfo: エネルギー情報
    """
    master_loader: MasterLoader = MasterLoader(conn)
    try:
        ccmst = master_loader.get_ccmst()
        ecmst = master_loader.get_ecmst()
        calmst = master_loader.get_calmst()
        hsmst = master_loader.get_hsmst()
        ccimst = master_loader.get_ccimst()
        wdimst = master_loader.get_wdimst()
        nfcmst = master_loader.get_nfcmst()
        gasmst = master_loader.get_gasmst()

        # 都道府県情報動的に指定する列名
        col_names = ccimst["EN_CODE_NAME"].str.upper().to_list()

        # 天気情報取り出す
        df_wdimst = wdimst[["TARGET_YEAR", "TARGET_MONTH"] + col_names]

        mapping = dict(zip(ccimst["EN_CODE_NAME"].str.upper(), ccimst["CODE"]))
        # 英字名から県コードへ変換
        df_wdimst = df_wdimst.rename(columns=mapping)

        # 重複名前の列削除
        dup_cols = df_wdimst.columns[df_wdimst.columns.duplicated()].unique()
        df_wdimst = df_wdimst.drop(columns=dup_cols)

        # 建物月別DF
        monthlyBuildingEnergyAggregation_df = get_building_month_df(
            conn,
            basic_df,
            df_buildingInfo,
            df_energyInfo,
            ccmst,
            ecmst,
            calmst,
            hsmst,
            df_wdimst,
            nfcmst,
            gasmst,
            target_years,
        )

        monthlyBuildingEnergyAggregation_df[
            "ENERGY_CATEGORY_NAME"
        ] = monthlyBuildingEnergyAggregation_df["ENERGY_CATEGORY_NAME"].replace(
            {
                "重油（C重油）": "Ｂ・Ｃ重油",
                "液化石油ガス（ＬＰＧ）": "LPガス",
                "液化天然ガス（LNG）": "液化天然ガス",
            }
        )

        monthlyBuildingEnergyAggregation_df.loc[
            monthlyBuildingEnergyAggregation_df["HEAT_CONVERTED_ENERGY_UNIT"] == "MJ",
            "HEAT_CONVERTED_ENERGY_USAGE",
        ] /= 1000
        # 事業所年度別DF
        annualBuildingEnergyAggregation_df = get_building_year_df(
            conn, basic_df, monthlyBuildingEnergyAggregation_df
        )

        # 企業月別DF
        monthlyCorporateEnergyAggregation_df = get_company_month_df(
            conn, basic_df, monthlyBuildingEnergyAggregation_df
        )

        # 企業年度別DF
        annualCorporateEnergyAggregation_df = get_company_year_df(
            conn, basic_df, monthlyBuildingEnergyAggregation_df
        )

        # for model in [TMonthlyBuildingEnergyAggregation, TMonthlyCorporateEnergyAggregation]:
        #     event.listen(model, "before_insert", before_save_validate)
        #     event.listen(model, "before_update", before_save_validate)

        # conn.commit()

        return (
            monthlyBuildingEnergyAggregation_df,
            annualBuildingEnergyAggregation_df,
            monthlyCorporateEnergyAggregation_df,
            annualCorporateEnergyAggregation_df,
        )

    except HTTPException:
        raise


# @log_time
def get_value(
    officeUsedEnergyInfo,
    energyRowData,
    energy_quantity_for_law,
    heatSupplyRegNo,
    fiscal_year,
    calmst,
    hsmst,
    electric_co2_emission_coef,
    gas_heat_coeff,
    calorificEnergyConsumption,
    co2EmissionCoefficient,
    nfcmst_sub,
):
    """
    熱量、CO2排出量計算
    """
    calorificEnergyConsumption = (
        float(calorificEnergyConsumption)
        if calorificEnergyConsumption not in ["", None]
        else -1
    )
    co2EmissionCoefficient = (
        float(co2EmissionCoefficient)
        if co2EmissionCoefficient not in ["", None]
        else -1
    )

    if not energy_quantity_for_law or pd.isna(energy_quantity_for_law):
        # エネルギー使用量（省エネ法）が None, 0 , ''の場合は 全て0で返却
        energy_quantity_for_law = 0

    else:
        # 熱量換算値
        # calorificEnergyConsumption = energyRowData.HEAT_CONVERTED_ENERGY_USAGE_MONTHLY
        # CO2調整後排出値
        # co2EmissionCoefficient = energyRowData.CO2_ADJUSTED_EMISSIONS

        # 熱量換算係数
        conversion_coef = (
            energyRowData.HEAT_CONVERSION_COEFFICIENT
            if (energyRowData.HEAT_CONVERSION_COEFFICIENT not in ["", None])
            and calorificEnergyConsumption != -1
            else officeUsedEnergyInfo["CONVERSION_COEF"]
        )
        # CO2調整後排出係数
        co2_emission_coef = (
            energyRowData.CO2_ADJUSTED_EMISSION_FACTOR
            if (energyRowData.CO2_ADJUSTED_EMISSION_FACTOR not in ["", None])
            and co2EmissionCoefficient != -1
            else officeUsedEnergyInfo["ENERGY_CO2_EMISSION_COEF"]
        )

        if calorificEnergyConsumption == -1 and officeUsedEnergyInfo is not None:
            # ========== 熱量換算値算出 ==========

            # 都市ガス（エネルギー使用量（省エネ法）* 40 代替値<都市ガス事業者別単位発熱量>）
            if constants_values.ENERGY_CODE_CITY_GAS == energyRowData.ENERGY_CODE:
                calorificEnergyConsumption = ceas.calorieConvert(
                    calmst, energy_quantity_for_law, gas_heat_coeff
                )
            else:
                # 都市ガス以外（エネルギー使用量（省エネ法）* 換算係数<EEGSマスタ>）
                calorificEnergyConsumption = ceas.calorieConvert(
                    calmst, energy_quantity_for_law, conversion_coef
                )

        if co2EmissionCoefficient == -1 and officeUsedEnergyInfo is not None:
            # ========== CO2調整後排出量算出 ==========

            # 都市ガス
            if (
                constants_values.ENERGY_CODE_CITY_GAS == energyRowData.ENERGY_CODE
            ):  # 2024年度都市ガス
                co2_emission_coef = constants_values.CO2_EMISSION_CITY_GAS_COEFFICIENT
                co2EmissionCoefficient = ceas.co2EmissionsConvert(
                    calmst, energy_quantity_for_law, co2_emission_coef
                )
            # 熱
            elif energyRowData.ENERGY_CODE.startswith("03"):
                # 熱供給事業者別の調整後排出係数係数取得
                if (
                    constants_values.ENERGY_CODE_INDUSTRIAL_STEAM
                    == energyRowData.ENERGY_CODE
                ):  # 産業用蒸気
                    co2_emission_coef = (
                        None
                        if officeUsedEnergyInfo is None
                        else officeUsedEnergyInfo.get("ENERGY_CO2_EMISSION_COEF")
                    )
                # CO2調整後排出量算出 (エネルギー使用量（省エネ法）* CO2排出係数)
                # co2_emission_coef = utils.get_heatSupplyHeatCoefficient(hsmst, energyRowData.SUPPLIER_REG_NO, str(fiscal_year))[0]
                else:
                    co2_emission_coef = utils.get_heatSupplyHeatCoefficient(
                        hsmst,
                        energyRowData.SUPPLIER_REG_NO,
                        energyRowData.SUPPLY_MENU_NO,
                        energyRowData.SUPPLY_MENU,
                        fiscal_year,
                        nfcmst_sub,
                        False,
                    )
                co2EmissionCoefficient = ceas.co2EmissionsConvert(
                    calmst, energy_quantity_for_law, co2_emission_coef
                )
            # 電気
            elif (
                constants_values.ENERGY_CODE_ELECTRIC_POWER_2022
                == energyRowData.ENERGY_CODE
                or constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
                == energyRowData.ENERGY_CODE
            ):
                # 電力のCO2調整後排出係数算出 (エネルギー使用量（省エネ法）* 電気事業者調整後排出係数 * 1000)
                co2EmissionCoefficient = ceas.co2ElectricCoefficient(
                    calmst, energy_quantity_for_law, electric_co2_emission_coef
                )

            # 電気、熱、都市ガス以外
            else:
                # 電気と熱以外場合のCO2排出係数取得（EEGSマスタから 換算係数<単位発熱量> * 排出係数<エネ起CO2> * 44/12）
                coefficient = ceas.co2ElectricExceptCoefficient(
                    calmst, conversion_coef, co2_emission_coef
                )
                # CO2調整後排出量算出 (エネルギー使用量（省エネ法）* CO2排出係数)
                co2EmissionCoefficient = ceas.co2EmissionsConvert(
                    calmst, energy_quantity_for_law, coefficient
                )

    return calorificEnergyConsumption, co2EmissionCoefficient, co2_emission_coef


# @log_time
def get_value_once_energy(
    officeUsedEnergyInfo, energyRowData, energy_quantity_for_law, calmst, gas_heat_coeff
):
    """
    一次エネルギー換算
    熱量、CO2排出量計算
    """
    # 熱量換算エネルギー使用量
    calorificEnergyConsumption = co2EmissionCoefficient = None
    if officeUsedEnergyInfo is not None:
        if (
            energy_quantity_for_law is None
            or energy_quantity_for_law == ""
            or (
                isinstance(energy_quantity_for_law, float)
                and math.isnan(energy_quantity_for_law)
            )
        ):
            # energy_quantity_for_law = 0
            pass

        # 都市ガスの場合、熱量係数40固定
        if constants_values.ENERGY_CODE_CITY_GAS == energyRowData.ENERGY_CODE:
            calorificEnergyConsumption = ceas.calorieConvert(
                calmst, energy_quantity_for_law, gas_heat_coeff
            )
        # 産業用以外の蒸気、温水、冷水
        elif (
            constants_values.ENERGY_CODE_INDUSTRIAL_EXCEPT_STEAM
            == energyRowData.ENERGY_CODE
            or constants_values.ENERGY_CODE_HOT_WATER == energyRowData.ENERGY_CODE
            or constants_values.ENERGY_CODE_COLD_WATER == energyRowData.ENERGY_CODE
        ):
            calorificEnergyConsumption = ceas.calorieConvert(
                calmst,
                energy_quantity_for_law,
                constants_values.HEAT_CONSUMPTION_INDUSTRIAL_EXCEPT_COEFFICIENT_2023,
            )
        # 産業用蒸気
        elif constants_values.ENERGY_CODE_INDUSTRIAL_STEAM == energyRowData.ENERGY_CODE:
            calorificEnergyConsumption = ceas.calorieConvert(
                calmst,
                energy_quantity_for_law,
                constants_values.HEAT_CONSUMPTION_INDUSTRIAL_COEFFICIENT_2023,
            )
        # 電気
        elif energyRowData.ENERGY_CODE[:2] == "02":
            calorificEnergyConsumption = ceas.calorieConvert(
                calmst,
                energy_quantity_for_law,
                constants_values.HEAT_CONSUMPTION_ELECRIC_COEFFICIENT_2023,
            )
        # 上記以外
        else:
            calorificEnergyConsumption = ceas.calorieConvert(
                calmst, energy_quantity_for_law, officeUsedEnergyInfo["CONVERSION_COEF"]
            )

        # CO2排出量
        # 都市ガスの場合、2.05固定
        if constants_values.ENERGY_CODE_CITY_GAS == energyRowData.ENERGY_CODE:
            co2EmissionCoefficient = ceas.co2EmissionsConvert(
                calmst,
                energy_quantity_for_law,
                constants_values.CO2_EMISSION_CITY_GAS_COEFFICIENT,
            )
        # 電気の場合、0.000551固定
        elif energyRowData.ENERGY_CODE[:2] == "02":
            co2EmissionCoefficient = ceas.co2ElectricCoefficient(
                calmst,
                energy_quantity_for_law,
                constants_values.CO2_EMISSION_ELECRIC_COEFFICIENT,
            )
        # 産業用以外の蒸気、温水、冷水の場合、固定0.057
        elif (
            constants_values.ENERGY_CODE_INDUSTRIAL_EXCEPT_STEAM
            == energyRowData.ENERGY_CODE
            or constants_values.ENERGY_CODE_HOT_WATER == energyRowData.ENERGY_CODE
            or constants_values.ENERGY_CODE_COLD_WATER == energyRowData.ENERGY_CODE
        ):
            co2EmissionCoefficient = ceas.co2EmissionsConvert(
                calmst,
                energy_quantity_for_law,
                constants_values.CO2_EMISSION_INDUSTRIAL_EXCEPT_COEFFICIENT_2013,
            )
        # 産業用蒸気の場合、固定0.06
        elif constants_values.ENERGY_CODE_INDUSTRIAL_STEAM == energyRowData.ENERGY_CODE:
            co2EmissionCoefficient = ceas.co2EmissionsConvert(
                calmst,
                energy_quantity_for_law,
                constants_values.CO2_EMISSION_INDUSTRIAL_COEFFICIENT_2013,
            )
        else:
            coefficient = ceas.co2ElectricExceptCoefficient(
                calmst,
                officeUsedEnergyInfo["CONVERSION_COEF"],
                (
                    officeUsedEnergyInfo["ENERGY_CO2_EMISSION_COEF"]
                    if officeUsedEnergyInfo is not None
                    and officeUsedEnergyInfo["ENERGY_CO2_EMISSION_COEF"]
                    else 0
                ),
            )
            co2EmissionCoefficient = ceas.co2EmissionsConvert(
                calmst, energy_quantity_for_law, coefficient
            )

    return calorificEnergyConsumption, co2EmissionCoefficient


# @log_time
def get_building_month_entity(
    session,
    basic_df,
    energyRowData,
    officeUsedEnergyInfo,
    calorificEnergyConsumption,
    co2EmissionCoefficient,
    calorificEnergyConsumption_2023,
    co2EmissionCoefficient_2013,
    buildingArea,
    electric_co2_emission_coef,
    heat_co2_emission_coef,
    updated_energy_dict: dict[str, any],
    building_month_list,
    vis_common_list,
    excel_row_list,
    co2EmissionCoefficient_avg,
    tEnergyStorageCommonInfo,
):
    updated_energy_code = updated_energy_dict.get("ENERGY_CODE")
    updated_energy_quantity = updated_energy_dict.get("ENERGY_QUANTITY")
    updated_energy_for_law = updated_energy_dict.get("ENERGY_QUANTITY_FOR_LAW")
    updated_energy_for_report = updated_energy_dict.get("ENERGY_QUANTITY_FOR_REPORT")
    updated_fiscal_year = str(updated_energy_dict.get("FISCAL_YEAR"))
    updated_temp_building = updated_energy_dict.get("TEMPERATURE_BUILDING")
    user_id = basic_df["CREATED_BY"].iloc[0]

    year_month = str(energyRowData.YEAR) + str(energyRowData.MONTH).zfill(2)

    common_filters = dict(
        corporate_number=basic_df["CORPORATE_NUMBER"].iloc[0],
        agreement_category=basic_df["AGREEMENT_CATEGORY"].iloc[0],
        org_id=basic_df["ORG_ID"].iloc[0],
        building_id=energyRowData.BUILDING_ID,
        energy_code=updated_energy_code,
    )
    input_supplier_name = (
        energyRowData.INPUT_SUPPLIER_NAME
        if energyRowData.INPUT_SUPPLIER_NAME is not None
        else energyRowData.BUILDING_ID
    )
    input_supplier_name = (
        unicodedata.normalize("NFC", input_supplier_name.strip())
        if isinstance(input_supplier_name, str)
        else input_supplier_name
    )

    vis_common_entity: TEnergyStorageCommonForVisualization = (
        session.query(TEnergyStorageCommonForVisualization)
        .filter_by(
            **common_filters,
            year_month=year_month,
            input_supplier_name=input_supplier_name,
            energy_name=energyRowData.ENERGY_NAME_JP,
        )
        .first()
    )

    if not vis_common_entity:
        vis_common_entity = TEnergyStorageCommonForVisualization(
            **common_filters,
            year_month=year_month,
            input_supplier_name=input_supplier_name,
            energy_name=energyRowData.ENERGY_NAME_JP,
        )
        vis_common_entity.created_by = user_id
        session.add(vis_common_entity)
    else:
        # hearing_entity: TEnergyStorageCommonForVisualization = session.query(TEnergyStorageCommonForVisualization).filter_by(
        #     corporate_number= basic_df['CORPORATE_NUMBER'].iloc[0],
        #     agreement_category= basic_df['AGREEMENT_CATEGORY'].iloc[0],
        #     # org_id= basic_df["ORG_ID"].iloc[0], # 組織IDを条件から除外
        #     building_id= energyRowData.BUILDING_ID,
        #     energy_code= updated_energy_code,
        #     year_month=year_month,
        #     input_supplier_name=input_supplier_name).first()
        # if hearing_entity:
        #     hearing_entity.delete_flg = True
        vis_common_entity.updated_by = user_id

    compare_entity_with_model(TEnergyStorageCommonForVisualization, vis_common_entity)

    vis_common_list.append(vis_common_entity)

    ep_customer_number = basic_df.loc[
        basic_df["BUILDING_ID"] == energyRowData.BUILDING_ID, "EP_CUSTOMER_NUMBER"
    ].iloc[0]
    ep_office_code = basic_df.loc[
        basic_df["BUILDING_ID"] == energyRowData.BUILDING_ID, "EP_OFFICE_CODE"
    ].iloc[0]
    site_address_prefecture = basic_df.loc[
        basic_df["BUILDING_ID"] == energyRowData.BUILDING_ID,
        "BUILDING_ADDRESS_PREFECTURE",
    ].iloc[0]
    site_address_city = basic_df.loc[
        basic_df["BUILDING_ID"] == energyRowData.BUILDING_ID, "BUILDING_ADDRESS_CITY"
    ].iloc[0]
    location_identifier_name = basic_df.loc[
        basic_df["BUILDING_ID"] == energyRowData.BUILDING_ID, "LOCATION_IDENTIFIER_NAME"
    ].iloc[0]
    zip_code = basic_df.loc[
        basic_df["BUILDING_ID"] == energyRowData.BUILDING_ID, "ZIP_CODE"
    ].iloc[0]
    municipality_code = basic_df.loc[
        basic_df["BUILDING_ID"] == energyRowData.BUILDING_ID, "MUNICIPALITY_CODE"
    ].iloc[0]
    supply_point_number = basic_df.loc[
        basic_df["BUILDING_ID"] == energyRowData.BUILDING_ID, "SUPPLY_POINT_NUMBER"
    ].iloc[0]

    # vis_common_entity.energy_name = energyRowData.ENERGY_NAME_JP

    # ヒアリングから設定
    vis_common_entity.company_name = basic_df["COMPANY_NAME"].iloc[0]

    vis_common_entity.company_address_prefecture = basic_df["ADDRESS_PREFECTURE"].iloc[
        0
    ]
    vis_common_entity.company_address_city = basic_df["ADDRESS_CITY"].iloc[0]

    vis_common_entity.ep_customer_number = ep_customer_number
    vis_common_entity.ep_office_code = ep_office_code
    vis_common_entity.location_identifier_code = energyRowData.LOCATION_IDENTIFIER_CODE
    vis_common_entity.location_identifier_name = location_identifier_name
    vis_common_entity.site_address_prefecture = site_address_prefecture
    vis_common_entity.site_address_city = site_address_city

    vis_common_entity.building_name = energyRowData.BUILDING_NAME

    vis_common_entity.supply_point_number = supply_point_number

    vis_common_entity.site_gross_floor_area = (
        float(energyRowData.SITE_GROSS_FLOOR_AREA)
        if pd.notna(energyRowData.SITE_GROSS_FLOOR_AREA)
        and str(energyRowData.SITE_GROSS_FLOOR_AREA).strip() != ""
        else None
    )
    vis_common_entity.energy_name_for_report = energyRowData.ENERGY_NAME_FOR_REPORT
    vis_common_entity.energy_name_for_coefficient_matching = (
        energyRowData.ENERGY_NAME_FOR_COEFFICIENT_MATCHING
    )

    vis_common_entity.energy_usage_monthly = float(updated_energy_quantity)
    vis_common_entity.energy_unit_original = (
        energyRowData.UNIT_ORIGIN
        if pd.notna(energyRowData.UNIT_ORIGIN)
        and str(energyRowData.UNIT_ORIGIN).strip() != ""
        else None
    )
    vis_common_entity.energy_unit_for_law = energyRowData.ENERGY_UNIT_FOR_LAW

    supplier_reg_no = energyRowData.SUPPLIER_REG_NO
    if supplier_reg_no in ("", None, np.nan):
        supplier_reg_no = "0"
    if updated_energy_code.startswith("03") and supplier_reg_no == "0":
        supplier_reg_no = "H0999"
    vis_common_entity.supplier_reg_no = supplier_reg_no
    vis_common_entity.supplier_name = (
        str(energyRowData.SUPPLIER_NAME) if bool(energyRowData.SUPPLIER_NAME) else None
    )
    vis_common_entity.supply_menu_no = (
        energyRowData.SUPPLY_MENU_NO
        if pd.notna(energyRowData.SUPPLY_MENU_NO) and energyRowData.SUPPLY_MENU_NO != ""
        else None
    )
    vis_common_entity.supply_menu = energyRowData.SUPPLY_MENU
    vis_common_entity.category = energyRowData.CATEGORY
    vis_common_entity.supply_conditions = energyRowData.SUPPLY_CONDITIONS

    is_noexist_energy: bool = updated_energy_code == "0000000000"
    # 熱量排出量・係数
    heat_converted_energy_usage = (
        float(energyRowData.HEAT_CONVERTED_ENERGY_USAGE_MONTHLY)
        if energyRowData.HEAT_CONVERTED_ENERGY_USAGE_MONTHLY not in [None, ""]
        else float(calorificEnergyConsumption)
    )
    heat_converted_energy_unit = (
        str(energyRowData.HEAT_CONVERTED_ENERGY_UNIT)
        if pd.notna(energyRowData.HEAT_CONVERTED_ENERGY_UNIT)
        and str(energyRowData.HEAT_CONVERTED_ENERGY_UNIT).strip() != ""
        else constants_values.HEAT_CONVERTED_ENERGY_UNIT
    )
    heat_conversion_coefficient = (
        float(energyRowData.HEAT_CONVERSION_COEFFICIENT)
        if energyRowData.HEAT_CONVERTED_ENERGY_USAGE_MONTHLY
        and (energyRowData.HEAT_CONVERSION_COEFFICIENT not in ["", None])
        else (
            float(officeUsedEnergyInfo["CONVERSION_COEF"])
            if officeUsedEnergyInfo is not None
            and officeUsedEnergyInfo["CONVERSION_COEF"]
            else None
        )
    )
    heat_conversion_coefficient_source = (
        "熱量換算係数データソース"
        if (energyRowData.HEAT_CONVERSION_COEFFICIENT not in ["", None])
        else f"EEGSマスタ{updated_fiscal_year}年度係数"
    )
    heat_conversion_coefficient_unit = (
        str(energyRowData.HEAT_CONVERSION_COEFFICIENT_UNIT)
        if (
            pd.notna(energyRowData.HEAT_CONVERSION_COEFFICIENT_UNIT)
            and str(energyRowData.HEAT_CONVERSION_COEFFICIENT_UNIT).strip() != ""
        )
        else (
            str(constants_values.HEAT_CONVERSION_COEFFICIENT_UNIT)
            + "/"
            + str(vis_common_entity.energy_unit_for_law)
            if vis_common_entity.energy_unit_for_law is not None
            else None
        )
    )

    # CO2調整後排出量・係数
    if energyRowData.SUPPLIER_REG_NO not in ("REENE", "SCOPE"):
        co2_adjusted_emissions_monthly = (
            float(energyRowData.CO2_ADJUSTED_EMISSIONS)
            if bool(energyRowData.CO2_ADJUSTED_EMISSIONS)
            else float(co2EmissionCoefficient)
        )
    else:
        co2_adjusted_emissions_monthly = 0

    co2_adjusted_emissions_unit = (
        str(energyRowData.CO2_ADJUSTED_EMISSIONS_UNIT)
        if pd.notna(energyRowData.CO2_ADJUSTED_EMISSIONS_UNIT)
        and str(energyRowData.CO2_ADJUSTED_EMISSIONS_UNIT).strip() != ""
        else constants_values.CO2_ADJUSTED_EMISSIONS_UNIT
    )

    if updated_energy_code == "0200010011":
        vis_common_entity.category = energyRowData.DAY_CATEGORY
        if (
            isinstance(electric_co2_emission_coef, str)
            and electric_co2_emission_coef.strip().lower() == "none"
        ):
            electric_co2_emission_coef = None
        if energyRowData.SUPPLIER_REG_NO == "REENE":
            co2_adjusted_emission_factor = 0
        else:
            co2_adjusted_emission_factor = float(electric_co2_emission_coef)
        co2_adjusted_emission_factor_source = (
            "CO2調整後排出係数データソース"
            if (energyRowData.CO2_ADJUSTED_EMISSION_FACTOR not in ["", None])
            else f"EEGSマスタ（電気事業者メニュー別）{updated_fiscal_year}年度係数"
        )
    else:
        if updated_energy_code.startswith("03"):
            co2_adjusted_emission_factor = heat_co2_emission_coef
        else:
            co2_adjusted_emission_factor = (
                float(energyRowData.CO2_ADJUSTED_EMISSION_FACTOR)
                if energyRowData.CO2_ADJUSTED_EMISSIONS
                and (energyRowData.CO2_ADJUSTED_EMISSION_FACTOR not in ["", None])
                else (
                    float(officeUsedEnergyInfo["ENERGY_CO2_EMISSION_COEF"])
                    if officeUsedEnergyInfo is not None
                    and officeUsedEnergyInfo["ENERGY_CO2_EMISSION_COEF"]
                    else 0
                )
            )
            co2_adjusted_emission_factor = (
                co2_adjusted_emission_factor
                if co2_adjusted_emission_factor
                else float(0.0)
            )
        if energyRowData.CO2_ADJUSTED_EMISSION_FACTOR not in ["", None]:
            co2_adjusted_emission_factor_source = "CO2調整後排出係数データソース"
        else:
            if updated_energy_code == constants_values.ENERGY_CODE_INDUSTRIAL_STEAM:
                co2_adjusted_emission_factor_source = f"EEGSマスタ（活動項目小分類（事業者））{updated_fiscal_year}年度係数"
            elif updated_energy_code.startswith("03"):
                co2_adjusted_emission_factor_source = (
                    f"EEGSマスタ（熱供給事業者メニュー別）{updated_fiscal_year}年度係数"
                )
            else:
                co2_adjusted_emission_factor_source = f"EEGSマスタ（活動項目小分類（事業者））{updated_fiscal_year}年度係数"
    if constants_values.ENERGY_CODE_CITY_GAS == updated_energy_code:
        co2_adjusted_emission_factor = (
            constants_values.CO2_EMISSION_CITY_GAS_COEFFICIENT
        )

    co2_adjusted_emission_factor_unit = (
        str(energyRowData.CO2_ADJUSTED_EMISSION_FACTOR_UNIT)
        if (
            pd.notna(energyRowData.CO2_ADJUSTED_EMISSION_FACTOR_UNIT)
            and str(energyRowData.CO2_ADJUSTED_EMISSION_FACTOR_UNIT).strip() != ""
        )
        else (
            str(constants_values.CO2_ADJUSTED_EMISSIONS_UNIT)
            + "/"
            + str(vis_common_entity.energy_unit_for_law)
            if vis_common_entity.energy_unit_for_law is not None
            else None
        )
    )

    vis_common_entity.heat_converted_energy_usage_monthly = heat_converted_energy_usage
    vis_common_entity.heat_converted_energy_unit = heat_converted_energy_unit
    vis_common_entity.heat_conversion_coefficient = heat_conversion_coefficient
    vis_common_entity.heat_conversion_coefficient_source = (
        heat_conversion_coefficient_source
    )
    vis_common_entity.heat_conversion_coefficient_unit = (
        heat_conversion_coefficient_unit
    )
    vis_common_entity.co2_base_emissions = (
        float(energyRowData.CO2_BASE_EMISSIONS)
        if pd.notna(energyRowData.CO2_BASE_EMISSIONS)
        and str(energyRowData.CO2_BASE_EMISSIONS).strip() != ""
        else None
    )
    vis_common_entity.co2_base_emissions_unit = (
        str(energyRowData.CO2_BASE_EMISSIONS_UNIT)
        if pd.notna(energyRowData.CO2_BASE_EMISSIONS_UNIT)
        and str(energyRowData.CO2_BASE_EMISSIONS_UNIT).strip() != ""
        else None
    )
    vis_common_entity.co2_base_emission_factor = (
        float(energyRowData.CO2_BASE_EMISSION_FACTOR)
        if pd.notna(energyRowData.CO2_BASE_EMISSION_FACTOR)
        and str(energyRowData.CO2_BASE_EMISSION_FACTOR).strip() != ""
        else None
    )
    vis_common_entity.co2_base_emission_factor_unit = (
        str(energyRowData.CO2_BASE_EMISSION_FACTOR_UNIT)
        if pd.notna(energyRowData.CO2_BASE_EMISSION_FACTOR_UNIT)
        and str(energyRowData.CO2_BASE_EMISSION_FACTOR_UNIT).strip() != ""
        else None
    )

    vis_common_entity.co2_adjusted_emissions_monthly = co2_adjusted_emissions_monthly
    vis_common_entity.co2_adjusted_emissions_unit = co2_adjusted_emissions_unit
    vis_common_entity.co2_adjusted_emission_factor = co2_adjusted_emission_factor
    vis_common_entity.co2_adjusted_emission_factor_source = (
        co2_adjusted_emission_factor_source
    )
    vis_common_entity.co2_adjusted_emission_factor_unit = (
        co2_adjusted_emission_factor_unit
    )

    vis_common_entity.zip_code = zip_code
    municipality_code = (
        int(municipality_code)
        if not basic_df.empty and bool(municipality_code)
        else None
    )
    vis_common_entity.municipality_code = municipality_code

    if supplier_reg_no == "SCOPE" or is_noexist_energy:
        return
    tMonthlyBuildingEnergyAggregation = TMonthlyBuildingEnergyAggregation(
        **common_filters, target_year_month=year_month, registration_seq=0
    )
    if supplier_reg_no:
        tMonthlyBuildingEnergyAggregation.supplier_reg_no = supplier_reg_no
    else:
        tMonthlyBuildingEnergyAggregation.supplier_reg_no = "0"
    tMonthlyBuildingEnergyAggregation.supplier_name = (
        str(energyRowData.SUPPLIER_NAME) if bool(energyRowData.SUPPLIER_NAME) else None
    )
    tMonthlyBuildingEnergyAggregation.supply_menu = (
        str(energyRowData.SUPPLY_MENU) if bool(energyRowData.SUPPLY_MENU) else None
    )

    tMonthlyBuildingEnergyAggregation.entry_draft_flag = int(
        basic_df["ENTRY_DRAFT_FLAG"].iloc[0]
    )  # 登録下書区分
    tMonthlyBuildingEnergyAggregation.building_name = (
        energyRowData.BUILDING_NAME
    )  # 拠点名
    tMonthlyBuildingEnergyAggregation.energy_category_name = (
        energyRowData.ENERGY_NAME_JP
    )  # エネルギー名称
    tMonthlyBuildingEnergyAggregation.fiscal_year = updated_fiscal_year  # 対象年度
    tMonthlyBuildingEnergyAggregation.temperature_corp = nan_to_none(
        energyRowData.TEMPERATURE_CORP
    )  # 本社温度
    tMonthlyBuildingEnergyAggregation.temperature_building = (
        updated_temp_building  # 温度
    )
    tMonthlyBuildingEnergyAggregation.energy_quantity = float(
        updated_energy_quantity
    )  # 年度エネルギー使用量
    tMonthlyBuildingEnergyAggregation.energy_quantity_for_report = float(
        updated_energy_for_report
    )  # 年度エネルギー使用量(レポート)
    tMonthlyBuildingEnergyAggregation.energy_quantity_for_law = float(
        updated_energy_for_law
    )  # 年度エネルギー使用量(省エネ)
    tMonthlyBuildingEnergyAggregation.energy_unit_original = (
        energyRowData.UNIT_ORIGIN
    )  # 年度エネルギー単位
    tMonthlyBuildingEnergyAggregation.energy_unit_for_report = (
        energyRowData.ENERGY_UNIT_FOR_REPORT
    )  # 年度エネルギー単位(レポート)
    tMonthlyBuildingEnergyAggregation.energy_unit_for_law = (
        energyRowData.ENERGY_UNIT_FOR_LAW
    )  # 年度エネルギー単位(省エネ)
    site_gross_floor_area = energyRowData.SITE_GROSS_FLOOR_AREA
    tMonthlyBuildingEnergyAggregation.energy_usage_area_unit = (
        float(round(updated_energy_for_law / float(site_gross_floor_area), 4))
        if site_gross_floor_area and site_gross_floor_area > 0
        else (
            None
            if buildingArea is None or buildingArea <= 0
            else float(round(updated_energy_for_law / float(buildingArea), 4))
        )
    )  # エネルギー使用量原単位
    energy_unit_for_law = (
        None if officeUsedEnergyInfo is None else officeUsedEnergyInfo["UNIT"],
    )  # エネルギー単位
    tMonthlyBuildingEnergyAggregation.energy_name_for_coefficient_matching = (
        energyRowData.ENERGY_NAME_FOR_COEFFICIENT_MATCHING
    )  # 省エネ法名称
    if updated_energy_code == "0200010011":
        tMonthlyBuildingEnergyAggregation.energy_name_for_coefficient_matching = (
            "電気事業者からの買電（化石電気）"
        )

    # 熱量換算・係数関連設定
    tMonthlyBuildingEnergyAggregation.heat_converted_energy_usage = (
        heat_converted_energy_usage
        if heat_converted_energy_usage
        else (
            float(tEnergyStorageCommonInfo.heat_converted_energy_usage_monthly)
            if tEnergyStorageCommonInfo
            else 0.0
        )
    )  # 熱量換算使用量
    tMonthlyBuildingEnergyAggregation.heat_converted_energy_usage_area_unit = (
        round(float(heat_converted_energy_usage) / float(site_gross_floor_area), 4)
        if site_gross_floor_area and site_gross_floor_area > 0
        else (
            None
            if buildingArea is None or buildingArea <= 0
            else round(float(heat_converted_energy_usage) / float(buildingArea), 4)
        )
    )  # 熱量換算面積単位使用量
    tMonthlyBuildingEnergyAggregation.heat_conversion_coefficient_source = (
        heat_conversion_coefficient_source
    )
    tMonthlyBuildingEnergyAggregation.heat_conversion_coefficient = (
        heat_conversion_coefficient
    )
    tMonthlyBuildingEnergyAggregation.heat_converted_energy_unit = (
        heat_converted_energy_unit
    )
    tMonthlyBuildingEnergyAggregation.heat_converted_energy_usage_zeb = float(
        calorificEnergyConsumption_2023
    )

    # CO2調整後排出量・係数関連設定
    tMonthlyBuildingEnergyAggregation.co2_adjusted_emissions = (
        co2_adjusted_emissions_monthly
        if co2_adjusted_emissions_monthly
        else (
            float(tEnergyStorageCommonInfo.co2_adjusted_emissions_monthly)
            if tEnergyStorageCommonInfo
            else 0.0
        )
    )  # CO2調整後排出量
    tMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_area_unit = (
        0
        if energyRowData.SUPPLIER_REG_NO == "REENE"
        else (
            None
            if co2_adjusted_emissions_monthly is None
            else (
                (float(co2_adjusted_emissions_monthly) / float(site_gross_floor_area))
                if site_gross_floor_area and site_gross_floor_area > 0
                else (
                    None
                    if buildingArea is None or buildingArea <= 0
                    else (float(co2_adjusted_emissions_monthly) / float(buildingArea))
                )
            )
        )
    )  # CO2排出面積単位使用量
    tMonthlyBuildingEnergyAggregation.co2_adjusted_emission_factor = (
        co2_adjusted_emission_factor
    )
    tMonthlyBuildingEnergyAggregation.co2_adjusted_emission_factor_source = (
        co2_adjusted_emission_factor_source
    )
    tMonthlyBuildingEnergyAggregation.co2_adjusted_emission_factor_unit = (
        co2_adjusted_emission_factor_unit
    )
    tMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_zeb = float(
        co2EmissionCoefficient_2013
    )
    tMonthlyBuildingEnergyAggregation.energy_unit_for_law = energy_unit_for_law
    tMonthlyBuildingEnergyAggregation.gross_floor_area = (
        float(energyRowData.SITE_GROSS_FLOOR_AREA)
        if pd.notna(energyRowData.SITE_GROSS_FLOOR_AREA)
        and str(energyRowData.SITE_GROSS_FLOOR_AREA).strip() != ""
        else None
    )
    if isinstance(heat_converted_energy_usage, tuple):
        tMonthlyBuildingEnergyAggregation.heat_converted_energy_usage = (
            heat_converted_energy_usage[0]
        )
    if isinstance(co2_adjusted_emissions_monthly, tuple):
        tMonthlyBuildingEnergyAggregation.co2_adjusted_emissions = (
            0
            if energyRowData.SUPPLIER_REG_NO == "REENE"
            else co2_adjusted_emissions_monthly[0]
        )
    if isinstance(energy_unit_for_law, tuple):
        tMonthlyBuildingEnergyAggregation.energy_unit_for_law = energy_unit_for_law[0]

    tMonthlyBuildingEnergyAggregation.co2_base_emissions = (
        float(energyRowData.CO2_BASE_EMISSIONS)
        if pd.notna(energyRowData.CO2_BASE_EMISSIONS)
        and str(energyRowData.CO2_BASE_EMISSIONS).strip() != ""
        else (
            float(tEnergyStorageCommonInfo.co2_base_emissions)
            if tEnergyStorageCommonInfo
            and tEnergyStorageCommonInfo.co2_base_emissions is not None
            else None
        )
    )
    # tMonthlyBuildingEnergyAggregation.co2_base_emissions_unit = (
    #     str(energyRowData.CO2_BASE_EMISSIONS_UNIT)
    #     if pd.notna(energyRowData.CO2_BASE_EMISSIONS_UNIT) and str(energyRowData.CO2_BASE_EMISSIONS_UNIT).strip() != ""
    #     else None
    # )
    tMonthlyBuildingEnergyAggregation.co2_base_emissions_unit = "ｔ-CO2"
    tMonthlyBuildingEnergyAggregation.co2_base_emission_factor = (
        float(energyRowData.CO2_BASE_EMISSION_FACTOR)
        if pd.notna(energyRowData.CO2_BASE_EMISSION_FACTOR)
        and str(energyRowData.CO2_BASE_EMISSION_FACTOR).strip() != ""
        else None
    )
    tMonthlyBuildingEnergyAggregation.co2_base_emission_factor_unit = (
        str(energyRowData.CO2_BASE_EMISSION_FACTOR_UNIT)
        if pd.notna(energyRowData.CO2_BASE_EMISSION_FACTOR_UNIT)
        and str(energyRowData.CO2_BASE_EMISSION_FACTOR_UNIT).strip() != ""
        else None
    )
    # tMonthlyBuildingEnergyAggregation.heat_converted_energy_unit = str(energyRowData.HEAT_CONVERTED_ENERGY_UNIT) \
    #     if pd.notna(energyRowData.HEAT_CONVERTED_ENERGY_UNIT) else None
    tMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_avg = (
        float(co2EmissionCoefficient_avg) if bool(co2EmissionCoefficient_avg) else 0.0
    )
    tMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_unit = (
        co2_adjusted_emissions_unit
    )
    tMonthlyBuildingEnergyAggregation.heat_conversion_coefficient_unit = (
        heat_conversion_coefficient_unit
    )
    tMonthlyBuildingEnergyAggregation.excel_row = energyRowData.EXCEL_ROW
    building_month_list.append(tMonthlyBuildingEnergyAggregation)
    excel_row_list.append(energyRowData.EXCEL_ROW)
    return tMonthlyBuildingEnergyAggregation


def get_building_annual_entity(session, basic_df, row):

    registration_seq = int(basic_df["REGISTRATION_SEQ"].iloc[0])
    # 主キー項目をまとめて変数に
    pk_values = {
        "corporate_number": basic_df["CORPORATE_NUMBER"].iloc[0],
        "agreement_category": basic_df["AGREEMENT_CATEGORY"].iloc[0],
        "org_id": basic_df["ORG_ID"].iloc[0],
        "building_id": row.BUILDING_ID,
        "energy_code": row.ENERGY_CODE,
        "target_year": str(row.FISCAL_YEAR),
        "fiscal_year": str(row.FISCAL_YEAR),
        "registration_seq": registration_seq,
        "supplier_reg_no": row.SUPPLIER_REG_NO,
    }

    tAnnualBuildingEnergyAggregation: TAnnualBuildingEnergyAggregation = (
        session.query(TAnnualBuildingEnergyAggregation).filter_by(**pk_values).first()
    )
    if not tAnnualBuildingEnergyAggregation:
        tAnnualBuildingEnergyAggregation = TAnnualBuildingEnergyAggregation()

        tAnnualBuildingEnergyAggregation.corporate_number = basic_df[
            "CORPORATE_NUMBER"
        ].iloc[
            0
        ]  # 法人番号
        tAnnualBuildingEnergyAggregation.agreement_category = basic_df[
            "AGREEMENT_CATEGORY"
        ].iloc[0]
        tAnnualBuildingEnergyAggregation.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
        tAnnualBuildingEnergyAggregation.building_id = row.BUILDING_ID  # 拠点ID
        tAnnualBuildingEnergyAggregation.energy_code = (
            row.ENERGY_CODE
        )  # エネルギーコード
        tAnnualBuildingEnergyAggregation.target_year = str(row.FISCAL_YEAR)
        tAnnualBuildingEnergyAggregation.fiscal_year = str(row.FISCAL_YEAR)
        tAnnualBuildingEnergyAggregation.registration_seq = registration_seq
        tAnnualBuildingEnergyAggregation.supplier_reg_no = row.SUPPLIER_REG_NO

        tAnnualBuildingEnergyAggregation.created_by = basic_df["CREATED_BY"].iloc[0]
        session.add(tAnnualBuildingEnergyAggregation)
    else:
        tAnnualBuildingEnergyAggregation.updated_by = basic_df["CREATED_BY"].iloc[0]

    # tAnnualBuildingEnergyAggregation.supplier_name = row.SUPPLIER_NAME
    # tAnnualBuildingEnergyAggregation.supply_conditions = row.SUPPLY_CONDITIONS if row.SUPPLY_CONDITIONS else "昼"
    tAnnualBuildingEnergyAggregation.building_name = row.BUILDING_NAME  # 拠点名
    tAnnualBuildingEnergyAggregation.energy_category_name = (
        row.ENERGY_CATEGORY_NAME
    )  # エネルギー名称
    tAnnualBuildingEnergyAggregation.energy_quantity = (
        row.ENERGY_QUANTITY
    )  # 年度エネルギー使用量
    tAnnualBuildingEnergyAggregation.energy_quantity_for_report = (
        row.ENERGY_QUANTITY_FOR_REPORT
    )  # 年度エネルギー使用量(レポート)
    tAnnualBuildingEnergyAggregation.energy_quantity_for_law = (
        row.ENERGY_QUANTITY_FOR_LAW
    )  # 年度エネルギー使用量(省エネ)
    tAnnualBuildingEnergyAggregation.energy_unit_original = (
        row.ENERGY_UNIT_ORIGINAL
    )  # 年度エネルギー単位
    tAnnualBuildingEnergyAggregation.energy_unit_for_report = (
        row.ENERGY_UNIT_FOR_REPORT
    )  # 年度エネルギー単位(レポート)
    tAnnualBuildingEnergyAggregation.energy_unit_for_law = (
        row.ENERGY_UNIT_FOR_LAW
    )  # 年度エネルギー単位(省エネ)
    tAnnualBuildingEnergyAggregation.heat_converted_energy_usage = round(
        row.HEAT_CONVERTED_ENERGY_USAGE, 4
    )  # 熱量換算エネルギー使用量
    tAnnualBuildingEnergyAggregation.co2_adjusted_emissions = (
        row.CO2_ADJUSTED_EMISSIONS
    )  # co2排出量
    tAnnualBuildingEnergyAggregation.energy_name_for_coefficient_matching = (
        row.ENERGY_NAME_FOR_COEFFICIENT_MATCHING
    )  # 省エネ法名称
    # tAnnualBuildingEnergyAggregation.heat_conversion_coefficient = row.HEAT_CONVERSION_COEFFICIENT
    # tAnnualBuildingEnergyAggregation.co2_adjusted_emission_factor = row.CO2_ADJUSTED_EMISSION_FACTOR
    if row.ENERGY_CODE == "0200010011":
        tAnnualBuildingEnergyAggregation.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_ELECTRIC
        )
    else:
        tAnnualBuildingEnergyAggregation.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC
        )
    tAnnualBuildingEnergyAggregation.heat_conversion_coefficient_source = (
        constants_values.HEAT_CONVERSION_COEFFICIENT_SOURCE
    )
    tAnnualBuildingEnergyAggregation.credit_certificate_purchase_energy_amount = (
        row.CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT
    )
    tAnnualBuildingEnergyAggregation.credit_certificate_purchase_tco2_amount = (
        row.CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT
    )

    return tAnnualBuildingEnergyAggregation


# @log_time
def get_company_month_entity(session, basic_df, row):
    registration_seq = int(basic_df["REGISTRATION_SEQ"].iloc[0])
    tMonthlyCorporateEnergyAggregation = (
        session.query(TMonthlyCorporateEnergyAggregation)
        .filter_by(
            corporate_number=basic_df["CORPORATE_NUMBER"].iloc[0],
            agreement_category=basic_df["AGREEMENT_CATEGORY"].iloc[0],
            org_id=basic_df["ORG_ID"].iloc[0],
            energy_code=row.ENERGY_CODE,
            target_year_month=row.TARGET_YEAR_MONTH,
            registration_seq=registration_seq,
        )
        .first()
    )
    if not tMonthlyCorporateEnergyAggregation:
        tMonthlyCorporateEnergyAggregation = TMonthlyCorporateEnergyAggregation()

        tMonthlyCorporateEnergyAggregation.corporate_number = basic_df[
            "CORPORATE_NUMBER"
        ].iloc[
            0
        ]  # 法人番号
        tMonthlyCorporateEnergyAggregation.agreement_category = basic_df[
            "AGREEMENT_CATEGORY"
        ].iloc[0]
        tMonthlyCorporateEnergyAggregation.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
        # tMonthlyCorporateEnergyAggregation.entry_draft_flag = basic_df['ENTRY_DRAFT_FLAG'].iloc[0]             #登録下書区分
        tMonthlyCorporateEnergyAggregation.energy_code = (
            row.ENERGY_CODE
        )  # エネルギーコード
        tMonthlyCorporateEnergyAggregation.target_year_month = (
            row.TARGET_YEAR_MONTH
        )  # 対象年+対象月
        tMonthlyCorporateEnergyAggregation.registration_seq = (
            registration_seq  # 登録回数
        )
        tMonthlyCorporateEnergyAggregation.created_by = basic_df["CREATED_BY"].iloc[0]
        session.add(tMonthlyCorporateEnergyAggregation)
    else:
        tMonthlyCorporateEnergyAggregation.updated_by = basic_df["CREATED_BY"].iloc[0]

    tMonthlyCorporateEnergyAggregation.energy_category_name = (
        row.ENERGY_CATEGORY_NAME
    )  # エネルギー名称
    tMonthlyCorporateEnergyAggregation.fiscal_year = str(row.FISCAL_YEAR)
    tMonthlyCorporateEnergyAggregation.energy_usage_area_unit = round(
        row.ENERGY_USAGE_AREA_UNIT, 4
    )  # 年度エネルギー使用量原単位
    tMonthlyCorporateEnergyAggregation.energy_quantity = None  # 年度エネルギー使用量
    tMonthlyCorporateEnergyAggregation.energy_quantity_for_report = (
        row.ENERGY_QUANTITY_FOR_REPORT
    )  # 年度エネルギー使用量(レポート)
    tMonthlyCorporateEnergyAggregation.energy_quantity_for_law = (
        row.ENERGY_QUANTITY_FOR_LAW
    )  # 年度エネルギー使用量(省エネ)
    # tMonthlyCorporateEnergyAggregation.energy_unit_original = row.ENERGY_UNIT_ORIGINAL                #年度エネルギー単位
    tMonthlyCorporateEnergyAggregation.energy_unit_for_report = (
        row.ENERGY_UNIT_FOR_REPORT
    )  # 年度エネルギー単位(レポート)
    tMonthlyCorporateEnergyAggregation.energy_unit_for_law = (
        row.ENERGY_UNIT_FOR_LAW
    )  # 年度エネルギー単位(省エネ)
    tMonthlyCorporateEnergyAggregation.heat_converted_energy_usage = round(
        row.HEAT_CONVERTED_ENERGY_USAGE, 4
    )  # 熱量換算エネルギー使用量
    # tMonthlyCorporateEnergyAggregation.heat_converted_energy_usage_last_year = round(row.HEAT_CONVERTED_ENERGY_USAGE_LAST_YEAR, 4) #熱量換算エネルギー使用量
    tMonthlyCorporateEnergyAggregation.heat_converted_energy_usage_area_unit = round(
        row.HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT, 4
    )  # 熱量換算面積単位使用量
    tMonthlyCorporateEnergyAggregation.co2_adjusted_emissions = (
        row.CO2_ADJUSTED_EMISSIONS
    )  # co2排出量
    # tMonthlyCorporateEnergyAggregation.co2_adjusted_emissions_last_year = round(row.CO2_ADJUSTED_EMISSIONS_LAST_YEAR, 4)           #前年度co2排出量
    tMonthlyCorporateEnergyAggregation.co2_adjusted_emissions_area_unit = round(
        row.CO2_ADJUSTED_EMISSIONS_AREA_UNIT, 4
    )  # CO2排出面積単位使用量
    tMonthlyCorporateEnergyAggregation.heat_conversion_coefficient = (
        row.HEAT_CONVERSION_COEFFICIENT
    )
    tMonthlyCorporateEnergyAggregation.co2_adjusted_emission_factor = (
        row.CO2_ADJUSTED_EMISSION_FACTOR
    )
    if row.ENERGY_CODE == "0200010011":
        tMonthlyCorporateEnergyAggregation.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_ELECTRIC
        )
    else:
        tMonthlyCorporateEnergyAggregation.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC
        )
    tMonthlyCorporateEnergyAggregation.heat_conversion_coefficient_source = (
        constants_values.HEAT_CONVERSION_COEFFICIENT_SOURCE
    )
    tMonthlyCorporateEnergyAggregation.energy_name_for_coefficient_matching = (
        row.ENERGY_NAME_FOR_COEFFICIENT_MATCHING
    )  # 省エネ法名称
    tMonthlyCorporateEnergyAggregation.credit_certificate_purchase_energy_amount = (
        row.CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT
    )
    tMonthlyCorporateEnergyAggregation.credit_certificate_purchase_tco2_amount = (
        row.CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT
    )

    return tMonthlyCorporateEnergyAggregation


# @log_time
def get_company_annual_entity(session, basic_df, row):
    registration_seq = int(basic_df["REGISTRATION_SEQ"].iloc[0])
    pk_values = {
        "corporate_number": basic_df["CORPORATE_NUMBER"].iloc[0],
        "agreement_category": basic_df["AGREEMENT_CATEGORY"].iloc[0],
        "org_id": basic_df["ORG_ID"].iloc[0],
        "energy_code": row.ENERGY_CODE,
        "target_year": str(row.FISCAL_YEAR),
        "fiscal_year": str(row.FISCAL_YEAR),
        "registration_seq": registration_seq,
    }
    tAnnualCorporateEnergyAggregation = (
        session.query(TAnnualCorporateEnergyAggregation).filter_by(**pk_values).first()
    )
    if not tAnnualCorporateEnergyAggregation:
        tAnnualCorporateEnergyAggregation = TAnnualCorporateEnergyAggregation()

        tAnnualCorporateEnergyAggregation.corporate_number = basic_df[
            "CORPORATE_NUMBER"
        ].iloc[
            0
        ]  # 法人番号
        tAnnualCorporateEnergyAggregation.agreement_category = basic_df[
            "AGREEMENT_CATEGORY"
        ].iloc[0]
        tAnnualCorporateEnergyAggregation.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
        tAnnualCorporateEnergyAggregation.energy_code = (
            row.ENERGY_CODE
        )  # エネルギーコード
        tAnnualCorporateEnergyAggregation.target_year = str(
            row.FISCAL_YEAR
        )  # 対象年+対象月
        tAnnualCorporateEnergyAggregation.fiscal_year = str(
            row.FISCAL_YEAR
        )  # 対象年+対象月
        tAnnualCorporateEnergyAggregation.registration_seq = (
            registration_seq  # 登録回数
        )

        tAnnualCorporateEnergyAggregation.created_by = basic_df["CREATED_BY"].iloc[0]
        session.add(tAnnualCorporateEnergyAggregation)
    else:
        tAnnualCorporateEnergyAggregation.updated_by = basic_df["CREATED_BY"].iloc[0]

    # tAnnualCorporateEnergyAggregation.entry_draft_flag = basic_df['ENTRY_DRAFT_FLAG'].iloc[0]             #登録下書区分
    tAnnualCorporateEnergyAggregation.energy_category_name = (
        row.ENERGY_CATEGORY_NAME
    )  # エネルギー名称
    tAnnualCorporateEnergyAggregation.energy_quantity = (
        row.ENERGY_QUANTITY
    )  # 年度エネルギー使用量
    tAnnualCorporateEnergyAggregation.energy_quantity_for_report = (
        row.ENERGY_QUANTITY_FOR_REPORT
    )  # 年度エネルギー使用量(レポート)
    tAnnualCorporateEnergyAggregation.energy_quantity_for_law = (
        row.ENERGY_QUANTITY_FOR_LAW
    )  # 年度エネルギー使用量(省エネ)
    # tAnnualCorporateEnergyAggregation.energy_unit_original = row.ENERGY_UNIT_ORIGINAL        #年度エネルギー単位
    tAnnualCorporateEnergyAggregation.energy_unit_for_report = (
        row.ENERGY_UNIT_FOR_REPORT
    )  # 年度エネルギー単位(レポート)
    tAnnualCorporateEnergyAggregation.energy_unit_for_law = (
        row.ENERGY_UNIT_FOR_LAW
    )  # 年度エネルギー単位(省エネ)
    tAnnualCorporateEnergyAggregation.heat_converted_energy_usage = round(
        row.HEAT_CONVERTED_ENERGY_USAGE, 4
    )  # 熱量換算エネルギー使用量
    tAnnualCorporateEnergyAggregation.co2_adjusted_emissions = (
        row.CO2_ADJUSTED_EMISSIONS
    )  # co2排出量
    # tAnnualCorporateEnergyAggregation.heat_conversion_coefficient = row.HEAT_CONVERSION_COEFFICIENT
    # tAnnualCorporateEnergyAggregation.co2_adjusted_emission_factor = row.CO2_ADJUSTED_EMISSION_FACTOR
    tAnnualCorporateEnergyAggregation.energy_name_for_coefficient_matching = (
        row.ENERGY_NAME_FOR_COEFFICIENT_MATCHING
    )  # 省エネ法名称
    if row.ENERGY_CODE == "0200010011":
        tAnnualCorporateEnergyAggregation.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_ELECTRIC
        )
    else:
        tAnnualCorporateEnergyAggregation.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC
        )
    tAnnualCorporateEnergyAggregation.heat_conversion_coefficient_source = (
        constants_values.HEAT_CONVERSION_COEFFICIENT_SOURCE
    )
    tAnnualCorporateEnergyAggregation.credit_certificate_purchase_energy_amount = (
        row.CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT
    )
    tAnnualCorporateEnergyAggregation.credit_certificate_purchase_tco2_amount = (
        row.CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT
    )

    return tAnnualCorporateEnergyAggregation


def build_energy_code_dict(ccmst: pd.DataFrame) -> dict:
    # ENERGY_CODE を作成
    ccmst["ENERGY_CODE"] = (
        ccmst["MAJOR_CATEGORY_ID"].astype(str)
        + ccmst["MIDDLE_CATEGORY_ID"].astype(str)
        + ccmst["MINOR_CATEGORY_ID"].astype(str)
    )

    # 年度一覧を取得
    years = sorted(ccmst["REPORT_YEAR"].unique())

    # 目的の dict を構築
    energy_coef_dict = {
        year: {
            row["ENERGY_CODE"]: row.to_dict()
            for _, row in ccmst[ccmst["REPORT_YEAR"] == year].iterrows()
        }
        for year in years
    }
    return energy_coef_dict


def build_energy_code_dict_zeb(ccmst: pd.DataFrame, emission_coef_year: str) -> dict:
    years = sorted(ccmst["REPORT_YEAR"].unique())
    if emission_coef_year not in years:
        # 過去の年度（最小より前）
        if emission_coef_year < years[0]:
            emission_coef_year = years[0]
        # 未来の年度（最大より後）
        elif emission_coef_year > years[-1]:
            emission_coef_year = years[-1]
        # 途中（間にあるけど存在しない）
        else:
            # 最も近い年度を選ぶ
            emission_coef_year = min(years, key=lambda y: abs(y - emission_coef_year))

    ccmst_sub = ccmst[ccmst["REPORT_YEAR"] == emission_coef_year]
    ccmst_sub["ENERGY_CODE"] = (
        ccmst_sub["MAJOR_CATEGORY_ID"].astype(str)
        + ccmst_sub["MIDDLE_CATEGORY_ID"].astype(str)
        + ccmst_sub["MINOR_CATEGORY_ID"].astype(str)
    )
    return ccmst_sub.set_index("ENERGY_CODE").to_dict(orient="index")


def preprocess_energy_info(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df[df["VALUE"].notna()]
    df["UNIT_ORIGIN"].replace("", pd.NA, inplace=True)
    df.dropna(subset=["UNIT_ORIGIN"], inplace=True)
    df["ENERGY_CODE"] = df["ENERGY_CODE"].astype(str)
    df["NEW_YEAR_MONTH"] = df["TARGET_DATE"].dt.strftime("%Y-%m")
    return df


def group_master_data(ccmst: pd.DataFrame, nfcmst: pd.DataFrame):
    ccmst_map = {
        (
            str(row.REPORT_YEAR),
            str(row.MAJOR_CATEGORY_ID),
            str(row.MIDDLE_CATEGORY_ID),
            str(row.MINOR_CATEGORY_ID),
        ): row
        for _, row in ccmst.iterrows()
    }
    nfcmst_map = {str(row.FACILITY_ID): row for _, row in nfcmst.iterrows()}
    return ccmst_map, nfcmst_map


def get_vis_flg(basic_df: pd.DataFrame, df_energyInfo: pd.DataFrame):
    vis_flg: bool = False
    reg_seq = basic_df.at[0, "REGISTRATION_SEQ"]
    heat_coef = df_energyInfo.at[0, "HEAT_CONVERSION_COEFFICIENT"]

    # 両方とも NaN でなければ flg を True に
    if pd.notna(reg_seq) and reg_seq == 0 and pd.notna(heat_coef):
        vis_flg = True

    return vis_flg


# @log_time
def get_building_month_df(
    session,
    basic_df,
    df_buildingInfo,
    df_energyInfo,
    ccmst,
    ecmst,
    calmst,
    hsmst,
    df_wdimst,
    nfcmst,
    gasmst,
    target_years,
):
    """
    建物月別集計データDF取得
    params:
    return:
    """
    start_time = time.time()

    # 新規登録対象月別建物エネルギー情報格納用list
    vis_common_list: list[TEnergyStorageCommonForVisualization] = []
    building_month_list: list[TMonthlyBuildingEnergyAggregation] = []
    excel_row_list: list[int] = []

    monthlyBuildingEnergyAggregationList = []
    # ENERGY_NAME_JPが「電気」の場合、ENERGY_CODEを設定
    # df_energyInfo["ENERGY_CODE"] = df_energyInfo["ENERGY_NAME_JP"].map(lambda x: constants_colums.enery_code_mapping.get(x, None))
    df_energyInfo = df_energyInfo.assign(ENERGY_SCOPE=None)

    # 本社気温名設定
    df_wdimst = df_wdimst.rename(
        columns={
            "TARGET_YEAR": "YEAR",
            "TARGET_MONTH": "MONTH",
            basic_df["ADDRESS_PREFECTURE"].iloc[0]: "TEMPERATURE_CORP",
        }
    )

    # タイプ変換
    df_energyInfo["YEAR"] = df_energyInfo["YEAR"].astype(int)
    df_energyInfo["MONTH"] = df_energyInfo["MONTH"].astype(int)
    df_wdimst["YEAR"] = df_wdimst["YEAR"].astype(int)
    df_wdimst["MONTH"] = df_wdimst["MONTH"].astype(int)
    # df_wdimst['TEMPERATURE_CORP'] = df_wdimst['TEMPERATURE_CORP'].fillna(0).astype(float)

    # 気温マージ # left join：df_energyInfoの行を維持
    df_energyInfo = df_energyInfo.merge(
        df_wdimst[["YEAR", "MONTH", "TEMPERATURE_CORP"]],
        on=["YEAR", "MONTH"],
        how="left",
    )

    # エネルギー最小年月取得
    # df_energyInfo["NEW_YEAR_MONTH"] = str(df_energyInfo['YEAR']) + str(df_energyInfo['MONTH'])
    min_value = df_energyInfo["YEAR_MONTH"].min()
    min_month = min_value[4:]

    # 空文字をNaNに変換
    df_energyInfo.loc[:, "UNIT_ORIGIN"] = df_energyInfo["UNIT_ORIGIN"].replace(
        "", pd.NA
    )

    # ===== index 正規化 =====
    df_energyInfo = df_energyInfo.reset_index(drop=True)

    _supplier_name_lc_series = df_energyInfo["SUPPLIER_NAME"].astype(object).str.lower()

    # --- UNIT_ORIGIN補完用 既存月別集計データを一括取得 ---
    existing_monthly_energy_list = (
        session.query(TMonthlyBuildingEnergyAggregation)
        .filter(
            TMonthlyBuildingEnergyAggregation.corporate_number
            == basic_df["CORPORATE_NUMBER"].iloc[0],
            TMonthlyBuildingEnergyAggregation.agreement_category
            == basic_df["AGREEMENT_CATEGORY"].iloc[0],
            TMonthlyBuildingEnergyAggregation.org_id == basic_df["ORG_ID"].iloc[0],
            TMonthlyBuildingEnergyAggregation.registration_seq == 0,
        )
        .all()
    )
    _existing_monthly_energy_bucket = defaultdict(list)
    for row in existing_monthly_energy_list:
        key = (
            row.corporate_number,
            row.agreement_category,
            row.org_id,
            row.building_id,
            row.energy_code,
            row.target_year_month,
            row.registration_seq,
        )
        # DB 返却順のまま append → .first() と一致
        _existing_monthly_energy_bucket[key].append(row)

    # --- 可視化用エネルギー既存データ一括取得 ---
    vis_energy_list = (
        session.query(TEnergyStorageCommonForVisualization)
        .filter(
            TEnergyStorageCommonForVisualization.corporate_number
            == basic_df["CORPORATE_NUMBER"].iloc[0],
            TEnergyStorageCommonForVisualization.agreement_category
            == basic_df["AGREEMENT_CATEGORY"].iloc[0],
            TEnergyStorageCommonForVisualization.org_id == basic_df["ORG_ID"].iloc[0],
        )
        .all()
    )
    _vis_energy_bucket = defaultdict(list)
    for row in vis_energy_list:
        key = (
            row.building_id,
            row.energy_code,
            row.year_month,
            row.input_supplier_name,
        )
        # DB 返却順のまま append → .first() と一致
        _vis_energy_bucket[key].append(row)

    _supplier_name_lc_series = df_energyInfo["SUPPLIER_NAME"].astype(object).str.lower()

    for energyRowData in df_energyInfo.itertuples():
        # ------------------------------------------------------------------
        # 【修正前SQL（意味論保持のため残す）】
        # tMonthlyBuildingEnergyInfo = (
        #     session.query(TMonthlyBuildingEnergyAggregation)
        #     .filter(
        #         TMonthlyBuildingEnergyAggregation.corporate_number == basic_df['CORPORATE_NUMBER'].iloc[0],
        #         TMonthlyBuildingEnergyAggregation.agreement_category == basic_df['AGREEMENT_CATEGORY'].iloc[0],
        #         TMonthlyBuildingEnergyAggregation.org_id == basic_df["ORG_ID"].iloc[0],
        #         TMonthlyBuildingEnergyAggregation.registration_seq == 0,
        #         TMonthlyBuildingEnergyAggregation.building_id == energyRowData.BUILDING_ID,
        #         TMonthlyBuildingEnergyAggregation.energy_code == energyRowData.ENERGY_CODE,
        #         TMonthlyBuildingEnergyAggregation.target_year_month == year_month,
        #         TMonthlyBuildingEnergyAggregation.supplier_name.like(f"{energyRowData.SUPPLIER_NAME}%"),
        #     )
        #     .first()
        # )
        # ------------------------------------------------------------------

        year_month = str(energyRowData.YEAR) + str(energyRowData.MONTH).zfill(2)

        new_tMonthlyBuildingEnergyInfo = None
        bucket_key = (
            basic_df["CORPORATE_NUMBER"].iloc[0],
            basic_df["AGREEMENT_CATEGORY"].iloc[0],
            basic_df["ORG_ID"].iloc[0],
            energyRowData.BUILDING_ID,
            energyRowData.ENERGY_CODE,
            year_month,
            0,
        )

        input_supplier_cmp = (
            _supplier_name_lc_series.iloc[energyRowData.Index]
            if energyRowData.SUPPLIER_NAME is not None
            else None
        )

        new_tMonthlyBuildingEnergyInfo = None
        for row in _existing_monthly_energy_bucket.get(bucket_key, []):
            db_supplier = row.supplier_name
            # SQL LIKE 再現：
            # NULL は比較不可、空文字は ""% として一致
            if db_supplier is None:
                continue
            if input_supplier_cmp is None:
                continue
            if db_supplier.startswith(energyRowData.SUPPLIER_NAME):
                new_tMonthlyBuildingEnergyInfo = row
                break  # .first() 再現

        if (
            new_tMonthlyBuildingEnergyInfo is not None
            and energyRowData.UNIT_ORIGIN is pd.NA
        ):
            df_energyInfo.at[energyRowData.Index, "UNIT_ORIGIN"] = (
                new_tMonthlyBuildingEnergyInfo.energy_unit_original
            )

    # NaN（None 含む）の行を削除
    # df_energyInfo = df_energyInfo.dropna(subset=['UNIT_ORIGIN'])
    # df_energyInfo = df_energyInfo[df_energyInfo["ENERGY_QUANTITY"] != ""]
    # 単位統一にする
    df_energyInfo = df_energyInfo.groupby("ENERGY_CODE", group_keys=False).apply(
        energy_unit_standardization
    )

    # 4月より小さい場合、前年度とする
    if int(min_month) < 4:
        basic_df["FISCAL_YEAR"] = int(min_value[:4]) - 1
    else:
        basic_df["FISCAL_YEAR"] = int(min_value[:4])

    # 変換fataframe
    conv_df = pd.DataFrame(
        constants_colums.conversion_data, columns=["UNIT_ORIGIN", "TARGET_UNIT", "COEF"]
    )

    df_energyInfo = standard_unit(ccmst, df_energyInfo, conv_df)

    # 列追加
    df_energyInfo["ENERGY_QUANTITY_FOR_REPORT"] = 0.0
    df_energyInfo["ENERGY_QUANTITY_FOR_LAW"] = 0.0
    # df_energyInfo["TEMPERATURE_BUILDING"] = 0

    # ccmst_energy_info_dict = build_energy_code_dict(ccmst, emission_coef_year)
    ccmst_2024_energy_info_dict = build_energy_code_dict_zeb(ccmst, 2024)

    # 必要な年度をリストアップ（例：2023年～2025年）
    # target_years = set([
    #     int(energyRowData.YEAR) for energyRowData in df_energyInfo.itertuples(index=False)
    # ]) | {int(energyRowData.YEAR) + 1 for energyRowData in df_energyInfo.itertuples(index=False)}

    # 年ごとに辞書を構築
    energy_coef_dict = build_energy_code_dict(ccmst)

    building_info_dict = {
        row.BUILDING_ID: row for row in df_buildingInfo.itertuples(index=False)
    }
    # 建物月別DF
    df_energyInfo = df_energyInfo.replace("None", np.nan)

    # 可視化事業者アップロード用フラグ
    vis_flg: bool = get_vis_flg(basic_df, df_energyInfo)

    ########### 時間計測 ############
    end_time = time.time()
    utils.get_process_time(start_time, end_time, "ループ前処理")

    df_energyInfo["YEAR"] = df_energyInfo["YEAR"].astype(str)
    df_energyInfo["MONTH"] = df_energyInfo["MONTH"].astype(str)
    df_energyInfo = df_energyInfo.astype(object)

    gas_row = gasmst.loc[
        gasmst["city_gas_supplier_code"] == "G0999", "heat_conversion_coefficient"
    ]
    gas_heat_coeff = float(gas_row.iloc[0]) if not gas_row.empty else 40

    # new_df_energyInfo = df_energyInfo.copy()
    # ===== nfcmst 検索高速化用 前処理 =====
    nfcmst = nfcmst.copy()
    nfcmst["REPORT_YEAR"] = nfcmst["REPORT_YEAR"].astype(int)
    # 年ごと & fossil free (=1) の DataFrame を保持
    _nfcmst_ff_by_year = {
        y: g
        for y, g in nfcmst[nfcmst["FOSSIL_FREE_CERT_TYPE_ID"] == "1"].groupby(
            "REPORT_YEAR"
        )
    }
    # fossil free 全体（空判定用）
    _nfcmst_ff_all = nfcmst[nfcmst["FOSSIL_FREE_CERT_TYPE_ID"] == "1"]
    # 全体（fallback 用）
    _nfcmst_all = nfcmst
    # キャッシュ：emission_coef_year → nfcmst_sub
    _nfcmst_cache: dict[int, pd.Series | pd.DataFrame] = {}

    start_time = time.time()
    for energyRowData in df_energyInfo.itertuples():
        # 初期化
        calorificEnergyConsumption = co2EmissionCoefficient_avg = (
            co2EmissionCoefficient
        ) = buildingArea = electric_co2_emission_coef = heat_co2_emission_coef = 0

        calorificEnergyConsumption_2023 = co2EmissionCoefficient_2013 = 0

        nfcmst_sub = nfcmst_sub_2023 = 0

        # 係数年度
        year = int(energyRowData.YEAR)
        month = int(energyRowData.MONTH)

        # 年 + 月 の整数値で比較し、4月以降なら翌年の係数を使用
        emission_coef_year = year + (month >= 4)

        # 電力会社名、建物面積取得
        (
            electricPowerCorporateCode,
            electricPowerMenuNo,
            electricPowerMenuNm,
            heatSupplyRegNo,
            buildingArea,
            buildingAddressPrefecture,
        ) = get_electric_company_buildingarea_by_id(
            building_info_dict, energyRowData.BUILDING_ID
        )

        df_wdimst_sub = df_wdimst[
            (df_wdimst["YEAR"] == int(energyRowData.YEAR))
            & (df_wdimst["MONTH"] == int(energyRowData.MONTH))
        ]
        if df_wdimst_sub.empty:
            df_energyInfo.at[energyRowData.Index, "TEMPERATURE_BUILDING"] = None
        else:
            if buildingAddressPrefecture not in df_wdimst.columns:
                df_energyInfo.at[energyRowData.Index, "TEMPERATURE_BUILDING"] = (
                    df_wdimst_sub["TEMPERATURE_CORP"].iloc[0]
                )
            else:
                value = float(df_wdimst_sub[buildingAddressPrefecture].iloc[0])
                df_energyInfo.at[energyRowData.Index, "TEMPERATURE_BUILDING"] = format(
                    value, ".2f"
                )

        row_energy_code: str = energyRowData.ENERGY_CODE
        officeUsedEnergyInfo = officeUsedEnergyInfo_2023 = None

        # 2023年度以前で電気の場合、電気エネルギーコード変更
        if (
            emission_coef_year < 2024
            and energyRowData.ENERGY_NAME_JP == constants_values.ELECTRIC_POWER_NAME
        ):
            df_energyInfo.at[energyRowData.Index, "ENERGY_CODE"] = (
                constants_values.ENERGY_CODE_ELECTRIC_POWER_2022
            )
            row_energy_code = constants_values.ENERGY_CODE_ELECTRIC_POWER_2022

        is_exist_energy: bool = row_energy_code != "0000000000"
        # 証書クレジット以外
        if not row_energy_code.startswith("9900") and is_exist_energy:

            officeUsedEnergyInfo = get_energy_info(
                energy_coef_dict,
                row_energy_code=row_energy_code,
                emission_coef_year=emission_coef_year,
            )

            # officeUsedEnergyInfo_2023 = get_energy_info(
            #     energy_coef_dict,
            #     row_energy_code=row_energy_code,
            #     emission_coef_year=2024
            # )
            # CN status by ZEB要2023年度係数取得
            officeUsedEnergyInfo_2023 = ccmst_2024_energy_info_dict.get(row_energy_code)

            if officeUsedEnergyInfo is None or officeUsedEnergyInfo_2023 is None:
                abort(
                    412,
                    description="換算係数マスタ情報取得は失敗しました。"
                    + row_energy_code,
                )
        # エネルギー値0へ変換
        if bool(energyRowData.ENERGY_QUANTITY) is False:
            df_energyInfo.loc[
                energyRowData.Index,
                [
                    "ENERGY_QUANTITY",
                    "ENERGY_QUANTITY_FOR_REPORT",
                    "ENERGY_QUANTITY_FOR_LAW",
                ],
            ] = 0.0

            calorificEnergyConsumption = co2EmissionCoefficient = (
                calorificEnergyConsumption_2023
            ) = co2EmissionCoefficient_2013 = buildingArea = 0.0
            electric_co2_emission_coef = 0.000438
        else:
            if is_exist_energy:
                # nfcmst_sub = nfcmst[nfcmst['REPORT_YEAR'] == str(emission_coef_year)]
                # nfcmst_sub = nfcmst_sub[nfcmst_sub['FOSSIL_FREE_CERT_TYPE_ID'] == "1"]
                # if nfcmst_sub.empty:
                #     nfcmst_sub = nfcmst.loc[nfcmst['REPORT_YEAR'].idxmax()]
                #     if nfcmst_sub['FOSSIL_FREE_CERT_TYPE_ID'] == "1":
                #         nfcmst_sub = nfcmst_sub

                # 文字列 → int に変換しておく
                target_year = int(emission_coef_year)

                if target_year in _nfcmst_cache:
                    nfcmst_sub = _nfcmst_cache[target_year]
                else:
                    # 対象年 + fossil free
                    if target_year in _nfcmst_ff_by_year:
                        nfcmst_sub = _nfcmst_ff_by_year[target_year]
                    else:
                        # fossil free の中で最も近い年
                        if not _nfcmst_ff_all.empty:
                            idx = (
                                (_nfcmst_ff_all["REPORT_YEAR"] - target_year)
                                .abs()
                                .idxmin()
                            )
                            nfcmst_sub = _nfcmst_ff_all.loc[idx]
                        else:
                            # 全体から最も近い年
                            idx = (
                                (_nfcmst_all["REPORT_YEAR"] - target_year)
                                .abs()
                                .idxmin()
                            )
                            nfcmst_sub = _nfcmst_all.loc[idx]

                    _nfcmst_cache[target_year] = nfcmst_sub

                # 電力会社係数取得
                if (
                    constants_values.ENERGY_CODE_ELECTRIC_POWER_2022 == row_energy_code
                    or constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
                    == row_energy_code
                ):  # 電力
                    # electric_co2_emission_coef, menu_name_electric, electric_supplier_nm= utils.get_co2EmissionCoefficient(
                    #     ecmst,electricPowerCorporateCode, electricPowerMenuNo, electricPowerMenuNm, str(emission_coef_year), nfcmst_sub)

                    electric_co2_emission_coef = (
                        float(energyRowData.CO2_ADJUSTED_EMISSION_FACTOR)
                        if energyRowData.CO2_ADJUSTED_EMISSIONS not in ["", None]
                        and energyRowData.CO2_ADJUSTED_EMISSION_FACTOR not in ["", None]
                        else utils.get_co2EmissionCoefficient(
                            ecmst,
                            energyRowData.SUPPLIER_REG_NO,
                            energyRowData.SUPPLY_MENU_NO,
                            energyRowData.SUPPLY_MENU,
                            str(emission_coef_year),
                            nfcmst_sub,
                        )
                    )

            # 月単位の年の対象外エネルギーを外す
            if not row_energy_code.startswith("9900") and is_exist_energy:
                df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_REPORT"] = (
                    calc_report(energyRowData)
                )
                df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_LAW"] = (
                    calc_law(energyRowData)
                )

                if vis_flg:
                    # 可視化事業者の場合

                    # 熱量、原油、CO2排出量換算
                    calorificEnergyConsumption = (
                        energyRowData.HEAT_CONVERTED_ENERGY_USAGE_MONTHLY
                    )
                    co2EmissionCoefficient = energyRowData.CO2_ADJUSTED_EMISSIONS

                    if (
                        constants_values.ENERGY_CODE_ELECTRIC_POWER_2022
                        == energyRowData.ENERGY_CODE
                        or constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
                        == energyRowData.ENERGY_CODE
                    ):

                        if energyRowData.SUPPLIER_REG_NO not in ("REENE", "SCOPE"):
                            # 再エネ以外はCO2調整後平均排出量取得
                            if not nfcmst_sub.empty:
                                val = nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]
                                val = val.iloc[0] if hasattr(val, "iloc") else val

                                co2EmissionCoefficient_avg = (
                                    ceas.co2ElectricCoefficient(
                                        calmst,
                                        float(
                                            df_energyInfo.at[
                                                energyRowData.Index,
                                                "ENERGY_QUANTITY_FOR_LAW",
                                            ]
                                        ),
                                        float(val),
                                    )
                                )
                    if calorificEnergyConsumption in [
                        "",
                        None,
                    ] or co2EmissionCoefficient in ["", None]:
                        (
                            calorificEnergyConsumption,
                            co2EmissionCoefficient,
                            heat_co2_emission_coef,
                        ) = get_value(
                            officeUsedEnergyInfo,
                            energyRowData,
                            df_energyInfo.at[
                                energyRowData.Index, "ENERGY_QUANTITY_FOR_LAW"
                            ],
                            heatSupplyRegNo,
                            emission_coef_year,
                            calmst,
                            hsmst,
                            electric_co2_emission_coef,
                            gas_heat_coeff,
                            calorificEnergyConsumption,
                            co2EmissionCoefficient,
                            nfcmst_sub,
                        )

                    # 一次エネルギー熱量、CO2排出量取得
                    calorificEnergyConsumption_2023, co2EmissionCoefficient_2013 = (
                        get_value_once_energy(
                            officeUsedEnergyInfo_2023,
                            energyRowData,
                            df_energyInfo.at[
                                energyRowData.Index, "ENERGY_QUANTITY_FOR_LAW"
                            ],
                            calmst,
                            gas_heat_coeff,
                        )
                    )

        # Nan値を0に変更
        calorificEnergyConsumption = (
            0
            if not bool(calorificEnergyConsumption)
            else float(calorificEnergyConsumption)
        )
        co2EmissionCoefficient_avg = (
            0
            if not bool(co2EmissionCoefficient_avg)
            else float(co2EmissionCoefficient_avg)
        )
        co2EmissionCoefficient = (
            0 if not bool(co2EmissionCoefficient) else float(co2EmissionCoefficient)
        )

        calorificEnergyConsumption_2023 = (
            0
            if not bool(calorificEnergyConsumption_2023)
            else float(calorificEnergyConsumption_2023)
        )
        co2EmissionCoefficient_2013 = (
            0
            if not bool(co2EmissionCoefficient_2013)
            else float(co2EmissionCoefficient_2013)
        )

        # TABLEAU表示のため、エネルギーコード統一にする
        if row_energy_code == constants_values.ENERGY_CODE_ELECTRIC_POWER_2022:
            df_energyInfo.at[energyRowData.Index, "ENERGY_CODE"] = (
                constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
            )
            # energyRowData.ENERGY_CODE = '0200010011'

        year_month = str(energyRowData.YEAR) + str(energyRowData.MONTH).zfill(2)
        # updated_energy_dict = {
        #     "ENERGY_CODE": df_energyInfo.at[energyRowData.Index, "ENERGY_CODE"],
        #     "FISCAL_YEAR": emission_coef_year - 1,
        #     "ENERGY_QUANTITY": df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY"] \
        #         if df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY"] else float(tMonthlyBuildingEnergyInfo.energy_quantity) if tMonthlyBuildingEnergyInfo.supplier_name == energyRowData.SUPPLIER_NAME else 0.0,
        #     "ENERGY_QUANTITY_FOR_LAW": df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_LAW"] \
        #         if df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_LAW"] else float(tMonthlyBuildingEnergyInfo.energy_quantity_for_law) if tMonthlyBuildingEnergyInfo.supplier_name == energyRowData.SUPPLIER_NAME else 0.0,
        #     "ENERGY_QUANTITY_FOR_REPORT": df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_REPORT"] \
        #         if df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_REPORT"] else float(tMonthlyBuildingEnergyInfo.energy_quantity_for_report) if tMonthlyBuildingEnergyInfo.supplier_name == energyRowData.SUPPLIER_NAME else 0.0,
        #     "TEMPERATURE_BUILDING": df_energyInfo.at[energyRowData.Index, "TEMPERATURE_BUILDING"]
        #     # "SUPPLIER_NAME": supplier_name, # TODO いるか？ energyrowに既に含まれているか
        #     # "SUPPLY_MENU": supply_menu,
        # }
        # ------------------------------------------------------------
        # 【修正前SQL（意味論保持のため残す）】
        # tEnergyStorageCommonInfo = (
        #     session.query(TEnergyStorageCommonForVisualization)
        #     .filter(
        #         TEnergyStorageCommonForVisualization.corporate_number == basic_df['CORPORATE_NUMBER'].iloc[0],
        #         TEnergyStorageCommonForVisualization.agreement_category == basic_df['AGREEMENT_CATEGORY'].iloc[0],
        #         TEnergyStorageCommonForVisualization.org_id == basic_df["ORG_ID"].iloc[0],
        #         TEnergyStorageCommonForVisualization.building_id == energyRowData.BUILDING_ID,
        #         TEnergyStorageCommonForVisualization.energy_code == energyRowData.ENERGY_CODE,
        #         TEnergyStorageCommonForVisualization.year_month == year_month,
        #         TEnergyStorageCommonForVisualization.input_supplier_name == energyRowData.INPUT_SUPPLIER_NAME,
        #     )
        #     .first()
        # )
        # ------------------------------------------------------------

        supplier_key = energyRowData.INPUT_SUPPLIER_NAME
        # SQL の「=」比較再現（None と "" は区別）
        bucket_key = (
            energyRowData.BUILDING_ID,
            energyRowData.ENERGY_CODE,
            year_month,
            supplier_key,
        )
        bucket = _vis_energy_bucket.get(bucket_key, [])
        tEnergyStorageCommonInfo = bucket[0] if bucket else None

        updated_energy_dict = {
            "ENERGY_CODE": df_energyInfo.at[energyRowData.Index, "ENERGY_CODE"],
            "FISCAL_YEAR": emission_coef_year - 1,
            "ENERGY_QUANTITY": (
                df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY"]
                if df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY"]
                else (
                    float(tEnergyStorageCommonInfo.energy_usage_monthly)
                    if tEnergyStorageCommonInfo
                    else 0.0
                )
            ),
            "ENERGY_QUANTITY_FOR_LAW": (
                df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_LAW"]
                if df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_LAW"]
                else 0
            ),
            "ENERGY_QUANTITY_FOR_REPORT": (
                df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_REPORT"]
                if df_energyInfo.at[energyRowData.Index, "ENERGY_QUANTITY_FOR_REPORT"]
                else 0
            ),
            "TEMPERATURE_BUILDING": df_energyInfo.at[
                energyRowData.Index, "TEMPERATURE_BUILDING"
            ],
            # "SUPPLIER_NAME": supplier_name, # TODO いるか？ energyrowに既に含まれているか
            # "SUPPLY_MENU": supply_menu,
        }

        # 建物月別集計データEntity取得
        tMonthlyBuildingEnergyAggregation = get_building_month_entity(
            session,
            basic_df,
            energyRowData,
            officeUsedEnergyInfo,
            calorificEnergyConsumption,
            co2EmissionCoefficient,
            calorificEnergyConsumption_2023,
            co2EmissionCoefficient_2013,
            float(buildingArea),
            electric_co2_emission_coef,
            heat_co2_emission_coef,
            updated_energy_dict,
            building_month_list,
            vis_common_list,
            excel_row_list,
            co2EmissionCoefficient_avg,
            tEnergyStorageCommonInfo,
        )

        compare_entity_with_model(
            TMonthlyBuildingEnergyAggregation, tMonthlyBuildingEnergyAggregation
        )

        # リストに集計済エネルギー情報格納
        # monthlyBuildingEnergyAggregationList.append(tMonthlyBuildingEnergyAggregation)

    ########### 時間計測 ############
    end_time = time.time()
    utils.get_process_time(start_time, end_time, "一レコード処理時間")

    def convert_unit_lpgas(row):
        unit = str(row.get("energy_unit_original", "")).lower()
        value = row.get("energy_quantity", 0)
        if pd.isna(value):
            return 0
        # if unit == "m3":
        #     return value * 2.18
        elif unit == "kg":
            return value / 2.18
        else:
            # すでに m3 の場合 or その他単位はそのまま
            return value

    def convert_unit_heat(row):
        unit = str(row.get("energy_unit_original", ""))
        value = row.get("energy_quantity", 0)
        if pd.isna(value):
            return 0
        if unit == "Mcal":
            return value * 4.18
        else:
            # すでに MJ の場合 or その他単位はそのまま
            return value

    def custom_last_or_not_reene(group):
        """グループ単位で、energy_code='0200010011' の場合は REENE・None 以外を優先"""
        if group["energy_code"].iloc[0] == "0200010011":
            # supplier_reg_no が None/NaN でなく、REENE でもないものを抽出
            non_reene = group[
                group["supplier_reg_no"].notna() & (group["supplier_reg_no"] != "REENE")
            ]
            if not non_reene.empty:
                return non_reene.iloc[-1]  # 該当があればその最後を返す
        # それ以外は通常通り最後の行
        return group.iloc[-1]

    if len(building_month_list) > 0:

        # SQLAlchemy エンティティ → dict に変換
        dict_list = [obj.__dict__ for obj in building_month_list]

        # SQLAlchemy は _sa_instance_state を持っているので除去
        for d in dict_list:
            d.pop("_sa_instance_state", None)

        building_month_df = pd.DataFrame(dict_list)
        building_month_df.columns = building_month_df.columns.str.lower()

        # --- 各エネルギーコードごとにマスク ---
        lpgas_mask = building_month_df["energy_code"] == "0100190000"
        # reisui_mask = building_month_df["energy_code"] == "0300040000"
        heat_mask = building_month_df["energy_code"].str.startswith("03")

        # --- 各マスクごとに単位変換を適用 ---
        building_month_df.loc[lpgas_mask, "energy_quantity"] = building_month_df[
            lpgas_mask
        ].apply(convert_unit_lpgas, axis=1)

        building_month_df.loc[heat_mask, "energy_quantity"] = building_month_df[
            heat_mask
        ].apply(convert_unit_heat, axis=1)
        building_month_df.loc[heat_mask, "energy_unit_original"] = "MJ"
        building_month_df["excel_row"] = excel_row_list

        sum_cols = [
            "energy_quantity",
            "energy_quantity_for_law",
            "energy_quantity_for_report",
            "energy_usage_area_unit",
            "heat_converted_energy_usage",
            "heat_converted_energy_usage_area_unit",
            "co2_base_emissions",
            "co2_adjusted_emissions_area_unit",
            "co2_adjusted_emissions",
            "co2_adjusted_emissions_zeb",
            "co2_adjusted_emissions_avg",
            "heat_converted_energy_usage_zeb",
        ]

        # 集計キー
        agg_keys = [
            "building_id",
            "energy_code",
            "target_year_month",
            "supplier_reg_no",
        ]

        # 数値列は sum
        # agg_dict = {col: "sum" for col in sum_cols}

        # # それ以外の列は group 内の最後の行を残す
        # for col in building_month_df.columns:
        #     if col not in agg_keys + sum_cols:
        #         agg_dict[col] = "last"

        # # groupby 集計（キーごとに最後の行の値を残す）
        # df_building_month_grouped = building_month_df.groupby(agg_keys, as_index=False).agg(agg_dict)

        # # df_energyInfo から ENERGY_QUANTITY が未設定（NaN / None）のデータを抽出
        # empty_energy_df = new_df_energyInfo[
        #     new_df_energyInfo["ENERGY_QUANTITY"].isna()
        #     | (new_df_energyInfo["ENERGY_QUANTITY"].astype(str).str.strip() == "")
        # ]

        # # 除外対象とするキー項目を building_month_df 側の列名に合わせて抽出（重複排除）
        # exclude_keys = (
        #     empty_energy_df[
        #         ["BUILDING_ID", "YEAR_MONTH", "ENERGY_CODE", "SUPPLIER_REG_NO"]
        #     ]
        #     .rename(columns={
        #         "BUILDING_ID": "building_id",
        #         "YEAR_MONTH": "target_year_month",
        #         "ENERGY_CODE": "energy_code",
        #         "SUPPLIER_REG_NO": "supplier_reg_no"
        #     })
        #     .drop_duplicates()
        # )

        # # building_month_df から該当するレコードを除外
        # building_month_df = (
        #     building_month_df
        #     .merge(
        #         exclude_keys,
        #         on=["building_id", "target_year_month", "energy_code", "supplier_reg_no"],
        #         how="left",
        #         indicator=True
        #     )
        #     .query("_merge == 'left_only'")
        #     .drop(columns="_merge")
        # )

        df_sum = building_month_df.groupby(agg_keys, as_index=False)[sum_cols].sum()

        # # グループ内最大 excel_row の index を取得
        idx = building_month_df.groupby(agg_keys)["excel_row"].idxmax()

        # 代表行を取得（sum_cols と agg_keys を除いた列）
        pick_cols = [
            c for c in building_month_df.columns if c not in sum_cols + agg_keys
        ]
        df_max = building_month_df.loc[idx, agg_keys + pick_cols].reset_index(drop=True)

        # sum 列と代表行を merge
        df_building_month_grouped = pd.merge(df_max, df_sum, on=agg_keys, how="left")

        mask = (
            df_building_month_grouped["energy_name_for_coefficient_matching"] == "冷水"
        )
        df_building_month_grouped.loc[mask, "energy_category_name"] = "冷水"

        df_building_month_grouped.to_csv(f"df_building_month_grouped.csv", index=False)

        # 必要に応じてリスト化
        result_list = df_building_month_grouped.to_dict(orient="records")

        # # モデル定義から有効なカラムを取得
        # valid_cols = [col.name for col in TMonthlyBuildingEnergyAggregation.__table__.columns]

        # # 想定外の列を除外
        # rep_df = rep_df[[c for c in rep_df.columns if c in valid_cols]]

        # # 辞書リストに変換
        # result_list = rep_df.to_dict(orient="records")
        db_cols = [c.name for c in TMonthlyBuildingEnergyAggregation.__table__.columns]

        result_entity_list = [
            TMonthlyBuildingEnergyAggregation(
                **{k: v for k, v in row.items() if k in db_cols}
            )
            for row in result_list
        ]
        # --- 既存月別集計データ一括取得 ---
        existing_bm_list = get_existing_bm_list(session, result_entity_list)

        _existing_bm_bucket = defaultdict(list)
        for row in existing_bm_list:
            key = (
                row.corporate_number,
                row.agreement_category,
                row.org_id,
                row.building_id,
                row.energy_code,
                row.target_year_month,
                row.supplier_reg_no,
            )
            # DB返却順を保持（.first() 再現）
            _existing_bm_bucket[key].append(row)

        user_id = basic_df["CREATED_BY"].iloc[0]
        exclude_fields = {
            "updated_at",
            "updated_by",
            "created_at",
            "created_by",
            "delete_flg",
        }

        for bm_entity in result_entity_list:
            tMonthlyBuildingEnergyAggregation = None

            key = (
                bm_entity.corporate_number,
                bm_entity.agreement_category,
                bm_entity.org_id,
                bm_entity.building_id,
                bm_entity.energy_code,
                bm_entity.target_year_month,
                bm_entity.supplier_reg_no,
            )

            # .first() 再現
            bucket = _existing_bm_bucket.get(key, [])
            tMonthlyBuildingEnergyAggregation = bucket[0] if bucket else None

            if not tMonthlyBuildingEnergyAggregation:
                bm_entity.created_by = user_id
                session.add(bm_entity)
            else:
                for k, v in bm_entity.__dict__.items():
                    if k not in exclude_fields and not k.startswith("_"):
                        setattr(tMonthlyBuildingEnergyAggregation, k, v)
                tMonthlyBuildingEnergyAggregation.updated_by = user_id

    monthlyBuildingEnergyAggregation_df = pd.DataFrame(
        [
            {
                col.name: getattr(row, col.name)
                for col in TMonthlyBuildingEnergyAggregation.__table__.columns
            }
            for row in result_entity_list
        ]
    )

    monthlyBuildingEnergyAggregation_df.columns = (
        monthlyBuildingEnergyAggregation_df.columns.str.upper()
    )
    # vis_common_df.columns = vis_common_df.columns.str.upper()
    monthlyBuildingEnergyAggregation_df.to_csv(
        "monthlyBuildingEnergyAggregation_df.csv", index=False
    )
    return monthlyBuildingEnergyAggregation_df


def get_electric_company_buildingarea_by_id(building_info_map, building_id):
    row = building_info_map.get(building_id)
    if row is None:
        abort(400, description=get_message("MASTER_DATA_NOT_FOUND", id=building_id))
        # return BLANK, "", "", BLANK, BLANK, ""

    electricPowerMenuNo = getattr(row, "MENU_NO", "")
    electricPowerMenuNm = getattr(row, "MENU_NM", "")

    return (
        row.ELECTRIC_COMPANY_REG_NO,
        electricPowerMenuNo,
        electricPowerMenuNm,
        row.HEAT_SUPPLY_REG_NO,
        row.GROSS_FLOOR_AREA,
        row.BUILDING_ADDRESS_PREFECTURE,
    )


def get_field_precision_and_scale(model_class, field_name):
    mapper = inspect(model_class)
    col = mapper.columns.get(field_name)
    if col is None:
        raise ValueError(
            f"モデル {model_class.__name__} に {field_name} 列が存在しません。"
        )
    col_type = col.type
    precision = getattr(col_type, "precision", None)
    scale = getattr(col_type, "scale", None)
    return precision, scale


def validate_field_against_model(model_class, entity, field_name):
    precision, scale = get_field_precision_and_scale(model_class, field_name)
    if precision is None:
        # 数值型でない場合などはスキップ
        return

    value = getattr(entity, field_name, None)
    if value is None:
        return

    value = Decimal(str(value))
    integer_part = str(value).split(".")[0]
    allowed_integer_digits = precision - (scale or 0)

    if len(integer_part) > allowed_integer_digits:
        error_msg = (
            f"{model_class.__tablename__}.{field_name} の整数部が "
            f"{allowed_integer_digits} 桁を超えています。"
            f"（現在 {len(integer_part)} 桁, 値={value}）"
        )

        abort(400, description=f"桁を超えています。詳細：{error_msg}")


# @log_time
def compare_entity_with_model(model_class, entity):
    # 対象フィールドを指定
    if model_class == TMonthlyBuildingEnergyAggregation:
        fields = [
            "energy_quantity_for_law",
            "energy_usage_area_unit",
            "energy_quantity",
            "energy_quantity_for_report",
            "heat_converted_energy_usage",
            "heat_converted_energy_usage_zeb",
            "heat_converted_energy_usage_area_unit",
            "co2_base_emissions",
            "co2_adjusted_emissions",
            "co2_adjusted_emissions_zeb",
            "co2_adjusted_emissions_avg",
            "co2_adjusted_emissions_area_unit",
        ]
    elif model_class == TMonthlyCorporateEnergyAggregation:
        fields = [
            "energy_quantity_for_law",
            "energy_usage_area_unit",
            "energy_quantity",
            "energy_quantity_for_report",
            "heat_converted_energy_usage",
            "heat_converted_energy_usage_area_unit",
            "co2_base_emissions",
            "co2_adjusted_emissions",
            "co2_adjusted_emissions_area_unit",
        ]
    elif model_class == TAnnualBuildingEnergyAggregation:
        fields = [
            "energy_quantity_for_law",
            "energy_quantity_for_report",
            "energy_quantity",
            "heat_converted_energy_usage",
            "co2_adjusted_emissions",
        ]
    elif model_class == TAnnualCorporateEnergyAggregation:
        fields = [
            "energy_quantity_for_law",
            "energy_quantity_for_report",
            "energy_quantity",
            "heat_converted_energy_usage",
            "co2_adjusted_emissions",
        ]
    elif model_class == TEnergyStorageCommonForVisualization:
        fields = [
            "energy_usage_monthly",
            "heat_converted_energy_usage_monthly",
            "co2_base_emissions",
            "co2_adjusted_emissions_monthly",
        ]
    else:
        None

    for field in fields:
        if hasattr(entity, field):
            validate_field_against_model(model_class, entity, field)


def energy_unit_standardization(group):
    """
    単位の換算
    """
    units = group["UNIT_ORIGIN"].unique()
    energy_code = group["ENERGY_CODE"].unique()

    if len(units) == 1:
        # 単位一致の場合、変換しない
        group["ENERGY_UNIT_FOR_REPORT"] = group["UNIT_ORIGIN"]
        # group["ENERGY_QUANTITY_FOR_LAW"] = group["ENERGY_QUANTITY"]

        # if group["ENERGY_UNIT_FOR_LAW"] != group["UNIT_ORIGIN"]:
        #     group["ENERGY_QUANTITY_FOR_LAW"] = group["ENERGY_QUANTITY"]/0.001
        return group

    # エネルギー単位（GJ/MJ/Mcal）
    energy_units = [u for u in units if u in constants_colums.heat_energy_priority]
    mass_vol_units = [u for u in units if u in constants_colums.mass_volume_priority]
    gas_serise_code = [e for e in energy_code if e in constants_colums.gas_energy_code]

    # 熱量単位換算
    if energy_units:
        if "GJ" in energy_units:
            target = "GJ"
        elif "MJ" in energy_units:
            target = "MJ"
        else:
            target = "Mcal"
        group["ENERGY_UNIT_FOR_REPORT"] = target
    # ガス単位換算
    elif mass_vol_units and gas_serise_code:
        if "T" in mass_vol_units:
            target = "t"
        elif "KG" in mass_vol_units:
            target = "kg"
        else:
            target = "m3"
        group["ENERGY_UNIT_FOR_REPORT"] = target
    # 上記以外エネルギー単位換算
    else:
        # その他の単位変換
        group["ENERGY_UNIT_FOR_REPORT"] = group["UNIT_ORIGIN"].map(
            lambda x: constants_colums.basic_unit_map.get(x, x)
        )

    return group


# @log_time
def standard_unit(ccmst, df_energyInfo, conv_df):
    # 省エネ単位設定
    ccmst["ENERGY_CODE"] = (
        ccmst["MAJOR_CATEGORY_ID"]
        + ccmst["MIDDLE_CATEGORY_ID"]
        + ccmst["MINOR_CATEGORY_ID"]
    )
    df = ccmst[["ENERGY_CODE", "UNIT"]].drop_duplicates()
    # df2 に df1.unit をマージ
    df_energyInfo = df_energyInfo.merge(
        df[["ENERGY_CODE", "UNIT"]],
        how="left",
        on="ENERGY_CODE",
        suffixes=("", "_ccmst"),
    )
    # unit の値を ENERGY_UNIT_FOR_LAW にセット
    df_energyInfo = df_energyInfo.rename(columns={"UNIT": "ENERGY_UNIT_FOR_LAW"})
    # レポート用マージする
    df_energyInfo = (
        df_energyInfo.merge(
            conv_df,
            how="left",
            left_on=["UNIT_ORIGIN", "ENERGY_UNIT_FOR_REPORT"],
            right_on=["UNIT_ORIGIN", "TARGET_UNIT"],
        )
        .rename(columns={"COEF": "COEF_REPORT"})
        .drop(columns=["TARGET_UNIT"])
    )
    # 省エネ法用マージする
    # 変換fataframe
    propane_conv_df = pd.DataFrame(
        constants_colums.propane_conversion_data,
        columns=["UNIT_ORIGIN", "TARGET_UNIT", "COEF"],
    )
    mask_propane = df_energyInfo["INPUT_SUPPLIER_NAME"] == "一般（プロパン100% m3）"
    mask_others = ~mask_propane
    df_energyInfo["__orig_index__"] = df_energyInfo.index
    # 供給会社が"一般（プロパン100% m3）"の場合
    df_energyInfo_propane = (
        df_energyInfo.loc[mask_propane]
        .merge(
            propane_conv_df,
            how="left",
            left_on=["UNIT_ORIGIN", "ENERGY_UNIT_FOR_LAW"],
            right_on=["UNIT_ORIGIN", "TARGET_UNIT"],
        )
        .rename(columns={"COEF": "COEF_LAW"})
        .drop(columns=["TARGET_UNIT"])
    )
    # 供給会社が"一般（プロパン100% m3）"以外の場合
    df_energyInfo_others = (
        df_energyInfo.loc[mask_others]
        .merge(
            conv_df,
            how="left",
            left_on=["UNIT_ORIGIN", "ENERGY_UNIT_FOR_LAW"],
            right_on=["UNIT_ORIGIN", "TARGET_UNIT"],
        )
        .rename(columns={"COEF": "COEF_LAW"})
        .drop(columns=["TARGET_UNIT"])
    )
    df_energyInfo = pd.concat([df_energyInfo_propane, df_energyInfo_others], axis=0)
    df_energyInfo = (
        df_energyInfo.sort_values("__orig_index__")
        .reset_index(drop=True)
        .drop(columns="__orig_index__")
    )

    return df_energyInfo


# REPORT の変換
def calc_report(row):
    if pd.notnull(row.COEF_REPORT):
        return row.ENERGY_QUANTITY * row.COEF_REPORT
    else:
        return None


# LAW の変換
def calc_law(row):
    if pd.notnull(row.COEF_LAW):
        return row.ENERGY_QUANTITY * row.COEF_LAW
    else:
        return None


def get_building_year_df(session, basic_df, monthlyBuildingEnergyAggregation_df):
    """
    建物年別集計データDF取得
    params:
    return:
    """
    annualBuildingEnergyAggregationList = []
    officeYearly_grouped_df = (
        monthlyBuildingEnergyAggregation_df.groupby(
            [
                "FISCAL_YEAR",
                "ENERGY_CODE",
                "BUILDING_NAME",
                "ENERGY_CATEGORY_NAME",
                "ENERGY_UNIT_ORIGINAL",
                "ENERGY_UNIT_FOR_LAW",
                "ENERGY_UNIT_FOR_REPORT",
                "BUILDING_ID",
                "SUPPLIER_REG_NO",
                "ENERGY_NAME_FOR_COEFFICIENT_MATCHING",
            ],
            dropna=False,
        )[
            [
                "ENERGY_QUANTITY",
                "ENERGY_QUANTITY_FOR_LAW",
                "ENERGY_QUANTITY_FOR_REPORT",
                "ENERGY_USAGE_AREA_UNIT",
                "HEAT_CONVERTED_ENERGY_USAGE",
                "HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT",
                "CO2_ADJUSTED_EMISSIONS_AREA_UNIT",
                "CO2_ADJUSTED_EMISSIONS",
                "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT",
                "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT",
            ]
        ]
        .sum()
        .reset_index()
    )

    # df_final = df_final[final_columns]
    officeYearly_grouped_df.to_csv(f"df_final.csv", index=False)
    # CO2排出量ランキング計算
    area_emissions_rank = (
        officeYearly_grouped_df.groupby("BUILDING_ID")[
            "CO2_ADJUSTED_EMISSIONS_AREA_UNIT"
        ]
        .sum()
        .rank(method="first", ascending=False)
        .astype(int)
    )

    # for index, row in officeYearly_grouped_df.iterrows():
    for row in officeYearly_grouped_df.itertuples():

        tAnnualBuildingEnergyAggregation = get_building_annual_entity(
            session, basic_df, row
        )

        compare_entity_with_model(
            TAnnualBuildingEnergyAggregation, tAnnualBuildingEnergyAggregation
        )

        # リストに集計済エネルギー情報格納
        annualBuildingEnergyAggregationList.append(tAnnualBuildingEnergyAggregation)

    # listからDFへ変換
    annualBuildingEnergyAggregation_df = pd.DataFrame(
        [
            {
                col.name: getattr(row, col.name)
                for col in TAnnualBuildingEnergyAggregation.__table__.columns
            }
            for row in annualBuildingEnergyAggregationList
        ]
    )

    return annualBuildingEnergyAggregation_df


# @log_time
def get_company_month_df(session, basic_df, monthlyBuildingEnergyAggregation_df):
    """
    企業月別集計データDF取得
    params:
    return:
    """
    tMonthlyCorporateEnergyAggregationList = []
    corporateMonthly_grouped_df = monthlyBuildingEnergyAggregation_df.groupby(
        [
            "ENERGY_CODE",
            "ENERGY_CATEGORY_NAME",
            "ENERGY_UNIT_FOR_LAW",
            "ENERGY_UNIT_FOR_REPORT",
            "TARGET_YEAR_MONTH",
            "ENERGY_NAME_FOR_COEFFICIENT_MATCHING",
            # ← HEAT_CONVERSION_COEFFICIENT, CO2_ADJUSTED_EMISSION_FACTOR
        ],
        as_index=False,
    ).agg(
        {
            "ENERGY_QUANTITY": "sum",
            "ENERGY_QUANTITY_FOR_LAW": "sum",
            "ENERGY_QUANTITY_FOR_REPORT": "sum",
            "ENERGY_USAGE_AREA_UNIT": "sum",
            "HEAT_CONVERTED_ENERGY_USAGE": "sum",
            "HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT": "sum",
            "CO2_ADJUSTED_EMISSIONS_AREA_UNIT": "sum",
            "CO2_ADJUSTED_EMISSIONS": "sum",
            "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT": "sum",
            "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT": "sum",
            "HEAT_CONVERSION_COEFFICIENT": "last",
            "CO2_ADJUSTED_EMISSION_FACTOR": "last",
            "FISCAL_YEAR": "first",
        }
    )

    # --- 2. 出力 ---
    corporateMonthly_grouped_df.to_csv("corporateMonthly_grouped_df.csv", index=False)

    # --- 3. CO2排出量ランキング計算 ---
    monthly_emissions_rank = (
        corporateMonthly_grouped_df.groupby("TARGET_YEAR_MONTH")[
            "CO2_ADJUSTED_EMISSIONS"
        ]
        .sum()
        .rank(method="first", ascending=False)
        .astype(int)
    )

    for row in corporateMonthly_grouped_df.itertuples():

        corporationMonthlyEntity = get_company_month_entity(session, basic_df, row)

        compare_entity_with_model(
            TMonthlyCorporateEnergyAggregation, corporationMonthlyEntity
        )

        # リストに集計済エネルギー情報格納
        tMonthlyCorporateEnergyAggregationList.append(corporationMonthlyEntity)

    # listからDFへ変換
    monthlyCorporateEnergyAggregation_df = pd.DataFrame(
        [
            {
                col.name: getattr(row, col.name)
                for col in TMonthlyCorporateEnergyAggregation.__table__.columns
            }
            for row in tMonthlyCorporateEnergyAggregationList
        ]
    )

    # numpyからintへ
    monthlyCorporateEnergyAggregation_df = (
        monthlyCorporateEnergyAggregation_df.applymap(
            lambda x: int(x) if isinstance(x, np.integer) else x
        )
    )

    return monthlyCorporateEnergyAggregation_df


# @log_time
def get_company_year_df(session, basic_df, monthlyBuildingEnergyAggregation_df):
    """
    企業年別集計データDF取得
    params:
    return:
    """
    tAnnualCorporateEnergyAggregationList = []

    corporateYearly_grouped_df = (
        monthlyBuildingEnergyAggregation_df.groupby(
            [
                "ENERGY_CODE",
                "FISCAL_YEAR",
                "ENERGY_CATEGORY_NAME",
                "ENERGY_UNIT_FOR_LAW",
                "ENERGY_UNIT_FOR_REPORT",
                "ENERGY_NAME_FOR_COEFFICIENT_MATCHING",
            ]
        )[
            [
                "ENERGY_QUANTITY",
                "ENERGY_QUANTITY_FOR_LAW",
                "ENERGY_QUANTITY_FOR_REPORT",
                "ENERGY_USAGE_AREA_UNIT",
                "HEAT_CONVERTED_ENERGY_USAGE",
                "HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT",
                "CO2_ADJUSTED_EMISSIONS_AREA_UNIT",
                "CO2_ADJUSTED_EMISSIONS",
                "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT",
                "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT",
            ]
        ]
        .sum()
        .reset_index()
    )

    corporateYearly_grouped_df.to_csv("corporateYearly_grouped_df.csv", index=False)

    for row in corporateYearly_grouped_df.itertuples():
        tAnnualCorporateEnergyAggregation = get_company_annual_entity(
            session, basic_df, row
        )

        compare_entity_with_model(
            TAnnualCorporateEnergyAggregation, tAnnualCorporateEnergyAggregation
        )

        # リストに集計済エネルギー情報格納
        tAnnualCorporateEnergyAggregationList.append(tAnnualCorporateEnergyAggregation)

    annualCorporateEnergyAggregation_df = pd.DataFrame(
        [
            {
                col.name: getattr(row, col.name)
                for col in TAnnualCorporateEnergyAggregation.__table__.columns
            }
            for row in tAnnualCorporateEnergyAggregationList
        ]
    )

    # numpyからintへ
    annualCorporateEnergyAggregation_df = annualCorporateEnergyAggregation_df.applymap(
        lambda x: int(x) if isinstance(x, np.integer) else x
    )

    return annualCorporateEnergyAggregation_df


def get_electric_company_buildingarea(df_buildingInfo, energyRowData):
    # 電力会社名前変数定義
    electricPowerCorporateCode = BLANK
    # 建物面積変数定義
    buildingArea = BLANK

    for buildingRowData in df_buildingInfo.itertuples(index=False):

        if buildingRowData.BUILDING_ID == energyRowData["BUILDING_ID"]:

            electricPowerMenuNo = electricPowerMenuNm = ""

            electricPowerCorporateCode = buildingRowData.ELECTRIC_COMPANY_REG_NO
            if "MENU_NO" in df_buildingInfo.columns:  # 入力シートよりのデータ
                electricPowerMenuNo = buildingRowData.MENU_NO
            if "MENU_NM" in df_buildingInfo.columns:  # 画面よりのデータ
                electricPowerMenuNm = buildingRowData.MENU_NM

            heatSupplyRegNo = buildingRowData.HEAT_SUPPLY_REG_NO
            buildingArea = buildingRowData.GROSS_FLOOR_AREA

            return (
                electricPowerCorporateCode,
                electricPowerMenuNo,
                electricPowerMenuNm,
                heatSupplyRegNo,
                buildingArea,
            )


def get_energy_info(energy_coef_dict, row_energy_code, emission_coef_year):
    # 1. まず対象年度を見る
    year_dict = energy_coef_dict.get(emission_coef_year, {})
    if row_energy_code in year_dict:
        return year_dict[row_energy_code]

    # 2. 他の年で同じ ENERGY_CODE を探す
    # year の絶対差でソートして近い年から探す
    sorted_years = sorted(
        energy_coef_dict.keys(), key=lambda y: abs(y - emission_coef_year)
    )

    for year in sorted_years:
        year_dict = energy_coef_dict[year]
        if row_energy_code in year_dict:
            return year_dict[row_energy_code]

    # 3. それでも無い場合
    return None


def get_existing_bm_list(session, result_entity_list):

    metadata = MetaData()

    temp_keys = Table(
        "temp_bm_keys",
        metadata,
        Column("corporate_number", String),
        Column("agreement_category", String),
        Column("org_id", String),
        Column("building_id", String),
        Column("energy_code", String),
        Column("target_year_month", String),
        Column("supplier_reg_no", String),
        prefixes=["TEMPORARY"],
        postgresql_on_commit="DROP",
    )

    conn = session.connection()

    conn.execute(text("DROP TABLE IF EXISTS temp_bm_keys"))

    temp_keys.create(bind=conn)

    keys = list(
        {
            (
                bm.corporate_number,
                bm.agreement_category,
                bm.org_id,
                bm.building_id,
                bm.energy_code,
                bm.target_year_month,
                bm.supplier_reg_no,
            )
            for bm in result_entity_list
        }
    )

    conn.execute(
        temp_keys.insert(),
        [
            {
                "corporate_number": k[0],
                "agreement_category": k[1],
                "org_id": k[2],
                "building_id": k[3],
                "energy_code": k[4],
                "target_year_month": k[5],
                "supplier_reg_no": k[6],
            }
            for k in keys
        ],
    )

    query = (
        session.query(TMonthlyBuildingEnergyAggregation)
        .join(
            temp_keys,
            (
                TMonthlyBuildingEnergyAggregation.corporate_number
                == temp_keys.c.corporate_number
            )
            & (
                TMonthlyBuildingEnergyAggregation.agreement_category
                == temp_keys.c.agreement_category
            )
            & (TMonthlyBuildingEnergyAggregation.org_id == temp_keys.c.org_id)
            & (TMonthlyBuildingEnergyAggregation.building_id == temp_keys.c.building_id)
            & (TMonthlyBuildingEnergyAggregation.energy_code == temp_keys.c.energy_code)
            & (
                TMonthlyBuildingEnergyAggregation.target_year_month
                == temp_keys.c.target_year_month
            )
            & (
                TMonthlyBuildingEnergyAggregation.supplier_reg_no
                == temp_keys.c.supplier_reg_no
            ),
        )
        .filter(TMonthlyBuildingEnergyAggregation.registration_seq == 0)
    )

    start = perf_counter()
    result = query.all()
    end = perf_counter()

    # print(query.statement.compile(session.get_bind(), compile_kwargs={"literal_binds": True}))
    print(f"SQL time: {end-start:.4f}s")

    return result
