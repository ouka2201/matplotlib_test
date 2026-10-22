import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from flask import abort
from sqlalchemy import or_, tuple_
from sqlalchemy.orm import scoped_session

import cndx_corp_back.common.constants_colums as constants_colums
import cndx_corp_back.common.constants_values as constants_values
import cndx_corp_back.common.utils as utils
import cndx_corp_back.logic.building.common.common_energy_algorithms as ceas
from cndx_corp_back.common.decorators import component
from cndx_corp_back.dto.building.energy_register_in_dto import (
    BuildingEnergyRegisterInDto as InDto,
)
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.t_annual_building_energy_aggregation_entity import (
    TAnnualBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_annual_corporate_energy_aggregation_entity import (
    TAnnualCorporateEnergyAggregation,
)
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_monthly_corporate_energy_aggregation_entity import (
    TMonthlyCorporateEnergyAggregation,
)
from cndx_corp_back.logic.building_vis.master_loader import MasterLoader


@component
def register_energy_aggregation_info(
    conn,
    basic_df,
    df_generalInfo,
    df_buildingInfo,
    df_energyInfo,
    dto: InDto,
    logger=None,
):
    """
    関数名：企業カルテエネルギー集計結果登録
        :params df_generalInfo: 企業基本情報
        :params df_buildingInfo: 事業所情報
        :params df_energyInfo: エネルギー情報
    """
    code_value = basic_df["ADDRESS_PREFECTURE"].iloc[0]
    code_list = df_buildingInfo["BUILDING_ADDRESS_PREFECTURE"].tolist()
    master_loader: MasterLoader = MasterLoader(conn)
    try:
        # マスタデータ取得

        ccmst = master_loader.get_ccmst()
        ecmst = master_loader.get_ecmst()
        calmst = master_loader.get_calmst()
        hsmst = master_loader.get_hsmst()
        wdimst = master_loader.get_wdimst()
        nfcmst = master_loader.get_nfcmst()
        gasmst = master_loader.get_gasmst()
        gasmst = gasmst.rename(columns=str.upper)

        ccimst = _to_df(
            conn.query(MCorpCodeInfo.en_code_name, MCorpCodeInfo.code)
            .filter(
                MCorpCodeInfo.delete_flg == False,
                or_(
                    MCorpCodeInfo.code == code_value, MCorpCodeInfo.code.in_(code_list)
                ),
                MCorpCodeInfo.code_type == "PREF",
            )
            .all(),
            upper=True,
        )
        # 都道府県情報動的に指定する列名
        # col_name = ccimst["EN_CODE_NAME"].iloc[0]
        col_names = ccimst["EN_CODE_NAME"].str.upper().tolist()

        # 天気情報取り出す
        # df_wdimst = wdimst[['TARGET_YEAR', 'TARGET_MONTH', col_name.upper()]]
        df_wdimst = wdimst[["TARGET_YEAR", "TARGET_MONTH"] + col_names]

        mapping = dict(zip(ccimst["EN_CODE_NAME"].str.upper(), ccimst["CODE"]))
        # 英字名から県コードへ変換
        df_wdimst = df_wdimst.rename(columns=mapping)

        # 重複名前の列削除
        dup_cols = df_wdimst.columns[df_wdimst.columns.duplicated()].unique()
        df_wdimst = df_wdimst.drop(columns=dup_cols)

        # 建物月別DF
        monthlyBuildingEnergyAggregation_df, supplier_name, supply_menu = (
            get_building_month_df(
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
            )
        )
        if "0" == dto.entry_draft_flag:

            # 事業所年度別DF
            get_building_year_df(
                conn,
                basic_df,
                monthlyBuildingEnergyAggregation_df,
                supplier_name,
                supply_menu,
            )

            # 企業月別DF
            get_company_month_df(conn, basic_df, monthlyBuildingEnergyAggregation_df)

            # 企業年度別DF
            get_company_year_df(conn, basic_df, monthlyBuildingEnergyAggregation_df)

        # KPI処理取得して更新する
        #        update_building_info_for_kpi(conn, monthlyBuildingEnergyAggregation_df)

        return

    # except HTTPException as e:
    #     raise e

    except Exception as e:
        conn.rollback()
        logger.info(e)
        raise e


def get_value(
    officeUsedEnergyInfo,
    energyRowData,
    buildingRowData,
    fiscal_year,
    calmst,
    electric_co2_emission_coef,
    nfcmst_sub,
    gas_heat_coeff,
    heatsupply_co2_emission_coef,
):
    """
    熱量、原油、CO2排出量計算
    """
    # 熱量換算エネルギー使用量
    calorificEnergyConsumption = co2EmissionCoefficient = co2EmissionCoefficient_avg = 0
    supplier_nm = None
    menu_nm = None
    # electric_co2_emission_coef = 0
    if officeUsedEnergyInfo is not None:
        # energyRowData['ENERGY_QUANTITY'] = energyRowData['ENERGY_QUANTITY'].replace('', np.nan).fillna(0)
        if (
            energyRowData["ENERGY_QUANTITY_FOR_LAW"] is None
            or energyRowData["ENERGY_QUANTITY_FOR_LAW"] == ""
            or (
                isinstance(energyRowData["ENERGY_QUANTITY_FOR_LAW"], float)
                and math.isnan(energyRowData["ENERGY_QUANTITY_FOR_LAW"])
            )
        ):
            energyRowData["ENERGY_QUANTITY_FOR_LAW"] = 0

        # 都市ガス会社ごと係数取得
        if constants_values.ENERGY_CODE_CITY_GAS == energyRowData["ENERGY_CODE"]:
            calorificEnergyConsumption = ceas.calorieConvert(
                calmst, energyRowData["ENERGY_QUANTITY_FOR_LAW"], gas_heat_coeff
            )
            # calorificEnergyConsumption = ceas.calorieConvert(calmst,
            # energyRowData['ENERGY_QUANTITY'], utils.get_cityGasHeatCoefficient(cgmst, cityGasRegNo, str(fiscal_year)))
            supplier_nm = buildingRowData["CITY_GAS_SUPPLIER_NAME"]
            menu_nm = buildingRowData["CITY_GAS_SUPPLIER_NO"]
        else:
            calorificEnergyConsumption = ceas.calorieConvert(
                calmst,
                energyRowData["ENERGY_QUANTITY_FOR_LAW"],
                officeUsedEnergyInfo["CONVERSION_COEF"],
            )

        # CO2排出量
        if (
            constants_values.ENERGY_CODE_CITY_GAS == energyRowData["ENERGY_CODE"]
            and int(fiscal_year) > 2023
        ):  # 2024年度都市ガス
            co2EmissionCoefficient = ceas.co2EmissionsConvert(
                calmst,
                energyRowData["ENERGY_QUANTITY_FOR_LAW"],
                officeUsedEnergyInfo["ENERGY_CO2_EMISSION_COEF"],
            )
        # 産業用蒸気、産業用以外の蒸気、温水、冷水
        elif (
            constants_values.ENERGY_CODE_INDUSTRIAL_STEAM
            == energyRowData["ENERGY_CODE"]
            or constants_values.ENERGY_CODE_INDUSTRIAL_EXCEPT_STEAM
            == energyRowData["ENERGY_CODE"]
            or constants_values.ENERGY_CODE_HOT_WATER == energyRowData["ENERGY_CODE"]
            or constants_values.ENERGY_CODE_COLD_WATER == energyRowData["ENERGY_CODE"]
        ):

            co2EmissionCoefficient = ceas.co2EmissionsConvert(
                calmst,
                energyRowData["ENERGY_QUANTITY_FOR_LAW"],
                heatsupply_co2_emission_coef,
            )
            supplier_nm = buildingRowData["HEAT_SUPPLIER_NAME"]
            menu_nm = buildingRowData["HEAT_SUPPLIER_NO"]
        # 電力の場合
        elif (
            constants_values.ENERGY_CODE_ELECTRIC_POWER_2022
            == energyRowData["ENERGY_CODE"]
            or constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
            == energyRowData["ENERGY_CODE"]
        ):  # 電力
            supplier_nm = buildingRowData["ELECTRICITY_SUPPLIER_NAME"]
            menu_nm = buildingRowData["ELECTRICITY_CONTRACT_MENU"]
            # electric_co2_emission_coef = utils.get_co2EmissionCoefficient(ec_mst,electricPowerCorporateCode, electricPowerMenuNo, electricPowerMenuNm, str(fiscal_year))
            co2EmissionCoefficient = ceas.co2ElectricCoefficient(
                calmst,
                energyRowData["ENERGY_QUANTITY_FOR_LAW"],
                electric_co2_emission_coef,
            )
            co2EmissionCoefficient_avg = ceas.co2ElectricCoefficient(
                calmst,
                energyRowData["ENERGY_QUANTITY_FOR_LAW"],
                float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]),
            )
        else:
            coefficient = ceas.co2ElectricExceptCoefficient(
                calmst,
                officeUsedEnergyInfo["CONVERSION_COEF"],
                officeUsedEnergyInfo["ENERGY_CO2_EMISSION_COEF"],
            )
            co2EmissionCoefficient = ceas.co2EmissionsConvert(
                calmst, energyRowData["ENERGY_QUANTITY_FOR_LAW"], coefficient
            )

    return (
        calorificEnergyConsumption,
        co2EmissionCoefficient,
        co2EmissionCoefficient_avg,
        supplier_nm,
        menu_nm,
    )


def get_building_month_entity(
    session: scoped_session,
    basic_df,
    energyRowData,
    officeUsedEnergyInfo,
    electric_co2_emission_coef,
    supplier_name,
    supply_menu,
    supplier_change_state,
    gas_heat_coeff,
    heatsupply_co2_emission_coef,
    national_average_factor,
    heat_adjusted_emission_factor,
):
    insert_flag = basic_df["INSERT_FLAG"].iloc[0]
    tMBEA = None
    new_insert = False

    target_year_month = str(energyRowData["YEAR"]) + str(energyRowData["MONTH"]).zfill(
        2
    )
    registration_seq = int(basic_df["REGISTRATION_SEQ"].iloc[0])
    new_supplier_reg_no = energyRowData["SUPPLIER_REG_NO"]
    updated_by = basic_df["CREATED_BY"].iloc[0]
    building_id = energyRowData["BUILDING_ID"]

    if (
        energyRowData["ENERGY_CODE"] == constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
        or energyRowData["ENERGY_CODE"]
        == constants_values.ENERGY_CODE_ELECTRIC_POWER_2022
    ) and new_supplier_reg_no != "REENE":
        # ★ DB見ない：初回 or (building_id/new_supplier_reg_no変化) のときだけ実行
        if (not insert_flag) and should_soft_delete_electric_supplier_by_param(
            state=supplier_change_state,
            building_id=building_id,
            new_supplier_reg_no=new_supplier_reg_no,
        ):
            soft_delete_old_supplier_rows(
                session=session,
                basic_df=basic_df,
                building_id=building_id,
                target_year_month=target_year_month,
                registration_seq=registration_seq,
                new_supplier_reg_no=new_supplier_reg_no,
                updated_by=updated_by,
            )

    # フラグで、レコードを作成か照会するのを決める
    if not insert_flag:
        tMBEA = (
            session.query(TMonthlyBuildingEnergyAggregation)
            .filter(
                TMonthlyBuildingEnergyAggregation.corporate_number
                == basic_df["CORPORATE_NUMBER"].iloc[0],  # 法人番号
                TMonthlyBuildingEnergyAggregation.agreement_category
                == basic_df["AGREEMENT_CATEGORY"].iloc[0],  # 同意者取得経路
                TMonthlyBuildingEnergyAggregation.org_id
                == basic_df["ORG_ID"].iloc[0],  # 組織ID
                TMonthlyBuildingEnergyAggregation.building_id
                == energyRowData["BUILDING_ID"],  # 拠点ID
                TMonthlyBuildingEnergyAggregation.energy_code
                == energyRowData["ENERGY_CODE"],  # エネルギーコード
                TMonthlyBuildingEnergyAggregation.target_year_month
                == str(energyRowData["YEAR"])
                + str(energyRowData["MONTH"]).zfill(2),  # 対象年+対象月
                TMonthlyBuildingEnergyAggregation.registration_seq
                == int(basic_df["REGISTRATION_SEQ"].iloc[0]),  # 登録回数
                TMonthlyBuildingEnergyAggregation.supplier_reg_no
                == energyRowData["SUPPLIER_REG_NO"],
            )
            .first()
        )
        if tMBEA:
            tMBEA.updated_by = basic_df["CREATED_BY"].iloc[0]

    if not tMBEA:
        tMBEA = TMonthlyBuildingEnergyAggregation()
        new_insert = True

        tMBEA.corporate_number = basic_df["CORPORATE_NUMBER"].iloc[0]  # 法人番号
        tMBEA.agreement_category = basic_df["AGREEMENT_CATEGORY"].iloc[
            0
        ]  # 同意者取得経路
        tMBEA.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
        tMBEA.building_id = energyRowData["BUILDING_ID"]  # 拠点ID
        tMBEA.energy_code = energyRowData["ENERGY_CODE"]  # エネルギーコード
        tMBEA.target_year_month = str(energyRowData["YEAR"]) + str(
            energyRowData["MONTH"]
        ).zfill(
            2
        )  # 対象年+対象月
        tMBEA.registration_seq = int(basic_df["REGISTRATION_SEQ"].iloc[0])  # 登録回数
        tMBEA.supplier_reg_no = energyRowData["SUPPLIER_REG_NO"]
        tMBEA.created_by = basic_df["CREATED_BY"].iloc[0]

    tMBEA.fiscal_year = str(basic_df["FISCAL_YEAR"].iloc[0])  # 対象年度
    tMBEA.entry_draft_flag = basic_df["ENTRY_DRAFT_FLAG"].iloc[0]  # 登録下書区分
    tMBEA.building_name = energyRowData["BUILDING_NAME"]  # 拠点名
    if energyRowData["ENERGY_NAME_JP"] == "再エネ発電（自家消費）":
        tMBEA.energy_category_name = "電気"
    else:
        tMBEA.energy_category_name = energyRowData["ENERGY_NAME_JP"]  # エネルギー名称
    tMBEA.temperature_corp = utils.nan_to_zero(
        energyRowData["TEMPERATURE_CORP"]
    )  # 本社温度
    tMBEA.temperature_building = utils.nan_to_zero(
        energyRowData["TEMPERATURE_BUILDING"]
    )  # 拠点温度
    tMBEA.energy_quantity = energyRowData["ENERGY_QUANTITY"]  # 年度エネルギー使用量
    tMBEA.energy_quantity_for_report = energyRowData[
        "ENERGY_QUANTITY_FOR_REPORT"
    ]  # 年度エネルギー使用量(レポート)
    tMBEA.energy_quantity_for_law = energyRowData[
        "ENERGY_QUANTITY_FOR_LAW"
    ]  # 年度エネルギー使用量(省エネ)
    tMBEA.energy_unit_original = energyRowData[
        "ENERGY_UNIT_ORIGINAL"
    ]  # 年度エネルギー単位
    tMBEA.energy_unit_for_report = energyRowData[
        "ENERGY_UNIT_FOR_REPORT"
    ]  # 年度エネルギー単位(レポート)
    tMBEA.energy_unit_for_law = energyRowData[
        "ENERGY_UNIT_FOR_LAW"
    ]  # 年度エネルギー単位(省エネ)
    tMBEA.supplier_reg_no = energyRowData["SUPPLIER_REG_NO"]
    area = safe_pos_float(energyRowData.get("BUILDING_AREA"))

    # 分子側の安全化（None/NaN → 0.0）
    qty_law_raw = energyRowData.get("ENERGY_QUANTITY_FOR_LAW")
    qty_law = 0.0 if qty_law_raw is None or pd.isna(qty_law_raw) else float(qty_law_raw)
    cal_energy_raw = energyRowData.get("CALORIFIC_ENERGY_CONSUMPTION")
    cal_energy = (
        0.0
        if cal_energy_raw is None or pd.isna(cal_energy_raw)
        else float(cal_energy_raw)
    )
    co2_coef = energyRowData.get("CO2_EMISSION_COEFFICIENT")
    if isinstance(co2_coef, tuple):  # タプル化対策
        co2_coef = co2_coef[0]
    co2_coef_val = None if co2_coef is None or pd.isna(co2_coef) else float(co2_coef)

    # 面積が妥当なら割り算、妥当でなければ None（算出不能）
    tMBEA.energy_usage_area_unit = (
        float(qty_law / area) if area is not None else None
    )  # エネルギー使用量原単位
    tMBEA.heat_converted_energy_usage = cal_energy
    tMBEA.heat_converted_energy_usage_area_unit = (
        float(cal_energy / area) if area is not None else None
    )  # 熱量換算エネルギー使用量
    if tMBEA.supplier_reg_no == "REENE":
        tMBEA.co2_adjusted_emissions_area_unit = tMBEA.co2_adjusted_emissions = 0
    else:
        tMBEA.co2_adjusted_emissions = co2_coef_val
        tMBEA.co2_adjusted_emissions_area_unit = (
            float(co2_coef_val / area)
            if (area is not None and co2_coef_val is not None)
            else None
        )  # Co2調整後排出量原単位
        tMBEA.supplier_name = supplier_name
        tMBEA.supply_menu = supply_menu
    energy_unit_for_law = (
        None if officeUsedEnergyInfo is None else officeUsedEnergyInfo["UNIT"],
    )  # エネルギー単位
    if energyRowData["ENERGY_CODE"].startswith("9900"):
        tMBEA.energy_name_for_coefficient_matching = energyRowData[
            "ENERGY_NAME_JP"
        ]  # 9900はエネルギー名称で係数マッチング
    else:
        tMBEA.energy_name_for_coefficient_matching = officeUsedEnergyInfo[
            "MINOR_CATEGORY_NM"
        ]  # 省エネ法名称
    tMBEA.heat_conversion_coefficient = (
        None
        if officeUsedEnergyInfo is None
        or officeUsedEnergyInfo["CONVERSION_COEF"] is None
        else float(officeUsedEnergyInfo["CONVERSION_COEF"])
    )  # 熱量換算係数
    if (
        energyRowData["ENERGY_CODE"] == constants_values.ENERGY_CODE_CITY_GAS
    ):  # 東京カス換算係数
        tMBEA.heat_conversion_coefficient = gas_heat_coeff

    if energyRowData["ENERGY_CODE"] == constants_values.ENERGY_CODE_ELECTRIC_POWER_2023:
        tMBEA.co2_adjusted_emission_factor = (
            None
            if electric_co2_emission_coef is None
            else float(electric_co2_emission_coef)
        )
        tMBEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_ELECTRIC
        )
    elif (
        constants_values.ENERGY_CODE_INDUSTRIAL_STEAM == energyRowData["ENERGY_CODE"]
        or constants_values.ENERGY_CODE_INDUSTRIAL_EXCEPT_STEAM
        == energyRowData["ENERGY_CODE"]
        or constants_values.ENERGY_CODE_HOT_WATER == energyRowData["ENERGY_CODE"]
        or constants_values.ENERGY_CODE_COLD_WATER == energyRowData["ENERGY_CODE"]
    ):
        tMBEA.co2_adjusted_emission_factor = (
            None
            if heatsupply_co2_emission_coef is None
            else float(heatsupply_co2_emission_coef)
        )
        tMBEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC
            if constants_values.ENERGY_CODE_INDUSTRIAL_STEAM
            == energyRowData["ENERGY_CODE"]
            else constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_HEAT
        )
    elif energyRowData["ENERGY_CODE"] == "9900011002":
        tMBEA.co2_adjusted_emission_factor = (
            None if national_average_factor is None else float(national_average_factor)
        )
        tMBEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_NFCFIT
        )
    elif energyRowData["ENERGY_CODE"] == "9900011006":
        tMBEA.co2_adjusted_emission_factor = (
            None
            if heat_adjusted_emission_factor is None
            else float(heat_adjusted_emission_factor)
        )
        tMBEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_HSM
        )
    else:
        coef = (
            None
            if officeUsedEnergyInfo is None
            else officeUsedEnergyInfo.get("ENERGY_CO2_EMISSION_COEF")
        )
        tMBEA.co2_adjusted_emission_factor = None if coef is None else float(coef)
        tMBEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_HEAT
            if energyRowData["ENERGY_CODE"].startswith("03")
            else constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC
        )
    tMBEA.heat_conversion_coefficient_source = (
        constants_values.HEAT_CONVERSION_COEFFICIENT_SOURCE
    )

    tMBEA.delete_flg = False
    tMBEA.heat_converted_energy_usage = cal_energy
    tMBEA.energy_unit_for_law = energy_unit_for_law
    tMBEA.heat_converted_energy_unit = constants_values.HEAT_CONVERTED_ENERGY_UNIT
    tMBEA.co2_adjusted_emissions_unit = constants_values.CO2_ADJUSTED_EMISSIONS_UNIT

    if energyRowData["ENERGY_CODE"].startswith("9900"):
        tMBEA.credit_certificate_purchase_energy_amount = energyRowData[
            "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT"
        ]
        tMBEA.credit_certificate_purchase_tco2_amount = energyRowData[
            "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT"
        ]
        tMBEA.credit_certificate_unit = energyRowData["CREDIT_CERTIFICATE_UNIT"]
        tMBEA.co2_adjusted_emissions = energyRowData["CO2_ADJUSTED_EMISSIONS"]
        tMBEA.energy_quantity = energyRowData["ENERGY_QUANTITY"]
        tMBEA.energy_quantity_for_report = energyRowData["ENERGY_QUANTITY_FOR_REPORT"]
        tMBEA.energy_quantity_for_law = energyRowData["ENERGY_QUANTITY_FOR_LAW"]
        tMBEA.energy_unit_original = energyRowData["ENERGY_UNIT_ORIGINAL"]
        tMBEA.energy_unit_for_report = energyRowData["ENERGY_UNIT_FOR_REPORT"]
        tMBEA.energy_unit_for_law = energyRowData["ENERGY_UNIT_FOR_LAW"]

    if isinstance(cal_energy, tuple):
        tMBEA.heat_converted_energy_usage = cal_energy[0]
    if isinstance(energyRowData["CO2_EMISSION_COEFFICIENT"], tuple):
        tMBEA.co2_adjusted_emissions = energyRowData["CO2_EMISSION_COEFFICIENT"][0]
    if isinstance(energy_unit_for_law, tuple):
        tMBEA.energy_unit_for_law = energy_unit_for_law[0]

    if new_insert:
        session.add(tMBEA)

    return tMBEA, supplier_name, supply_menu


# 面積の安全化（None/空/NaN/非数/<=0 を検知）
def safe_pos_float(v):
    try:
        f = float(v)
        return f if f > 0 and not pd.isna(f) else None
    except Exception:
        return None


def get_building_annual_entity(
    session: scoped_session, basic_df, row, supplier_name, supply_menu
):

    insert_flag = basic_df["INSERT_FLAG"].iloc[0]
    tABEA = None
    new_insert = False

    # フラグで、レコードを作成か照会するのを決める
    if not insert_flag:
        tABEA = (
            session.query(TAnnualBuildingEnergyAggregation)
            .filter(
                TAnnualBuildingEnergyAggregation.corporate_number
                == basic_df["CORPORATE_NUMBER"].iloc[0],  # 法人番号
                TAnnualBuildingEnergyAggregation.agreement_category
                == basic_df["AGREEMENT_CATEGORY"].iloc[0],  # 同意者取得経路
                TAnnualBuildingEnergyAggregation.org_id
                == basic_df["ORG_ID"].iloc[0],  # 組織ID
                TAnnualBuildingEnergyAggregation.building_id
                == row["BUILDING_ID"],  # 拠点ID
                TAnnualBuildingEnergyAggregation.energy_code
                == row["ENERGY_CODE"],  # エネルギーコード
                TAnnualBuildingEnergyAggregation.target_year
                == str(basic_df["FISCAL_YEAR"].iloc[0]),
                TAnnualBuildingEnergyAggregation.fiscal_year
                == str(basic_df["FISCAL_YEAR"].iloc[0]),
                TAnnualBuildingEnergyAggregation.registration_seq
                == int(basic_df["REGISTRATION_SEQ"].iloc[0]),  # 登録回数
                TAnnualBuildingEnergyAggregation.supplier_reg_no
                == row["SUPPLIER_REG_NO"],
            )
            .first()
        )
        if tABEA:
            tABEA.updated_by = basic_df["CREATED_BY"].iloc[0]

    if not tABEA:
        tABEA = TAnnualBuildingEnergyAggregation()
        new_insert = True

        tABEA.corporate_number = basic_df["CORPORATE_NUMBER"].iloc[0]  # 法人番号
        tABEA.agreement_category = basic_df["AGREEMENT_CATEGORY"].iloc[
            0
        ]  # 同意者取得経路
        tABEA.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
        tABEA.building_id = row["BUILDING_ID"]  # 拠点ID
        tABEA.energy_code = row["ENERGY_CODE"]  # エネルギーコード
        tABEA.target_year = str(basic_df["FISCAL_YEAR"].iloc[0])
        tABEA.fiscal_year = tABEA.target_year
        tABEA.registration_seq = int(basic_df["REGISTRATION_SEQ"].iloc[0])  # 登録回数
        tABEA.supplier_reg_no = row["SUPPLIER_REG_NO"]

        tABEA.created_by = basic_df["CREATED_BY"].iloc[0]

    # tABEA.entry_draft_flag = basic_df['ENTRY_DRAFT_FLAG'].iloc[0]                                         #登録下書区分
    tABEA.building_name = row["BUILDING_NAME"]  # 拠点名
    tABEA.energy_category_name = row["ENERGY_CATEGORY_NAME"]  # エネルギー名称
    tABEA.energy_quantity = row["ENERGY_QUANTITY"]  # 年度エネルギー使用量
    tABEA.energy_quantity_for_report = row[
        "ENERGY_QUANTITY_FOR_REPORT"
    ]  # 年度エネルギー使用量(レポート)
    tABEA.energy_quantity_for_law = row[
        "ENERGY_QUANTITY_FOR_LAW"
    ]  # 年度エネルギー使用量(省エネ)
    tABEA.energy_unit_original = row["ENERGY_UNIT_ORIGINAL"]  # 年度エネルギー単位
    tABEA.energy_unit_for_report = row[
        "ENERGY_UNIT_FOR_REPORT"
    ]  # 年度エネルギー単位(レポート)
    tABEA.energy_unit_for_law = row["ENERGY_UNIT_FOR_LAW"]  # 年度エネルギー単位(省エネ)
    tABEA.heat_converted_energy_usage = float(
        row["HEAT_CONVERTED_ENERGY_USAGE"]
    )  # 熱量換算エネルギー使用量
    tABEA.co2_adjusted_emissions = float(row["CO2_ADJUSTED_EMISSIONS"])  # co2排出量
    tABEA.energy_name_for_coefficient_matching = row[
        "ENERGY_NAME_FOR_COEFFICIENT_MATCHING"
    ]  # 省エネ法名称
    # tABEA.heat_conversion_coefficient = row['HEAT_CONVERSION_COEFFICIENT']
    # tABEA.co2_adjusted_emission_factor = row['CO2_ADJUSTED_EMISSION_FACTOR']
    if row["ENERGY_CODE"] == "0200010011":
        tABEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_ELECTRIC
        )
    else:
        tABEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC
        )
    tABEA.heat_conversion_coefficient_source = (
        constants_values.HEAT_CONVERSION_COEFFICIENT_SOURCE
    )
    tABEA.credit_certificate_purchase_energy_amount = row[
        "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT"
    ]
    tABEA.credit_certificate_purchase_tco2_amount = row[
        "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT"
    ]
    tABEA.delete_flg = False

    if new_insert:
        session.add(tABEA)

    return tABEA


def get_company_month_entity(session: scoped_session, basic_df, row):

    insert_flag = basic_df["INSERT_FLAG"].iloc[0]
    tMCEA = None
    new_insert = False

    # フラグで、レコードを作成か照会するのを決める

    if not insert_flag:
        tMCEA = (
            session.query(TMonthlyCorporateEnergyAggregation)
            .filter(
                TMonthlyCorporateEnergyAggregation.corporate_number
                == basic_df["CORPORATE_NUMBER"].iloc[0],  # 法人番号
                TMonthlyCorporateEnergyAggregation.agreement_category
                == basic_df["AGREEMENT_CATEGORY"].iloc[0],  # 同意者取得経路
                TMonthlyCorporateEnergyAggregation.org_id
                == basic_df["ORG_ID"].iloc[0],  # 組織ID
                TMonthlyCorporateEnergyAggregation.energy_code
                == row["ENERGY_CODE"],  # エネルギーコード
                TMonthlyCorporateEnergyAggregation.target_year_month
                == row["TARGET_YEAR_MONTH"],
                TMonthlyCorporateEnergyAggregation.registration_seq
                == int(basic_df["REGISTRATION_SEQ"].iloc[0]),  # 登録回数
            )
            .first()
        )
        if tMCEA:
            tMCEA.updated_by = basic_df["CREATED_BY"].iloc[0]

    if not tMCEA:
        tMCEA = (
            session.query(TMonthlyCorporateEnergyAggregation)
            .filter(
                TMonthlyCorporateEnergyAggregation.corporate_number
                == basic_df["CORPORATE_NUMBER"].iloc[0],  # 法人番号
                TMonthlyCorporateEnergyAggregation.agreement_category
                == basic_df["AGREEMENT_CATEGORY"].iloc[0],  # 同意者取得経路
                TMonthlyCorporateEnergyAggregation.org_id
                == basic_df["ORG_ID"].iloc[0],  # 組織ID
                TMonthlyCorporateEnergyAggregation.energy_code
                == row["ENERGY_CODE"],  # エネルギーコード
                TMonthlyCorporateEnergyAggregation.target_year_month
                == row["TARGET_YEAR_MONTH"],
                TMonthlyCorporateEnergyAggregation.registration_seq
                == int(basic_df["REGISTRATION_SEQ"].iloc[0]),  # 登録回数
            )
            .first()
        )

        if tMCEA:
            tMCEA.updated_by = basic_df["CREATED_BY"].iloc[0]
        else:
            tMCEA = TMonthlyCorporateEnergyAggregation()
            new_insert = True
            tMCEA.corporate_number = basic_df["CORPORATE_NUMBER"].iloc[0]  # 法人番号
            tMCEA.agreement_category = basic_df["AGREEMENT_CATEGORY"].iloc[
                0
            ]  # 同意者取得経路
            tMCEA.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
            tMCEA.energy_code = row["ENERGY_CODE"]  # エネルギーコード
            tMCEA.target_year_month = row["TARGET_YEAR_MONTH"]  # 対象年+対象月
            tMCEA.registration_seq = int(
                basic_df["REGISTRATION_SEQ"].iloc[0]
            )  # 登録回数
            tMCEA.created_by = basic_df["CREATED_BY"].iloc[0]

    # tMCEA.entry_draft_flag = basic_df['ENTRY_DRAFT_FLAG'].iloc[0]             #登録下書区分
    tMCEA.energy_category_name = row["ENERGY_CATEGORY_NAME"]  # エネルギー名称
    tMCEA.energy_usage_area_unit = float(
        row["ENERGY_USAGE_AREA_UNIT"]
    )  # 年度エネルギー使用量原単位
    tMCEA.energy_quantity = None  # 年度エネルギー使用量
    tMCEA.fiscal_year = str(basic_df["FISCAL_YEAR"].iloc[0])
    tMCEA.energy_quantity_for_report = row[
        "ENERGY_QUANTITY_FOR_REPORT"
    ]  # 年度エネルギー使用量(レポート)
    tMCEA.energy_quantity_for_law = row[
        "ENERGY_QUANTITY_FOR_LAW"
    ]  # 年度エネルギー使用量(省エネ)
    tMCEA.energy_unit_original = None  # 年度エネルギー単位
    tMCEA.energy_unit_for_report = row[
        "ENERGY_UNIT_FOR_REPORT"
    ]  # 年度エネルギー単位(レポート)
    tMCEA.energy_unit_for_law = row["ENERGY_UNIT_FOR_LAW"]  # 年度エネルギー単位(省エネ)
    tMCEA.heat_converted_energy_usage = float(
        row["HEAT_CONVERTED_ENERGY_USAGE"]
    )  # 熱量換算エネルギー使用量
    # tMCEA.heat_converted_energy_usage_last_year = round(row['HEAT_CONVERTED_ENERGY_USAGE_LAST_YEAR'], 4) #熱量換算エネルギー使用量
    tMCEA.heat_converted_energy_usage_area_unit = float(
        row["HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT"]
    )  # 熱量換算面積単位使用量
    tMCEA.co2_adjusted_emissions = float(row["CO2_ADJUSTED_EMISSIONS"])  # co2排出量
    # tMCEA.co2_adjusted_emissions_last_year = round(row['CO2_ADJUSTED_EMISSIONS_LAST_YEAR'], 4)           #前年度co2排出量
    tMCEA.co2_adjusted_emissions_area_unit = float(
        row["CO2_ADJUSTED_EMISSIONS_AREA_UNIT"]
    )  # CO2排出面積単位使用量
    tMCEA.heat_conversion_coefficient = row["HEAT_CONVERSION_COEFFICIENT"]
    # tMCEA.co2_adjusted_emission_factor = row['CO2_ADJUSTED_EMISSION_FACTOR']
    if row["ENERGY_CODE"] == "0200010011":
        tMCEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_ELECTRIC
        )
    else:
        tMCEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC
        )
    tMCEA.heat_conversion_coefficient_source = (
        constants_values.HEAT_CONVERSION_COEFFICIENT_SOURCE
    )
    tMCEA.energy_name_for_coefficient_matching = row[
        "ENERGY_NAME_FOR_COEFFICIENT_MATCHING"
    ]  # 省エネ法名称
    tMCEA.credit_certificate_purchase_energy_amount = row[
        "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT"
    ]
    tMCEA.credit_certificate_purchase_tco2_amount = row[
        "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT"
    ]
    tMCEA.heat_converted_energy_unit = constants_values.HEAT_CONVERTED_ENERGY_UNIT
    tMCEA.co2_adjusted_emissions_unit = constants_values.CO2_ADJUSTED_EMISSIONS_UNIT
    tMCEA.delete_flg = False
    tMCEA.supply_menu = row["SUPPLY_MENU"]

    if new_insert:
        session.add(tMCEA)

    return tMCEA


def get_company_annual_entity(session: scoped_session, basic_df, row):

    insert_flag = basic_df["INSERT_FLAG"].iloc[0]
    tACEA = None
    new_insert = False

    # フラグで、レコードを作成か照会するのを決める
    if not insert_flag:
        tACEA = (
            session.query(TAnnualCorporateEnergyAggregation)
            .filter(
                TAnnualCorporateEnergyAggregation.corporate_number
                == basic_df["CORPORATE_NUMBER"].iloc[0],  # 法人番号
                TAnnualCorporateEnergyAggregation.agreement_category
                == basic_df["AGREEMENT_CATEGORY"].iloc[0],  # 同意者取得経路
                TAnnualCorporateEnergyAggregation.org_id
                == basic_df["ORG_ID"].iloc[0],  # 組織ID
                TAnnualCorporateEnergyAggregation.energy_code
                == row["ENERGY_CODE"],  # エネルギーコード
                TAnnualCorporateEnergyAggregation.target_year
                == str(basic_df["FISCAL_YEAR"].iloc[0]),
                TAnnualCorporateEnergyAggregation.fiscal_year
                == str(basic_df["FISCAL_YEAR"].iloc[0]),
                TAnnualCorporateEnergyAggregation.registration_seq
                == int(basic_df["REGISTRATION_SEQ"].iloc[0]),  # 登録回数
            )
            .first()
        )
        if tACEA:
            tACEA.updated_by = basic_df["CREATED_BY"].iloc[0]

    if not tACEA:
        tACEA = TAnnualCorporateEnergyAggregation()
        new_insert = True

        tACEA.corporate_number = basic_df["CORPORATE_NUMBER"].iloc[0]  # 法人番号
        tACEA.agreement_category = basic_df["AGREEMENT_CATEGORY"].iloc[
            0
        ]  # 同意者取得経路
        tACEA.org_id = basic_df["ORG_ID"].iloc[0]  # 組織ID
        tACEA.energy_code = row["ENERGY_CODE"]  # エネルギーコード
        tACEA.target_year = str(basic_df["FISCAL_YEAR"].iloc[0])
        tACEA.fiscal_year = tACEA.target_year
        tACEA.registration_seq = int(basic_df["REGISTRATION_SEQ"].iloc[0])  # 登録回数

        tACEA.created_by = basic_df["CREATED_BY"].iloc[0]

    # tACEA.entry_draft_flag = basic_df['ENTRY_DRAFT_FLAG'].iloc[0]             #登録下書区分
    tACEA.energy_category_name = row["ENERGY_CATEGORY_NAME"]  # エネルギー名称
    tACEA.energy_quantity = None  # 年度エネルギー使用量
    tACEA.energy_quantity_for_report = row[
        "ENERGY_QUANTITY_FOR_REPORT"
    ]  # 年度エネルギー使用量(レポート)
    tACEA.energy_quantity_for_law = row[
        "ENERGY_QUANTITY_FOR_LAW"
    ]  # 年度エネルギー使用量(省エネ)
    tACEA.energy_unit_original = None  # 年度エネルギー単位
    tACEA.energy_unit_for_report = row[
        "ENERGY_UNIT_FOR_REPORT"
    ]  # 年度エネルギー単位(レポート)
    tACEA.energy_unit_for_law = row["ENERGY_UNIT_FOR_LAW"]  # 年度エネルギー単位(省エネ)
    tACEA.heat_converted_energy_usage = float(
        row["HEAT_CONVERTED_ENERGY_USAGE"]
    )  # 熱量換算エネルギー使用量
    tACEA.co2_adjusted_emissions = float(row["CO2_ADJUSTED_EMISSIONS"])  # co2排出量
    # tACEA.heat_conversion_coefficient = row['HEAT_CONVERSION_COEFFICIENT']
    # tACEA.co2_adjusted_emission_factor = row['CO2_ADJUSTED_EMISSION_FACTOR']
    tACEA.energy_name_for_coefficient_matching = row[
        "ENERGY_NAME_FOR_COEFFICIENT_MATCHING"
    ]  # 省エネ法名称
    if row["ENERGY_CODE"] == "0200010011":
        tACEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_ELECTRIC
        )
    else:
        tACEA.co2_adjusted_emission_factor_source = (
            constants_values.CO2_ADJUSTED_EMISSION_FACTOR_SOURCE_EXCEPT_ELECTRIC
        )
    tACEA.heat_conversion_coefficient_source = (
        constants_values.HEAT_CONVERSION_COEFFICIENT_SOURCE
    )
    tACEA.credit_certificate_purchase_energy_amount = row[
        "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT"
    ]
    tACEA.credit_certificate_purchase_tco2_amount = row[
        "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT"
    ]
    tACEA.delete_flg = False

    if new_insert:
        session.add(tACEA)

    return tACEA


def get_building_month_df(
    session: scoped_session,
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
):
    """
    建物月別集計データDF取得
    params:
    return:
    """
    hsmst_daitai = hsmst[(hsmst["HEAT_SUPPLIER_CD"] == "H0999")]

    tMBEAs: list[TMonthlyBuildingEnergyAggregation] = []
    # ENERGY_NAME_JPが「電気」の場合、ENERGY_CODEを設定
    df_energyInfo["ENERGY_CODE"] = df_energyInfo["ENERGY_NAME_JP"].map(
        lambda x: constants_colums.enery_code_mapping.get(x, None)
    )

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
    # df_wdimst['MONTH'] = df_wdimst['TEMPERATURE_CORP'].fillna(0).astype(float)

    # 本社気温マージ
    df_energyInfo = df_energyInfo.merge(
        df_wdimst[["YEAR", "MONTH", "TEMPERATURE_CORP"]],
        on=["YEAR", "MONTH"],
        how="left",  # left join：df_energyInfoの行を維持
    )

    # エネルギー最小年月取得
    df_energyInfo["NEW_YEAR_MONTH"] = str(df_energyInfo["YEAR"].iloc[0]) + str(
        df_energyInfo["MONTH"].iloc[0]
    )
    min_value = df_energyInfo["NEW_YEAR_MONTH"].astype(int).min()
    min_month = str(min_value)[4:]

    # 4月より小さい場合、前年度とする
    # if int(min_month) < 4:
    #     basic_df["FISCAL_YEAR"] = int(str(min_value)[:4]) -1
    # else:
    basic_df["FISCAL_YEAR"] = int(str(min_value)[:4])

    # 空文字をNaNに変換
    df_energyInfo["UNIT_ORIGIN"].replace("", pd.NA, inplace=True)
    # NaN（None 含む）の行を削除
    df_energyInfo = df_energyInfo.dropna(subset=["UNIT_ORIGIN"])
    # 単位統一にする
    df_energyInfo = df_energyInfo.groupby("ENERGY_CODE", group_keys=False).apply(
        energy_unit_standardization
    )

    # #証書クレジット
    # df_others_energy = df_energyInfo[df_energyInfo['ENERGY_CODE'].str.startswith("9900")]
    # #証書クレジット以外
    # df_energyInfo = df_energyInfo[~df_energyInfo['ENERGY_CODE'].str.startswith("9900")]

    # 変換fataframe
    conv_df = pd.DataFrame(
        constants_colums.conversion_data, columns=["UNIT_ORIGIN", "TARGET_UNIT", "COEF"]
    )

    df_energyInfo = standard_unit(ccmst, df_energyInfo, conv_df)

    # gas_row = gasmst.loc[gasmst["city_gas_supplier_code"] == "G0999", "heat_conversion_coefficient"]
    gas_row = gasmst.loc[
        gasmst["CITY_GAS_SUPPLIER_CODE"] == "G0999", "HEAT_CONVERSION_COEFFICIENT"
    ]
    gas_heat_coeff = float(gas_row.iloc[0]) if not gas_row.empty else 40

    supplier_change_state = SupplierChangeState()

    # 建物月別DF
    for index, energyRowData in df_energyInfo.iterrows():
        # 初期化
        calorificEnergyConsumption = co2EmissionCoefficient_avg = (
            co2EmissionCoefficient
        ) = buildingArea = electric_co2_emission_coef = heatsupply_co2_emission_coef = 0

        calorificEnergyConsumption_2023 = co2EmissionCoefficient_2013 = 0

        nfcmst_sub = 0

        supplier_name = supply_menu = heat_adjusted_emission_factor = (
            national_average_factor
        ) = None

        try:
            # 係数年度
            emission_coef_year = None
            emission_coef_month = str(energyRowData["YEAR"]) + "4"
            input_month = str(energyRowData["YEAR"]) + str(energyRowData["MONTH"])
            # 月の年ごとに係数情報取得
            if int(input_month) < int(emission_coef_month):
                emission_coef_year = energyRowData["YEAR"]
            else:
                emission_coef_year = energyRowData["YEAR"] + 1
            # エネルギー値0へ変換
            if bool(energyRowData["ENERGY_QUANTITY"]) is False:
                energyRowData["ENERGY_QUANTITY"] = 0

            # 電力会社名、建物面積取得
            buildingRowData = get_electric_company_buildingarea(
                df_buildingInfo, energyRowData
            )

            energy_code = str(energyRowData["ENERGY_CODE"])

            if energy_code.startswith("02"):
                key = "ELECTRICITY_SUPPLIER_NO"
            elif energy_code.startswith("03"):
                key = "HEAT_SUPPLIER_NO"
            elif energy_code == "0100230000":
                key = "CITY_GAS_SUPPLIER_NO"
            else:
                key = None

            supplier_reg_no = buildingRowData[key] if key else None

            if energy_code == "9900010001":
                # 再エネ発電（自家消費）の場合
                supplier_reg_no = "REENE"
                energyRowData["ENERGY_CODE"] = "0200010011"

            energyRowData["SUPPLIER_REG_NO"] = (
                supplier_reg_no if supplier_reg_no else "0"
            )

            # 2023年度以前で電気の場合、電気エネルギーコード変更
            # if int(emission_coef_year) < 2024 and energyRowData["ENERGY_NAME_JP"] == constants_values.ELECTRIC_POWER_NAME:
            #     energyRowData["ENERGY_CODE"] = constants_values.ENERGY_CODE_ELECTRIC_POWER_2022

            # 証書クレジット以外
            if not energyRowData["ENERGY_CODE"].startswith("9900"):
                # 換算係数マスタから処理中エネルギーデータを取得する(DataFrame型)
                officeUsedEnergyInfo = get_office_usedenergy_info(
                    ccmst, energyRowData, emission_coef_year
                )

                if officeUsedEnergyInfo is None:
                    abort(
                        412,
                        description="換算係数マスタ情報取得は失敗しました。"
                        + energyRowData["ENERGY_CODE"],
                    )

            electricPowerCorporateCode = buildingRowData["ELECTRIC_COMPANY_REG_NO"]
            electricPowerSupplierName = buildingRowData["ELECTRICITY_SUPPLIER_NAME"]
            electricPowerMenuNm = buildingRowData["ELECTRICITY_CONTRACT_MENU"]
            buildingArea = buildingRowData["GROSS_FLOOR_AREA"]
            buildingAddressPrefecture = buildingRowData["BUILDING_ADDRESS_PREFECTURE"]

            energyRowData["BUILDING_AREA"] = buildingArea

            if buildingAddressPrefecture in df_wdimst.columns:
                # if "TEMPERATURE_BUILDING" in df_wdimst.columns:
                #     df_wdimst.drop(columns=["TEMPERATURE_BUILDING"], inplace=True)
                df_wdimst = df_wdimst.rename(
                    columns={
                        buildingAddressPrefecture: "TEMPERATURE_BUILDING_"
                        + buildingAddressPrefecture
                    }
                )
            else:
                if (
                    not "TEMPERATURE_BUILDING_" + buildingAddressPrefecture
                    in df_wdimst.columns
                ):
                    df_wdimst["TEMPERATURE_BUILDING_" + buildingAddressPrefecture] = (
                        df_wdimst["TEMPERATURE_CORP"]
                    )

            df_wdimst_sub = df_wdimst[
                (df_wdimst["YEAR"] == energyRowData["YEAR"])
                & (df_wdimst["MONTH"] == energyRowData["MONTH"])
            ]
            if df_wdimst_sub.empty:
                energyRowData["TEMPERATURE_BUILDING"] = None
            else:
                energyRowData["TEMPERATURE_BUILDING"] = df_wdimst_sub[
                    "TEMPERATURE_BUILDING_" + buildingAddressPrefecture
                ].iloc[0]

            nfcmst_sub = nfcmst[nfcmst["REPORT_YEAR"] == str(emission_coef_year)]
            nfcmst_sub = nfcmst_sub[nfcmst_sub["FOSSIL_FREE_CERT_TYPE_ID"] == "1"]
            if nfcmst_sub.empty:
                nfcmst_sub = nfcmst.loc[nfcmst["REPORT_YEAR"].idxmax()]
                if nfcmst_sub["FOSSIL_FREE_CERT_TYPE_ID"] == "1":
                    nfcmst_sub = nfcmst_sub

            # 電力会社係数取得
            if (
                constants_values.ENERGY_CODE_ELECTRIC_POWER_2022
                == energyRowData["ENERGY_CODE"]
                or constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
                == energyRowData["ENERGY_CODE"]
            ):  # 電力
                electricPowerMenuNo = buildingRowData["ELECTRICITY_CONTRACT_MENU"]
                electric_co2_emission_coef = utils.get_co2EmissionCoefficient(
                    ecmst,
                    electricPowerCorporateCode,
                    electricPowerMenuNo,
                    electricPowerMenuNm,
                    str(emission_coef_year),
                    nfcmst_sub,
                    isBank=True,
                )

            # 熱供給事業者別の調整後排出係数係数取得
            if (
                constants_values.ENERGY_CODE_INDUSTRIAL_STEAM
                == energyRowData["ENERGY_CODE"]
            ):  # 産業用蒸気
                heatsupply_co2_emission_coef = (
                    None
                    if officeUsedEnergyInfo is None
                    else officeUsedEnergyInfo.get("ENERGY_CO2_EMISSION_COEF")
                )
            elif (
                constants_values.ENERGY_CODE_INDUSTRIAL_EXCEPT_STEAM
                == energyRowData["ENERGY_CODE"]
                or constants_values.ENERGY_CODE_HOT_WATER
                == energyRowData["ENERGY_CODE"]
                or constants_values.ENERGY_CODE_COLD_WATER
                == energyRowData["ENERGY_CODE"]
            ):
                heatsupply_co2_emission_coef = utils.get_heatSupplyHeatCoefficient(
                    hsmst,
                    energyRowData.SUPPLIER_REG_NO,
                    None,
                    None,
                    emission_coef_year,
                    nfcmst_sub,
                    False,
                )

            # 月単位の年の対象外エネルギーを外す
            if energyRowData["ENERGY_QUANTITY"] != 0 and bool(
                energyRowData["ENERGY_QUANTITY"]
            ):
                if not energyRowData["ENERGY_CODE"].startswith("9900"):
                    energyRowData["ENERGY_QUANTITY_FOR_REPORT"] = calc_report(
                        energyRowData
                    )
                    energyRowData["ENERGY_QUANTITY_FOR_LAW"] = calc_law(energyRowData)

                    # 熱量、原油、CO2排出量換算
                    (
                        calorificEnergyConsumption,
                        co2EmissionCoefficient,
                        co2EmissionCoefficient_avg,
                        supplier_nm,
                        menu_nm,
                    ) = get_value(
                        officeUsedEnergyInfo,
                        energyRowData,
                        buildingRowData,
                        emission_coef_year,
                        calmst,
                        electric_co2_emission_coef,
                        nfcmst_sub,
                        gas_heat_coeff,
                        heatsupply_co2_emission_coef,
                    )

                    supplier_name = supplier_nm
                    supply_menu = menu_nm

                elif energyRowData["ENERGY_CODE"].startswith("9900"):
                    # CO2値
                    co2EmissionCoefficient = energyRowData["ENERGY_QUANTITY"]
                    # 電力の場合
                    if energyRowData["ENERGY_CODE"] == "9900011002":

                        energyRowData["ENERGY_UNIT_FOR_LAW"] = "千KWh"
                        energyRowData["ENERGY_UNIT_ORIGINAL"] = energyRowData[
                            "ENERGY_UNIT_FOR_REPORT"
                        ] = "kWh"
                        national_average_factor = nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]
                        # 電力値の計算
                        energyRowData["ENERGY_QUANTITY_FOR_LAW"] = (
                            float(co2EmissionCoefficient)
                            / float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"])
                            / 1000
                        )
                        energyRowData["ENERGY_QUANTITY_FOR_REPORT"] = energyRowData[
                            "ENERGY_QUANTITY"
                        ] = float(co2EmissionCoefficient) / float(
                            nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]
                        )

                    # CO2の場合
                    elif energyRowData["ENERGY_CODE"] == "9900011006":
                        # 電力値の計算
                        hsmst_daitai["REPORT_YEAR"] = hsmst_daitai[
                            "REPORT_YEAR"
                        ].astype(int)
                        available_years = hsmst_daitai["REPORT_YEAR"].unique()

                        # emission_coef_year が存在しない場合 → 最も近い年度に差し替え
                        if emission_coef_year not in available_years:
                            available_years = np.asarray(available_years, dtype=int)
                            emission_coef_year = int(emission_coef_year)

                            nearest_year = available_years[
                                np.abs(available_years - emission_coef_year).argmin()
                            ]
                        else:
                            nearest_year = emission_coef_year

                        # 最終的に nearest_year を使って値を取得
                        heat_adjusted_emission_factor = hsmst_daitai.loc[
                            hsmst_daitai["REPORT_YEAR"] == nearest_year,
                            "ADJUSTED_EMISSION_FACTOR",
                        ].iloc[0]

                        energyRowData["ENERGY_QUANTITY_FOR_LAW"] = round(
                            co2EmissionCoefficient
                            / float(heat_adjusted_emission_factor),
                            4,
                        )
                        energyRowData["ENERGY_UNIT_ORIGINAL"] = energyRowData[
                            "ENERGY_UNIT_FOR_REPORT"
                        ] = energyRowData["ENERGY_UNIT_FOR_LAW"] = "GJ"

                        energyRowData["ENERGY_QUANTITY"] = energyRowData[
                            "ENERGY_QUANTITY_FOR_REPORT"
                        ] = round(
                            co2EmissionCoefficient
                            / float(heat_adjusted_emission_factor),
                            4,
                        )

                    # その他証書の場合
                    elif energyRowData["ENERGY_CODE"] == "9900011009":
                        energyRowData["ENERGY_QUANTITY_FOR_REPORT"] = energyRowData[
                            "ENERGY_QUANTITY_FOR_LAW"
                        ] = None

                    energyRowData["CREDIT_CERTIFICATE_UNIT"] = "t-CO2"
                    energyRowData["CO2_ADJUSTED_EMISSIONS"] = co2EmissionCoefficient

                    if not buildingArea and co2EmissionCoefficient:
                        # Co2調整後排出量原単位
                        energyRowData["CO2_ADJUSTED_EMISSIONS_AREA_UNIT"] = (
                            (co2EmissionCoefficient / buildingArea)
                            if (
                                buildingArea is not None
                                and buildingArea > 0
                                and co2EmissionCoefficient is not None
                            )
                            else None
                        )

                    energyRowData["CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT"] = (
                        co2EmissionCoefficient
                    )
                    if energyRowData["ENERGY_CODE"] == "9900011009":
                        # その他の証書・クレジットの場合、使用量への変換は実施しない為、「0」が設定
                        energyRowData["CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT"] = 0
                    else:
                        energyRowData["CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT"] = (
                            energyRowData["ENERGY_QUANTITY"]
                        )

            else:
                energyRowData["ENERGY_QUANTITY_FOR_REPORT"] = 0
                energyRowData["ENERGY_QUANTITY_FOR_LAW"] = 0
                energyRowData["CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT"] = None
                energyRowData["CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT"] = None
                energyRowData["CREDIT_CERTIFICATE_UNIT"] = "t-CO2"
                energyRowData["CO2_ADJUSTED_EMISSIONS"] = 0
                if energyRowData["ENERGY_CODE"] == "9900011002":
                    energyRowData["ENERGY_UNIT_ORIGINAL"] = "千KWh"
                    energyRowData["ENERGY_UNIT_FOR_REPORT"] = energyRowData[
                        "ENERGY_UNIT_FOR_LAW"
                    ] = "kWh"
                elif energyRowData["ENERGY_CODE"] == "9900011006":
                    energyRowData["ENERGY_UNIT_ORIGINAL"] = energyRowData[
                        "ENERGY_UNIT_FOR_REPORT"
                    ] = energyRowData["ENERGY_UNIT_FOR_LAW"] = "GJ"

            # スコープバリュー設定
            # set_scope_value(energyRowData)

            # Nan値を0に変更
            calorificEnergyConsumption = (
                0
                if math.isnan(calorificEnergyConsumption)
                else calorificEnergyConsumption
            )
            co2EmissionCoefficient_avg = (
                0
                if math.isnan(co2EmissionCoefficient_avg)
                else co2EmissionCoefficient_avg
            )
            co2EmissionCoefficient = (
                0 if math.isnan(co2EmissionCoefficient) else co2EmissionCoefficient
            )

            calorificEnergyConsumption_2023 = (
                0
                if math.isnan(calorificEnergyConsumption_2023)
                else calorificEnergyConsumption_2023
            )
            co2EmissionCoefficient_2013 = (
                0
                if math.isnan(co2EmissionCoefficient_2013)
                else co2EmissionCoefficient_2013
            )

            # TABLEAU表示のため、エネルギーコード統一にする
            if energyRowData["ENERGY_CODE"] == "0200010001":
                energyRowData["ENERGY_CODE"] = "0200010011"

            energyRowData["CALORIFIC_ENERGY_CONSUMPTION"] = calorificEnergyConsumption
            energyRowData["CO2_EMISSION_COEFFICIENT"] = co2EmissionCoefficient
            energyRowData["CALORIFIC_ENERGY_CONSUMPTION_2023"] = (
                calorificEnergyConsumption_2023
            )
            energyRowData["CO2_EMISSION_COEFFICIENT_2013"] = co2EmissionCoefficient_2013
            energyRowData["CO2_EMISSION_COEFFICIENT_AVG"] = co2EmissionCoefficient_avg
            energyRowData["CO2_EMISSION_COEFFICIENT"] = co2EmissionCoefficient

            # 建物月別集計データEntity取得
            tMonthlyBuildingEnergyAggregation, supplier_name, supply_menu = (
                get_building_month_entity(
                    session,
                    basic_df,
                    energyRowData,
                    officeUsedEnergyInfo,
                    electric_co2_emission_coef,
                    supplier_name,
                    supply_menu,
                    supplier_change_state,
                    gas_heat_coeff,
                    heatsupply_co2_emission_coef,
                    national_average_factor,
                    heat_adjusted_emission_factor,
                )
            )

            # リストに集計済エネルギー情報格納
            tMBEAs.append(tMonthlyBuildingEnergyAggregation)

        except Exception as e:
            session.rollback()
            abort(500, description="システムエラーが発生しました。")

    # 存在しない 建物とエネルギーの組合せ を削除
    combos = (
        df_energyInfo[["BUILDING_ID", "ENERGY_CODE"]].drop_duplicates().values.tolist()
    )

    session.query(TMonthlyBuildingEnergyAggregation).filter(
        TMonthlyBuildingEnergyAggregation.corporate_number
        == tMBEAs[0].corporate_number,
        TMonthlyBuildingEnergyAggregation.agreement_category
        == tMBEAs[0].agreement_category,
        TMonthlyBuildingEnergyAggregation.org_id == tMBEAs[0].org_id,
        TMonthlyBuildingEnergyAggregation.fiscal_year == tMBEAs[0].fiscal_year,
        TMonthlyBuildingEnergyAggregation.registration_seq
        == tMBEAs[0].registration_seq,
        ~tuple_(
            TMonthlyBuildingEnergyAggregation.building_id,
            TMonthlyBuildingEnergyAggregation.energy_code,
        ).in_(combos),
    ).delete(synchronize_session=False)

    # 集計済みエネルギー情報登録
    monthlyBuildingEnergyAggregation_df = pd.DataFrame(
        [
            {
                col.name: getattr(row, col.name)
                for col in TMonthlyBuildingEnergyAggregation.__table__.columns
            }
            for row in tMBEAs
        ]
    )
    # カラム統一で大文字にする
    monthlyBuildingEnergyAggregation_df.columns = (
        monthlyBuildingEnergyAggregation_df.columns.str.upper()
    )

    return monthlyBuildingEnergyAggregation_df, supplier_name, supply_menu


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
        if energy_code == "9900010001":
            group["ENERGY_UNIT_FOR_REPORT"] = "kWh"
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

    # 再エネ発電（自家消費）（ENERGY_CODE: 9900010001）に対してマスタデータがなめ、手動で設定
    df_energyInfo.loc[
        df_energyInfo["ENERGY_CODE"] == "9900010001", "ENERGY_UNIT_FOR_LAW"
    ] = "千kWh"

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
    df_energyInfo = (
        df_energyInfo.merge(
            conv_df,
            how="left",
            left_on=["UNIT_ORIGIN", "ENERGY_UNIT_FOR_LAW"],
            right_on=["UNIT_ORIGIN", "TARGET_UNIT"],
        )
        .rename(columns={"COEF": "COEF_LAW"})
        .drop(columns=["TARGET_UNIT"])
    )

    return df_energyInfo


# REPORT の変換
def calc_report(row):
    if pd.notnull(row["COEF_REPORT"]):
        return row["ENERGY_QUANTITY"] * row["COEF_REPORT"]
    else:
        return None


# LAW の変換
def calc_law(row):
    if pd.notnull(row["COEF_LAW"]):
        return row["ENERGY_QUANTITY"] * row["COEF_LAW"]
    else:
        return None


def get_building_year_df(
    session: scoped_session,
    basic_df,
    monthlyBuildingEnergyAggregation_df,
    supplier_name,
    supply_menu,
):
    """
    建物年別集計データDF取得
    params:
    return:
    """
    tABEAs: list[TAnnualBuildingEnergyAggregation] = []
    officeYearly_grouped_df = (
        monthlyBuildingEnergyAggregation_df.groupby(
            [
                "FISCAL_YEAR",
                "ENERGY_CODE",
                "BUILDING_NAME",
                "ENERGY_CATEGORY_NAME",
                "ENERGY_UNIT_FOR_LAW",
                "ENERGY_UNIT_FOR_REPORT",
                "BUILDING_ID",
                "SUPPLIER_REG_NO",
                # "ENERGY_NAME_FOR_COEFFICIENT_MATCHING",
            ],
            dropna=False,
        )
        .agg(
            ENERGY_UNIT_ORIGINAL=("ENERGY_UNIT_ORIGINAL", "first"),
            ENERGY_QUANTITY=("ENERGY_QUANTITY", "sum"),
            ENERGY_QUANTITY_FOR_LAW=("ENERGY_QUANTITY_FOR_LAW", "sum"),
            ENERGY_QUANTITY_FOR_REPORT=("ENERGY_QUANTITY_FOR_REPORT", "sum"),
            ENERGY_USAGE_AREA_UNIT=("ENERGY_USAGE_AREA_UNIT", "sum"),
            HEAT_CONVERTED_ENERGY_USAGE=("HEAT_CONVERTED_ENERGY_USAGE", "sum"),
            HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT=(
                "HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT",
                "sum",
            ),
            CO2_ADJUSTED_EMISSIONS_AREA_UNIT=(
                "CO2_ADJUSTED_EMISSIONS_AREA_UNIT",
                "sum",
            ),
            CO2_ADJUSTED_EMISSIONS=("CO2_ADJUSTED_EMISSIONS", "sum"),
            CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT=(
                "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT",
                "sum",
            ),
            CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT=(
                "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT",
                "sum",
            ),
            ENERGY_NAME_FOR_COEFFICIENT_MATCHING=(
                "ENERGY_NAME_FOR_COEFFICIENT_MATCHING",
                "last",
            ),
        )
        .reset_index()
    )

    # CO2排出量ランキング計算
    area_emissions_rank = (
        officeYearly_grouped_df.groupby("BUILDING_ID")[
            "CO2_ADJUSTED_EMISSIONS_AREA_UNIT"
        ]
        .sum()
        .rank(method="first", ascending=False)
        .astype(int)
    )

    # officeYearly_df = make_df_columns(constants_colums.officeYearly_columns, officeYearly_grouped_df)

    for index, row in officeYearly_grouped_df.iterrows():

        tAnnualBuildingEnergyAggregation = get_building_annual_entity(
            session, basic_df, row, supplier_name, supply_menu
        )
        # リストに集計済エネルギー情報格納
        tABEAs.append(tAnnualBuildingEnergyAggregation)

    # 存在しない 建物とエネルギーの組合せ を削除
    combos = (
        officeYearly_grouped_df[["BUILDING_ID", "ENERGY_CODE"]]
        .drop_duplicates()
        .values.tolist()
    )

    session.query(TAnnualBuildingEnergyAggregation).filter(
        TAnnualBuildingEnergyAggregation.corporate_number == tABEAs[0].corporate_number,
        TAnnualBuildingEnergyAggregation.agreement_category
        == tABEAs[0].agreement_category,
        TAnnualBuildingEnergyAggregation.org_id == tABEAs[0].org_id,
        TAnnualBuildingEnergyAggregation.target_year == tABEAs[0].target_year,
        TAnnualBuildingEnergyAggregation.fiscal_year == tABEAs[0].fiscal_year,
        TAnnualBuildingEnergyAggregation.registration_seq == tABEAs[0].registration_seq,
        ~tuple_(
            TAnnualBuildingEnergyAggregation.building_id,
            TAnnualBuildingEnergyAggregation.energy_code,
        ).in_(combos),
    ).delete(synchronize_session=False)


def get_company_month_df(
    session: scoped_session, basic_df, monthlyBuildingEnergyAggregation_df
):
    """
    企業月別集計データDF取得
    params:
    return:
    """
    tMCEAs: list[TMonthlyCorporateEnergyAggregation] = []
    # corporateMonthly_grouped_df = monthlyBuildingEnergyAggregation_df.groupby(
    #     ['ENERGY_CODE',
    #      'ENERGY_CATEGORY_NAME',
    #      'ENERGY_UNIT_FOR_LAW',
    #      'ENERGY_UNIT_FOR_REPORT',
    #      'TARGET_YEAR_MONTH',
    #      'HEAT_CONVERSION_COEFFICIENT',
    #      "ENERGY_NAME_FOR_COEFFICIENT_MATCHING",
    #      "ENERGY_UNIT_ORIGINAL",
    #      "SUPPLY_MENU"
    #      ])\
    #     [['ENERGY_QUANTITY','ENERGY_QUANTITY_FOR_LAW','ENERGY_QUANTITY_FOR_REPORT', 'ENERGY_USAGE_AREA_UNIT', 'HEAT_CONVERTED_ENERGY_USAGE','HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT',\
    #       'CO2_ADJUSTED_EMISSIONS_AREA_UNIT','CO2_ADJUSTED_EMISSIONS', 'CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT', 'CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT']].sum().reset_index()
    group_cols = [
        "ENERGY_CODE",
        "ENERGY_CATEGORY_NAME",
        "ENERGY_UNIT_FOR_LAW",
        "ENERGY_UNIT_FOR_REPORT",
        "TARGET_YEAR_MONTH",
        # 'HEAT_CONVERSION_COEFFICIENT',
        "ENERGY_NAME_FOR_COEFFICIENT_MATCHING",
    ]

    def unique_or_first(s):
        u = s.dropna().unique()
        return u[0] if len(u) >= 1 else None

    agg_dict = {
        "ENERGY_QUANTITY_FOR_LAW": "sum",
        "ENERGY_QUANTITY_FOR_REPORT": "sum",
        "ENERGY_USAGE_AREA_UNIT": "sum",
        "HEAT_CONVERTED_ENERGY_USAGE": "sum",
        "HEAT_CONVERTED_ENERGY_USAGE_AREA_UNIT": "sum",
        "CO2_ADJUSTED_EMISSIONS_AREA_UNIT": "sum",
        "CO2_ADJUSTED_EMISSIONS": "sum",
        "CREDIT_CERTIFICATE_PURCHASE_ENERGY_AMOUNT": "sum",
        "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT": "sum",
        "SUPPLY_MENU": unique_or_first,
        "HEAT_CONVERSION_COEFFICIENT": "last",
    }

    corporateMonthly_grouped_df = (
        monthlyBuildingEnergyAggregation_df.groupby(group_cols, dropna=False)
        .agg(agg_dict)
        .reset_index()
    )

    # CO2排出量ランキング計算
    monthly_emissions_rank = (
        corporateMonthly_grouped_df.groupby("TARGET_YEAR_MONTH")[
            "CO2_ADJUSTED_EMISSIONS"
        ]
        .sum()
        .rank(method="first", ascending=False)
        .astype(int)
    )

    for index, row in corporateMonthly_grouped_df.iterrows():

        corporationMonthlyEntity = get_company_month_entity(session, basic_df, row)
        # リストに集計済エネルギー情報格納
        tMCEAs.append(corporationMonthlyEntity)

    # 存在しないエネルギーを削除
    energy_cds = corporateMonthly_grouped_df["ENERGY_CODE"].drop_duplicates().tolist()

    session.query(TMonthlyCorporateEnergyAggregation).filter(
        TMonthlyCorporateEnergyAggregation.corporate_number
        == tMCEAs[0].corporate_number,
        TMonthlyCorporateEnergyAggregation.agreement_category
        == tMCEAs[0].agreement_category,
        TMonthlyCorporateEnergyAggregation.org_id == tMCEAs[0].org_id,
        TMonthlyCorporateEnergyAggregation.target_year_month
        == tMCEAs[0].target_year_month,
        TMonthlyCorporateEnergyAggregation.registration_seq
        == tMCEAs[0].registration_seq,
        ~TMonthlyCorporateEnergyAggregation.energy_code.in_(energy_cds),
        # ~tuple_(
        #     TMonthlyBuildingEnergyAggregation.energy_code
        # ).in_(energy_cds)
    ).delete(synchronize_session=False)


def get_company_year_df(
    session: scoped_session, basic_df, monthlyBuildingEnergyAggregation_df
):
    """
    企業年別集計データDF取得
    params:
    return:
    """
    tACEAs: list[TAnnualCorporateEnergyAggregation] = []
    #'HEAT_CONVERSION_COEFFICIENT', 'CO2_ADJUSTED_EMISSION_FACTOR'
    group_cols = [
        "ENERGY_CODE",
        "ENERGY_CATEGORY_NAME",
        "ENERGY_UNIT_FOR_LAW",
        "ENERGY_UNIT_FOR_REPORT",
        # "ENERGY_NAME_FOR_COEFFICIENT_MATCHING",
        # "ENERGY_UNIT_ORIGINAL"
    ]
    agg_dict = {
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
        "ENERGY_NAME_FOR_COEFFICIENT_MATCHING": "last",
    }
    corporateYearly_grouped_df = (
        monthlyBuildingEnergyAggregation_df.groupby(group_cols, dropna=False)
        .agg(agg_dict)
        .reset_index()
    )
    for index, row in corporateYearly_grouped_df.iterrows():
        tAnnualCorporateEnergyAggregation = get_company_annual_entity(
            session, basic_df, row
        )
        # リストに集計済エネルギー情報格納
        tACEAs.append(tAnnualCorporateEnergyAggregation)

    # 存在しないエネルギーを削除
    energy_cds = corporateYearly_grouped_df["ENERGY_CODE"].drop_duplicates().tolist()

    session.query(TAnnualCorporateEnergyAggregation).filter(
        TAnnualCorporateEnergyAggregation.corporate_number
        == tACEAs[0].corporate_number,
        TAnnualCorporateEnergyAggregation.agreement_category
        == tACEAs[0].agreement_category,
        TAnnualCorporateEnergyAggregation.org_id == tACEAs[0].org_id,
        TAnnualCorporateEnergyAggregation.target_year == tACEAs[0].target_year,
        TAnnualCorporateEnergyAggregation.fiscal_year == tACEAs[0].fiscal_year,
        TAnnualCorporateEnergyAggregation.registration_seq
        == tACEAs[0].registration_seq,
        ~TAnnualCorporateEnergyAggregation.energy_code.in_(energy_cds),
        # ~tuple_(
        #     TMonthlyBuildingEnergyAggregation.energy_code
        # ).in_(energy_cds)
    ).delete(synchronize_session=False)


def get_electric_company_buildingarea(df_buildingInfo, energyRowData):

    for index, buildingRowData in df_buildingInfo.iterrows():

        if buildingRowData["BUILDING_ID"] == energyRowData["BUILDING_ID"]:
            return buildingRowData


def get_office_usedenergy_info(ccmst, energyRowData, emission_coef_year):
    # 2023年度以前で電気の場合、電気エネルギーコード変更
    if (
        int(emission_coef_year) < 2024
        and energyRowData["ENERGY_CODE"]
        == constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
    ):
        energyCode = constants_values.ENERGY_CODE_ELECTRIC_POWER_2022
    else:
        energyCode = energyRowData["ENERGY_CODE"]

    if "ENERGY_CODE" not in ccmst.columns:
        ccmst["ENERGY_CODE"] = (
            ccmst["MAJOR_CATEGORY_ID"].astype(str)
            + ccmst["MIDDLE_CATEGORY_ID"].astype(str)
            + ccmst["MINOR_CATEGORY_ID"].astype(str)
        )

    ccmst_sub = ccmst[ccmst["ENERGY_CODE"].astype(str) == str(energyCode)]
    if ccmst_sub.empty:
        return None

    # 同一年度のデータがある場合はそれを優先して返す
    ccmst_sub_same_year = ccmst_sub[
        ccmst_sub["REPORT_YEAR"].astype(str) == str(emission_coef_year)
    ]
    if not ccmst_sub_same_year.empty:
        return ccmst_sub_same_year.iloc[0]

    # 同一年度のデータがない場合は、emission_coef_year に最も近い年度のデータを返す
    ccmst_sub["YEAR_DIFF"] = (
        ccmst_sub["REPORT_YEAR"]
        .astype(int)
        .apply(lambda x: abs(x - int(emission_coef_year)))
    )
    ccmst_sub = ccmst_sub.sort_values(by="YEAR_DIFF").drop(columns=["YEAR_DIFF"])
    return ccmst_sub.iloc[0]


def _to_df(query_result, upper=False):
    if not query_result:
        return pd.DataFrame()
    row = query_result[0]
    if hasattr(row, "_fields"):  # namedtuple形式
        df = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in query_result
            ]
        )
    else:
        df = pd.DataFrame(
            [
                {col.name: getattr(row, col.name) for col in row.__table__.columns}
                for row in query_result
            ]
        )
    return df.rename(columns=str.upper) if upper else df


def soft_delete_old_supplier_rows(
    session: scoped_session,
    basic_df,
    building_id: str,
    target_year_month: str,
    registration_seq: int,
    new_supplier_reg_no: str,
    updated_by: str,
):
    """
    同一(法人/同意/組織/拠点/年月/登録回数) で supplier_reg_no が異なる既存行を論理削除する。
    ※主キーに supplier_reg_no が含まれるため、変更時は旧行をdelete_flg=Trueにする。
    """
    q = session.query(TMonthlyBuildingEnergyAggregation).filter(
        TMonthlyBuildingEnergyAggregation.corporate_number
        == basic_df["CORPORATE_NUMBER"].iloc[0],
        TMonthlyBuildingEnergyAggregation.agreement_category
        == basic_df["AGREEMENT_CATEGORY"].iloc[0],
        TMonthlyBuildingEnergyAggregation.org_id == basic_df["ORG_ID"].iloc[0],
        TMonthlyBuildingEnergyAggregation.building_id == building_id,
        # TMonthlyBuildingEnergyAggregation.target_year_month == target_year_month,
        TMonthlyBuildingEnergyAggregation.registration_seq == registration_seq,
        TMonthlyBuildingEnergyAggregation.delete_flg == False,
        TMonthlyBuildingEnergyAggregation.supplier_reg_no != new_supplier_reg_no,
        TMonthlyBuildingEnergyAggregation.energy_code == "0200010011",
    )

    old_rows = q.all()
    for r in old_rows:
        r.delete_flg = True
        r.updated_by = updated_by


@dataclass
class SupplierChangeState:
    initialized: bool = False
    prev_building_id: Optional[str] = None
    prev_supplier_reg_no: Optional[str] = None


def should_soft_delete_electric_supplier_by_param(
    state: SupplierChangeState,
    building_id: str,
    new_supplier_reg_no: str,
) -> bool:
    """
    DBは見ない。パラメータ変化だけで判定。
    - 初回: True
    - building_id または supplier_reg_no が前回と違う: True
    - それ以外: False
    """
    if not state.initialized:
        state.initialized = True
        state.prev_building_id = building_id
        state.prev_supplier_reg_no = new_supplier_reg_no
        return True  # 初回

    changed = (state.prev_building_id != building_id) or (
        state.prev_supplier_reg_no != new_supplier_reg_no
    )

    state.prev_building_id = building_id
    state.prev_supplier_reg_no = new_supplier_reg_no
    return changed


# def undelete_current_supplier_row_electric(
#     session: scoped_session,
#     basic_df,
#     building_id: str,
#     target_year_month: str,
#     registration_seq: int,
#     new_supplier_reg_no: str,
#     updated_by: str,
# ):
#     """
#     電気(0200010011) かつ new_supplier_reg_no の行がもし delete_flg=True でも、
#     必ず delete_flg=False に戻す（初回でも同様）。
#     """
#     row = (
#         session.query(TMonthlyBuildingEnergyAggregation)
#         .filter(
#             TMonthlyBuildingEnergyAggregation.corporate_number == basic_df["CORPORATE_NUMBER"].iloc[0],
#             TMonthlyBuildingEnergyAggregation.agreement_category == basic_df["AGREEMENT_CATEGORY"].iloc[0],
#             TMonthlyBuildingEnergyAggregation.org_id == basic_df["ORG_ID"].iloc[0],
#             TMonthlyBuildingEnergyAggregation.building_id == building_id,
#             TMonthlyBuildingEnergyAggregation.target_year_month == target_year_month,
#             TMonthlyBuildingEnergyAggregation.registration_seq == registration_seq,
#             TMonthlyBuildingEnergyAggregation.energy_code == "0200010011",
#             TMonthlyBuildingEnergyAggregation.supplier_reg_no == new_supplier_reg_no,
#         )
#         .first()
#     )

#     if row:
#         if row.delete_flg:
#             row.delete_flg = False
#         row.updated_by = updated_by
