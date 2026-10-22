from datetime import datetime
from typing import Dict, Optional, Set, Tuple

import pandas as pd
from flask import abort
from flask_jwt_extended import get_jwt
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import scoped_session

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.common.load_master import mst_data
from cndx_corp_back.dto.building.energy_register_in_dto import (
    BuildingEnergyRegisterInDto as InDto,
)
from cndx_corp_back.entity.m_city_gas_heating_value_entity import MCityGasHeatingValue
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.m_electricity_conversion_entity import MElectricityConversion
from cndx_corp_back.entity.m_heat_supplier_menu_entity import MHeatSupplierMenu
from cndx_corp_back.entity.m_jp_st_industry_classification_entity import (
    MJpStIndustryClassification,
)
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo


@component
def dto_to_dfs(dto: InDto, user_context: dict, logger=None):

    basic_dict = {
        "CORPORATE_NUMBER": dto.corporate_number,
        # "fiscal_year": dto.fiscal_year,
        "FILE_ID": None,
        "REPORT_SAVE_PATH": None,
        "REPORT_STATUS": "0",
        "REPORT_CLASSIFY": "01",
        "CREATED_AT": datetime.now(),
        "CREATED_BY": user_context.get("user_id"),
        "UPDATED_AT": None,
        "UPDATED_BY": None,
        "DELETE_FLG": False,
        "REGISTRATION_SEQ": dto.registration_seq,
        "ORG_ID": dto.org_id,
        "AGREEMENT_CATEGORY": dto.agreement_category,
        "GHG_SYSTEM_COMPANY_NAME": None,
        "ENERGY_BENCHMARK_TARGET_INDUSTRY": None,
        "ENERGY_BENCHMARK_INDICATOR": None,
        "ENERGY_BENCHMARK_YEAR": None,
        "ENTRY_DRAFT_FLAG": dto.entry_draft_flag,
        "INSERT_FLAG": dto.insert_flag,
        "FISCAL_YEAR": dto.fiscal_year,
        "REPORT_PERIOD_START_YEAR_MONTH": dto.start_year_month,
        "REPORT_PERIOD_END_YEAR_MONTH": dto.end_year_month,
    }

    basic_df = pd.DataFrame([basic_dict])

    basic_df["ORG_ID"] = user_context.get("org_id")

    try:
        with get_scoped_session() as session:

            if dto.insert_flag:
                # 登録回数を取得
                registration_seq = get_registration_seq(session, basic_df)

                basic_df["REGISTRATION_SEQ"] = registration_seq
                basic_df["NUMBER_REGISTRATIONS"] = registration_seq

            # コード→名称 のマッピングを取得
            mapping_industry_df, mapping_industry_mapping = (
                fetch_industry_classification_info(dto, session)
            )
            # mapping_electric = fetch_electric_company_names(dto, session)
            mapping_city_gas = fetch_city_gas_names(dto, session)
            mapping_heat_supplier = fetch_heat_supplier_names(dto, session)

            # 各コード値の名称を結合
            for info in dto.updated_building_info:
                key = (
                    info.industry_class_major_code,
                    info.industry_class_middle_code,
                    info.industry_class_minor_code,
                    info.industry_class_detail_code,
                )
                if key in mapping_industry_mapping:
                    names = mapping_industry_mapping[key]
                    info.industry_class_major_name = names["industry_class_major_name"]
                    info.industry_class_middle_name = names[
                        "industry_class_middle_name"
                    ]
                    info.industry_class_minor_name = names["industry_class_minor_name"]
                    info.industry_class_detail_name = names[
                        "industry_class_detail_name"
                    ]

                # code_electric = info.electric_company_reg_no
                # if code_electric and code_electric in mapping_electric:
                #     info.electricity_supplier_name = mapping_electric[code_electric]
                code_city_gas = info.city_gas_reg_no
                if code_city_gas and code_city_gas in mapping_city_gas:
                    info.city_gas_supplier_name = mapping_city_gas[code_city_gas]
                code_heat_supply = info.heat_supply_reg_no
                if code_heat_supply and code_heat_supply in mapping_heat_supplier:
                    info.heat_supplier_name = mapping_heat_supplier[code_heat_supply]

            # 登録回数が空の場合 1で登録する(新規登録)
            # if dto.registration_seq is None:
            #     registration_seq = 1
            # # 登録回数が空以外 かつ insert_flagがtrueの場合 +1 する(2回目以降の新規登録)
            # elif dto.registration_seq is not None and dto.insert_flag:
            #     registration_seq = dto.registration_seq + 1
            # # それ以外はそのまま登録(更新処理)
            # else:
            #     registration_seq = dto.registration_seq

            # 年度のインデスク取得
            # col_index = basic_df.columns.get_loc("FISCAL_YEAR")
            # 登録回数の項目と値の差込
            # basic_df.insert(col_index + 1, "REGISTRATION_SEQ", registration_seq)
            # basic_df.insert(col_index + 1, "NUMBER_REGISTRATIONS", registration_seq)

            stmt = (
                select(
                    MCorporateBasic.company_name,
                    MCorporateBasic.company_name.label("CORPORATE_NAME"),
                    MCorporateBasic.company_address_prefecture.label(
                        "ADDRESS_PREFECTURE"
                    ),
                    MCorporateBasic.company_address_city.label("ADDRESS_CITY"),
                    MCorporateDetailsInfo.business_office_count,
                    # MCorporateDetailsInfo.industry_class_major_name,
                    # MCorporateDetailsInfo.industry_class_middle_name,
                    # MCorporateDetailsInfo.industry_class_minor_name,
                    # MCorporateDetailsInfo.industry_class_detail_name,
                    # MCorporateDetailsInfo.industry_class_major_code,
                    # MCorporateDetailsInfo.industry_class_middle_code,
                    # MCorporateDetailsInfo.industry_class_minor_code,
                    # MCorporateDetailsInfo.industry_class_detail_code,
                )
                .join(
                    MCorporateDetailsInfo,
                    MCorporateBasic.corporate_number
                    == MCorporateDetailsInfo.corporate_number,
                )
                .where(
                    MCorporateDetailsInfo.corporate_number == dto.corporate_number,
                    MCorporateDetailsInfo.agreement_category == dto.agreement_category,
                    # MCorporateDetailsInfo.org_id == dto.org_id,
                    MCorporateDetailsInfo.delete_flg.isnot(True),
                )
            )

            corp_res = session.execute(stmt).mappings().first()

    except Exception as e:
        logger.error(f"データベース接続エラー: {str(e)}")
        abort(500)

    if corp_res == None:
        abort(412, description="企業情報が存在しません。")
    corporate_df = pd.DataFrame([dict(corp_res)])

    building_df = pd.DataFrame([bld.model_dump() for bld in dto.updated_building_info])

    # 大文字に変換
    building_df.columns = building_df.columns.str.upper()
    corporate_df.columns = corporate_df.columns.str.upper()

    # DBのカラム名に合わせる
    # building_df = building_df.rename(columns={
    #     "ELECTRIC_COMPANY_REG_NO": "ELECTRICITY_SUPPLIER_NO",
    #     "MENU_NO": "ELECTRICITY_CONTRACT_MENU",
    #     "CITY_GAS_REG_NO": "CITY_GAS_SUPPLIER_NO",
    #     "HEAT_SUPPLY_REG_NO": "HEAT_SUPPLIER_NO",
    # })
    building_df["ELECTRICITY_SUPPLIER_NO"] = building_df["ELECTRIC_COMPANY_REG_NO"]
    building_df["ELECTRICITY_CONTRACT_MENU"] = building_df["MENU_NO"]
    building_df["CITY_GAS_SUPPLIER_NO"] = building_df["CITY_GAS_REG_NO"]
    building_df["HEAT_SUPPLIER_NO"] = building_df["HEAT_SUPPLY_REG_NO"]

    # 可視化側用と作成周りの情報
    building_df["REPORT_SELECTION_PERIOD_FROM"] = "0"
    building_df["FORMAT_TYPE"] = "0"
    building_df["SITE_SELECTION_TYPE"] = "0"
    building_df["REPORT_CREATED_AT"] = None
    building_df["REPORT_CREATED_BY"] = "0"

    # bld_df_dup_droped = building_df.drop(
    #     columns=[
    #        "INDUSTRY_CLASS_MAJOR_CODE",
    #        "INDUSTRY_CLASS_MIDDLE_CODE",
    #        "INDUSTRY_CLASS_MINOR_CODE",
    #        "INDUSTRY_CLASS_DETAIL_CODE",
    #         "REGISTRATION_SEQ",
    #     ]
    # )
    industry_mst_df = mapping_industry_df
    industry_mst_df.columns = [
        "INDUSTRY_CLASS_MAJOR_CODE",
        "INDUSTRY_CLASS_MIDDLE_CODE",
        "INDUSTRY_CLASS_MINOR_CODE",
        "INDUSTRY_CLASS_DETAIL_CODE",
        "INDUSTRY_CLASS_MAJOR_NAME",
        "INDUSTRY_CLASS_MIDDLE_NAME",
        "INDUSTRY_CLASS_MINOR_NAME",
        "INDUSTRY_CLASS_DETAIL_NAME",
    ]

    name_cols = [
        "INDUSTRY_CLASS_MAJOR_NAME",
        "INDUSTRY_CLASS_MIDDLE_NAME",
        "INDUSTRY_CLASS_MINOR_NAME",
        "INDUSTRY_CLASS_DETAIL_NAME",
    ]

    # マスタは必要列だけに絞る
    mst_min = industry_mst_df[["INDUSTRY_CLASS_DETAIL_CODE"] + name_cols]
    # merge: 左(building)はそのまま、右(マスタ)だけ _mst を付与
    bld_comp = building_df.merge(
        mst_min,
        on="INDUSTRY_CLASS_DETAIL_CODE",
        how="left",
        suffixes=("", "_mst"),
        validate="many_to_one",
    )
    # 欠損だけをマスタで補完
    for c in name_cols:
        bld_comp[c] = bld_comp[c].fillna(bld_comp[f"{c}_mst"])
    # 一時列は削除
    bld_comp = bld_comp.drop(columns=[f"{c}_mst" for c in name_cols])

    #    bld_comp = pd.merge(
    #        bld_df_dup_droped,
    #        industry_mst_df,
    #        on="INDUSTRY_CLASS_DETAIL_CODE",
    #        how="left",
    #    )

    repeated_basic_df = pd.concat([basic_df] * len(bld_comp), ignore_index=True)
    repeated_corporate_df = pd.concat([corporate_df] * len(bld_comp), ignore_index=True)

    # basic_df = pd.concat([basic_df, corporate_df], axis=1)
    basic_df = pd.concat([repeated_basic_df, repeated_corporate_df, bld_comp], axis=1)

    energy_df = _get_energy_records(dto, building_df)

    # print(basic_df.head(50).to_dict("records"))

    return {
        "basic_df": basic_df,
        "corporate_df": corporate_df,
        "building_df": building_df,
        "energy_df": energy_df,
    }


def _get_energy_records(dto: InDto, building_df: pd.DataFrame):

    res_list = []

    fiscal_year = dto.fiscal_year

    start_year = int(dto.start_year_month[:4])
    start_month = int(dto.start_year_month[-2:])

    for k, row in building_df.iterrows():

        for ei in row["ENERGY_INFO"]:

            raw_month_idx = start_month - 1

            for eu in ei["energy_quantity"]:

                row_data = {
                    "BUILDING_ID": row["BUILDING_ID"],
                    "BUILDING_NAME": row["BUILDING_NAME"],
                    "ENERGY_CODE": ei["energy_code"],
                    "ENERGY_NAME_JP": ei["energy_name_jp"],
                    "CATEGORY": None,
                    "ENERGY_NAME": None,  # DataFrame 結合
                    "YEAR": start_year + (raw_month_idx) // 12,
                    "MONTH": (raw_month_idx) % 12 + 1,
                    "FISCAL_YEAR": fiscal_year,
                    "ENERGY_QUANTITY": eu,
                    "ENERGY_UNIT_ORIGINAL": ei["energy_unit_original"],
                    "UNIT_ORIGIN": ei["energy_unit_original"],
                }
                res_list.append(row_data)

                raw_month_idx += 1

    building_df.drop(columns=["ENERGY_INFO"], inplace=True)

    return pd.DataFrame(res_list)


def get_registration_seq(conn, basic_df):
    """
    登録回数取得
    """
    # result_df = select_data(conn, condition_list, None, "DB_CORP.T_CN_APPLICATION_INFO")
    max_registration_seq = (
        conn.query(func.max(TCnApplicationInfo.registration_seq))
        .filter(
            TCnApplicationInfo.fiscal_year == basic_df["FISCAL_YEAR"].iloc[0],
            TCnApplicationInfo.corporate_number == basic_df["CORPORATE_NUMBER"].iloc[0],
            #    TCnApplicationInfo.org_id == basic_df["ORG_ID"].iloc[0],
            TCnApplicationInfo.agreement_category
            == basic_df["AGREEMENT_CATEGORY"].iloc[0],
        )
        .all()
    )

    insert_registration_seq = None
    if not max_registration_seq or max_registration_seq[0][0] is None:
        insert_registration_seq = 1
    else:
        insert_registration_seq = max_registration_seq[0][0] + 1

    return insert_registration_seq


def fetch_industry_classification_info(
    dto: InDto, session: scoped_session
) -> Dict[Tuple[str, str, str, str], Dict[str, str]]:
    # まずはコードの組み合わせをセットに集約
    code_quads: Set[
        Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]
    ] = set()
    for info in dto.updated_building_info:
        maj = info.industry_class_major_code
        mid = info.industry_class_middle_code
        grp = info.industry_class_minor_code
        ind = info.industry_class_detail_code

        # major のみ
        code_quads.add((maj, None, None, None))
        # middle があるなら middle まで
        if mid:
            code_quads.add((maj, mid, None, None))
            # minor があるなら minor まで
            if grp:
                code_quads.add((maj, mid, grp, None))
                # detail があるなら detail まで
                if ind:
                    code_quads.add((maj, mid, grp, ind))

    # AND 条件を組み立てて OR でつなぐ
    clauses = []
    for maj, mid, grp, ind in code_quads:
        conds = [MJpStIndustryClassification.division_code == maj]
        if mid is not None:
            conds.append(MJpStIndustryClassification.major_group_code == mid)
        if grp is not None:
            conds.append(MJpStIndustryClassification.group_code == grp)
        if ind is not None:
            conds.append(MJpStIndustryClassification.industry_code == ind)
        clauses.append(and_(*conds))

    stmt = select(
        MJpStIndustryClassification.division_code,
        MJpStIndustryClassification.major_group_code,
        MJpStIndustryClassification.group_code,
        MJpStIndustryClassification.industry_code,
        MJpStIndustryClassification.division_name,
        MJpStIndustryClassification.major_group_name,
        MJpStIndustryClassification.group_name,
        MJpStIndustryClassification.industry_name,
    ).where(or_(*clauses))

    results = session.execute(stmt).all()
    results_df = pd.DataFrame(
        [{field: getattr(row, field) for field in row._fields} for row in results],
        dtype=str,
    )

    # # 取得結果を辞書に詰め替え
    mapping: Dict[Tuple[str, str, str, str], Dict[str, str]] = {}
    for row in results:
        (
            maj_code,
            mid_code,
            grp_code,
            ind_code,
            maj_name,
            mid_name,
            grp_name,
            ind_name,
        ) = row
        key = (maj_code, mid_code, grp_code, ind_code)
        mapping[key] = {
            "industry_class_major_name": maj_name,
            "industry_class_middle_name": mid_name,
            "industry_class_minor_name": grp_name,
            "industry_class_detail_name": ind_name,
        }

        # 下書き保存する場合、grp_codeとind_codeの未選択もあり得るため、
        # maj_code + mid_code と maj_code + mid_code + grp_codeのレコードを追加
        mapping.setdefault(
            (maj_code, mid_code, "", ""),
            {
                "industry_class_major_name": maj_name,
                "industry_class_middle_name": mid_name,
                "industry_class_minor_name": "",
                "industry_class_detail_name": "",
            },
        )

        mapping.setdefault(
            (maj_code, mid_code, grp_code, ""),
            {
                "industry_class_major_name": maj_name,
                "industry_class_middle_name": mid_name,
                "industry_class_minor_name": grp_name,
                "industry_class_detail_name": "",
            },
        )
    return results_df, mapping


def fetch_electric_company_names(dto: InDto, session: scoped_session) -> Dict[str, str]:
    """
    電気事業者名を返す
    """
    # セットで抽出（None/空文字は除外）
    codes = {
        info.electric_company_reg_no
        for info in dto.updated_building_info
        if info.electric_company_reg_no
    }
    if not codes:
        return {}

    # SELECT
    stmt = select(
        MElectricityConversion.electric_company_reg_no,
        MElectricityConversion.electric_supplier_nm,
    ).where(MElectricityConversion.electric_company_reg_no.in_(codes))
    rows = session.execute(stmt).all()

    # {code: name} 辞書化
    return {code: name for code, name in rows}


def fetch_city_gas_names(dto: InDto, session: scoped_session) -> Dict[str, str]:
    """
    都市ガス事業者名を返す
    """
    # セットで抽出（None/空文字は除外）
    codes = {
        info.city_gas_reg_no
        for info in dto.updated_building_info
        if info.city_gas_reg_no
    }
    if not codes:
        return {}

    # SELECT
    stmt = select(
        MCityGasHeatingValue.city_gas_supplier_cd,
        MCityGasHeatingValue.city_gas_supplier_nm,
    ).where(MCityGasHeatingValue.city_gas_supplier_cd.in_(codes))
    rows = session.execute(stmt).all()

    # {code: name} 辞書化
    return {code: name for code, name in rows}


def fetch_heat_supplier_names(dto: InDto, session: scoped_session) -> Dict[str, str]:
    """
    熱事業者名を返す
    """
    # セットで抽出（None/空文字は除外）
    codes = {
        info.heat_supply_reg_no
        for info in dto.updated_building_info
        if info.heat_supply_reg_no
    }
    if not codes:
        return {}

    # SELECT
    stmt = select(
        MHeatSupplierMenu.heat_supplier_cd, MHeatSupplierMenu.heat_supplier_name
    ).where(MHeatSupplierMenu.heat_supplier_cd.in_(codes))
    rows = session.execute(stmt).all()

    # {code: name} 辞書化
    return {code: name for code, name in rows}
