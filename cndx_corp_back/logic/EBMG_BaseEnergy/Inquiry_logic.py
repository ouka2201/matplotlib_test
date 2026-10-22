import os
import traceback
from collections.abc import Mapping
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
from flask import abort, current_app
from sqlalchemy import Integer, and_, cast, func, or_

import cndx_corp_back.logic.EBMG_BaseEnergy.auto_entry_logic as AutoEntryLogic
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_city_gas_heating_value_entity import MCityGasHeatingValue
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.m_electricity_conversion_entity import MElectricityConversion
from cndx_corp_back.entity.m_heat_supplier_menu_entity import MHeatSupplierMenu
from cndx_corp_back.entity.m_jp_st_industry_classification_entity import (
    MJpStIndustryClassification,
)
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.query import common_queries as Queries
from cndx_corp_back.utils.utils import get_message


class BaseEnergyInquiryLogic:
    BUILDING_INFO_MAP = {
        "building_name": "building_name",
        "building_address_prefecture": "building_address_prefecture",
        "building_address_city": "building_address_city",
        "industry_class_major_code": "industry_class_major_code",
        "industry_class_major_name": "industry_class_major_name",
        "industry_class_middle_code": "industry_class_middle_code",
        "industry_class_middle_name": "industry_class_middle_name",
        "industry_class_minor_code": "industry_class_minor_code",
        "industry_class_minor_name": "industry_class_minor_name",
        "industry_class_detail_code": "industry_class_detail_code",
        "industry_class_detail_name": "industry_class_detail_name",
        "gross_floor_area": "gross_floor_area",
        "electricity_supplier_no": "electricity_supplier_no",
        "electricity_supplier_name": "electricity_supplier_name",
        "menu_no": "menu_no",
        "menu_name": "electricity_contract_menu",
        "ep_office_code": "ep_office_code",
        "ep_customer_number": "ep_customer_number",
        "supply_point_number": "supply_point_number",
        "city_gas_supplier_no": "city_gas_supplier_no",
        "city_gas_supplier_name": "city_gas_supplier_name",
        "heat_supplier_no": "heat_supplier_no",
        "heat_supplier_name": "heat_supplier_name",
        "registration_seq": "registration_seq",
    }

    # 新規登録編集のパターン
    @component
    def inquiry_building_mast_map(self, user_context, request_dict: dict, logger=None):
        """
        建物マスタの内容を
        ネストのdictリストにして返す
        """
        logger.info(f"{os.path.basename(__file__)}inquiry_building_mast_map処理開始。")

        login_org_id = user_context.get("org_id")
        org_type_code = user_context.get("org_type_code")
        role_id = user_context.get("role")
        user_id = user_context.get("user_id")

        with get_scoped_session() as session:
            # 建物マスタと企業詳細情報マスタ
            fiscal_year = request_dict.get("start_year_month")[:-2]
            sub_max = (
                session.query(
                    TCnApplicationInfo.corporate_number,
                    # TCnApplicationInfo.org_id,
                    TCnApplicationInfo.agreement_category,
                    func.max(TCnApplicationInfo.registration_seq).label("max_seq"),
                )
                .where(TCnApplicationInfo.fiscal_year == fiscal_year)
                .group_by(
                    TCnApplicationInfo.corporate_number,
                    # TCnApplicationInfo.org_id,
                    TCnApplicationInfo.agreement_category,
                )
            ).subquery()
            qry = (
                session.query(
                    MBuilding.corporate_number,
                    MBuilding.agreement_category,
                    MBuilding.agreement_org.label("org_id"),
                    MBuilding.building_id,
                    MBuilding.location_identifier_name.label("building_name"),
                    MBuilding.building_address_prefecture,
                    MBuilding.building_address_city,
                    MCorporateDetailsInfo.industry_class_major_code,
                    MCorporateDetailsInfo.industry_class_major_name,
                    MCorporateDetailsInfo.industry_class_middle_code,
                    MCorporateDetailsInfo.industry_class_middle_name,
                    MBuilding.ep_office_code,
                    MBuilding.ep_customer_number,
                    MBuilding.supply_point_number,
                    sub_max.c.max_seq.label("registration_seq"),
                )
                .join(
                    MBuilding,
                    and_(
                        MBuilding.corporate_number
                        == MCorporateDetailsInfo.corporate_number,
                        MBuilding.agreement_category
                        == MCorporateDetailsInfo.agreement_category,
                    ),
                )
                .outerjoin(
                    sub_max,
                    and_(
                        sub_max.c.corporate_number == MBuilding.corporate_number,
                        # sub_max.c.org_id == login_org_id,
                        sub_max.c.agreement_category == MBuilding.agreement_category,
                    ),
                )
                # sub_max.c.org_id.in_([MBuilding.agreement_org, login_org_id])),)
                .where(
                    MBuilding.corporate_number == request_dict.get("corporate_number"),
                    MBuilding.agreement_category
                    == request_dict.get("agreement_category"),
                    MBuilding.agreement_org == request_dict.get("org_id"),
                    MBuilding.delete_flg.is_(False),
                    MCorporateDetailsInfo.delete_flg.is_(False),
                )
                .distinct()
                .order_by(MBuilding.building_id.asc())
            )

            # # 金融機関（org_type_code=02/03）：agreement_org で権限制御
            # if org_type_code == "03" or org_type_code == "02":
            #     # Query child organizations for role_id == "9"
            #     child_org_ids = []
            #     if str(role_id) == "9":
            #         role_stmt = Queries.get_user_role(session, user_id, login_org_id, role_id, logger)
            #         df_role = pd.read_sql(role_stmt, session.connection())

            #         if "child_org_id" in df_role.columns:
            #             child_org_ids = (
            #                 df_role["child_org_id"]
            #                     .dropna()
            #                     .astype(str)
            #                     .unique()
            #                     .tolist()
            #             )

            #     # Apply authorization filter: parent + children + request org
            #     if str(role_id) == "9" and child_org_ids:
            #         qry = qry.where(MBuilding.agreement_org.in_([request_dict.get("org_id"), login_org_id] + child_org_ids))
            #     else:
            #         qry = qry.where(MBuilding.agreement_org.in_([request_dict.get("org_id"), login_org_id]))
            # # REP/TCS（org_type_code=04/05）：m_staff_info で権限制御
            # elif org_type_code in ("04", "05"):
            #     from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
            #     staff_exists_subq = (
            #         session.query(1)
            #         .select_from(MStaffInfo)
            #         .where(
            #             MStaffInfo.corporate_number == MBuilding.corporate_number,
            #             MStaffInfo.agreement_category == MBuilding.agreement_category,
            #             MStaffInfo.org_id == login_org_id,
            #             MStaffInfo.delete_flg.is_(False)
            #         )
            #         .exists()
            #     )
            #     qry = qry.where(staff_exists_subq)
            # # 可視化事業者（org_type_code=06）：agreement_org で権限制御
            # elif org_type_code == "06":
            #     qry = qry.where(MBuilding.agreement_org == login_org_id)

            logger.info(f"データ: {qry} ")
            sql = qry.statement.compile(
                dialect=session.connection().dialect,
                compile_kwargs={"literal_binds": True},
            )

            # DataFrame化
            df_parent = pd.read_sql(qry.statement, session.connection()).fillna("")
            children_map = dict()

        # マスタリストは空の場合、エラー返す
        if df_parent.empty:
            abort(412, description=get_message("BUILDING_INFO_NOT_EXSIT"))

        logger.info(f"データ: {df_parent} ")
        logger.info(
            f"{os.path.basename(__file__)}inquiry_building_mast_map結合処理開始。"
        )
        # 結合処理呼び出し
        res = self.combine_building(df_parent, children_map)
        return res

    # 登録済みデータがあるパターン
    @component
    def inquiry_building_info_map(self, user_context, request_dict: dict, logger=None):
        """
        建物情報と月別建物エネルギー集計情報の内容を
        ネストのdictリストにして返す
        """
        logger.info(f"{os.path.basename(__file__)}inquiry_building_info_map処理開始。")

        login_org_id = user_context.get("org_id")
        org_type_code = user_context.get("org_type_code")
        role_id = user_context.get("role")
        user_id = user_context.get("user_id")

        with get_scoped_session() as session:
            # Query child organizations for role_id == "9" (financial institutions only)
            child_org_ids = []
            if org_type_code in ("02", "03") and str(role_id) == "9":
                role_stmt = Queries.get_user_role(
                    session, user_id, login_org_id, role_id, logger
                )
                df_role = pd.read_sql(role_stmt, session.connection())

                if "child_org_id" in df_role.columns:
                    child_org_ids = (
                        df_role["child_org_id"].dropna().astype(str).unique().tolist()
                    )

            # 建物情報とCN対策実施申込情報と電力会社排出係数マスタと建物マスタ
            building_qry = (
                session.query(
                    TBuildingInfo.corporate_number,
                    TBuildingInfo.agreement_category,
                    TBuildingInfo.org_id,
                    TBuildingInfo.building_id,
                    MBuilding.location_identifier_name.label("building_name"),
                    TBuildingInfo.address_prefecture.label(
                        "building_address_prefecture"
                    ),
                    TBuildingInfo.address_city.label("building_address_city"),
                    TBuildingInfo.industry_class_major_code,
                    TBuildingInfo.industry_class_middle_code,
                    TBuildingInfo.industry_class_minor_code,
                    TBuildingInfo.industry_class_detail_code,
                    TBuildingInfo.industry_class_major_name,
                    TBuildingInfo.industry_class_middle_name,
                    TBuildingInfo.industry_class_minor_name,
                    TBuildingInfo.industry_class_detail_name,
                    TBuildingInfo.gross_floor_area,
                    TBuildingInfo.electricity_supplier_no,
                    TBuildingInfo.electricity_supplier_name,
                    TBuildingInfo.electricity_contract_menu,
                    TBuildingInfo.ep_office_code,
                    TBuildingInfo.ep_customer_number,
                    TBuildingInfo.supply_point_number,
                    TBuildingInfo.city_gas_supplier_no,
                    TBuildingInfo.city_gas_supplier_name,
                    TBuildingInfo.heat_supplier_no,
                    TBuildingInfo.heat_supplier_name,
                    TBuildingInfo.registration_seq,
                    TBuildingInfo.created_by,
                )
                .select_from(TCnApplicationInfo)
                .join(
                    TBuildingInfo,
                    and_(
                        TBuildingInfo.corporate_number
                        == TCnApplicationInfo.corporate_number,
                        TBuildingInfo.agreement_category
                        == TCnApplicationInfo.agreement_category,
                        TBuildingInfo.org_id == TCnApplicationInfo.org_id,
                        TBuildingInfo.fiscal_year == TCnApplicationInfo.fiscal_year,
                        TBuildingInfo.registration_seq
                        == TCnApplicationInfo.registration_seq,
                        TBuildingInfo.entry_draft_flag
                        == TCnApplicationInfo.entry_draft_flag,
                        TCnApplicationInfo.report_period_start_year_month
                        == request_dict.get("start_year_month"),
                        TCnApplicationInfo.report_period_end_year_month
                        == request_dict.get("end_year_month"),
                        TCnApplicationInfo.registration_seq
                        == request_dict.get("registration_seq"),
                        TCnApplicationInfo.entry_draft_flag
                        == request_dict.get("entry_draft_flag"),
                        TBuildingInfo.delete_flg.is_(False),
                    ),
                )
                .outerjoin(
                    MElectricityConversion,
                    and_(
                        TBuildingInfo.electricity_supplier_no
                        == MElectricityConversion.electric_company_reg_no,
                        TBuildingInfo.electricity_contract_menu
                        == MElectricityConversion.menu_nm,
                        (cast(TBuildingInfo.fiscal_year, Integer)) + 1
                        == cast(MElectricityConversion.report_target_year, Integer),
                        MElectricityConversion.delete_flg.is_(False),
                    ),
                )
                .join(
                    MBuilding,
                    and_(
                        TBuildingInfo.corporate_number == MBuilding.corporate_number,
                        TBuildingInfo.agreement_category
                        == MBuilding.agreement_category,
                        # or_(
                        #     TBuildingInfo.org_id == MBuilding.agreement_org,
                        #     TBuildingInfo.org_id == login_org_id,
                        # ),
                        TBuildingInfo.building_id == MBuilding.building_id,
                        MBuilding.delete_flg.is_(False),
                    ),
                )
                .where(
                    TBuildingInfo.corporate_number
                    == request_dict.get("corporate_number"),
                    TBuildingInfo.org_id.in_(
                        [request_dict.get("org_id"), login_org_id] + child_org_ids
                    ),
                    TBuildingInfo.agreement_category
                    == request_dict.get("agreement_category"),
                    TCnApplicationInfo.delete_flg.is_(False),
                )
                .distinct()
                .order_by(TBuildingInfo.building_id.asc())
            )

            logger.debug(building_qry.statement)

            logger.info(f"{os.path.basename(__file__)}energy_qry処理開始。")
            # 月別建物エネルギー集計情報と建物情報とCN対策実施申込情報
            target_year_month_list = AutoEntryLogic.yyyymm_list(
                request_dict.get("start_year_month"), 12
            )
            energy_qry = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_code,
                    TMonthlyBuildingEnergyAggregation.target_year_month,
                    TMonthlyBuildingEnergyAggregation.energy_quantity,
                    TMonthlyBuildingEnergyAggregation.energy_unit_original,
                    TMonthlyBuildingEnergyAggregation.supplier_reg_no,
                    TMonthlyBuildingEnergyAggregation.credit_certificate_purchase_tco2_amount,
                    TMonthlyBuildingEnergyAggregation.credit_certificate_unit,
                )
                .select_from(TCnApplicationInfo)
                .join(
                    TBuildingInfo,
                    and_(
                        TCnApplicationInfo.corporate_number
                        == TBuildingInfo.corporate_number,
                        TCnApplicationInfo.agreement_category
                        == TBuildingInfo.agreement_category,
                        TCnApplicationInfo.org_id == TBuildingInfo.org_id,
                        TCnApplicationInfo.registration_seq
                        == TBuildingInfo.registration_seq,
                        TCnApplicationInfo.entry_draft_flag
                        == TBuildingInfo.entry_draft_flag,
                        TCnApplicationInfo.registration_seq
                        == request_dict.get("registration_seq"),
                        TCnApplicationInfo.entry_draft_flag
                        == request_dict.get("entry_draft_flag"),
                    ),
                )
                .join(
                    TMonthlyBuildingEnergyAggregation,
                    and_(
                        TBuildingInfo.corporate_number
                        == TMonthlyBuildingEnergyAggregation.corporate_number,
                        TBuildingInfo.agreement_category
                        == TMonthlyBuildingEnergyAggregation.agreement_category,
                        TBuildingInfo.org_id
                        == TMonthlyBuildingEnergyAggregation.org_id,
                        TBuildingInfo.building_id
                        == TMonthlyBuildingEnergyAggregation.building_id,
                        TBuildingInfo.registration_seq
                        == TMonthlyBuildingEnergyAggregation.registration_seq,
                        TBuildingInfo.entry_draft_flag
                        == TMonthlyBuildingEnergyAggregation.entry_draft_flag,
                        TMonthlyBuildingEnergyAggregation.target_year_month.in_(
                            target_year_month_list
                        ),
                    ),
                )
                .where(
                    TCnApplicationInfo.report_period_start_year_month
                    == request_dict.get("start_year_month"),
                    TCnApplicationInfo.report_period_end_year_month
                    == request_dict.get("end_year_month"),
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == request_dict.get("corporate_number"),
                    TMonthlyBuildingEnergyAggregation.org_id.in_(
                        [request_dict.get("org_id"), login_org_id] + child_org_ids
                    ),
                    TMonthlyBuildingEnergyAggregation.fiscal_year
                    == request_dict.get("start_year_month", "")[:4],
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_(False),
                    TCnApplicationInfo.delete_flg.is_(False),
                )
                .distinct()
                .order_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number.asc(),
                    TMonthlyBuildingEnergyAggregation.agreement_category.asc(),
                    TMonthlyBuildingEnergyAggregation.org_id.asc(),
                    TMonthlyBuildingEnergyAggregation.building_id.asc(),
                )
            )

            # DataFrame化
            df_parent = pd.read_sql(
                building_qry.statement, session.connection()
            ).fillna("")
            df = pd.read_sql(energy_qry.statement, session.connection()).fillna("")

            # 結合処理呼び出し
            children_map = self.make_energy_list(df)

            logger.info(
                f"{os.path.basename(__file__)}inquiry_building_info_map結合処理開始。"
            )
            res = self.combine_building(df_parent, children_map)
            return res

    # エネルギー情報リスト作成
    @component
    def make_energy_list(
        self, df: pd.DataFrame, logger=None
    ) -> Dict[Tuple[str, str, str, str], List[dict]]:
        """
        dfをグループ化して、
        ネストのdictリストを返す
        """
        if df.empty:
            return {}
        df["energy_quantity"] = df["energy_quantity"].round(2)

        df["credit_certificate_purchase_tco2_amount"] = self.blank_to_zero_numeric(
            df["credit_certificate_purchase_tco2_amount"]
        )

        # energy_codeごとに12ヶ月分まとめてlist化
        grouped = df.groupby(
            [
                "corporate_number",
                "agreement_category",
                "org_id",
                "building_id",
                "energy_code",
                "supplier_reg_no",
            ],
            sort=False,
        ).agg(
            energy_quantities=("energy_quantity", list),
            energy_unit_original=("energy_unit_original", "first"),
            credit_certificate_purchase_tco2_amounts=(
                "credit_certificate_purchase_tco2_amount",
                list,
            ),
            credit_certificate_unit=("credit_certificate_unit", self.first_non_null),
        )

        # マップ構築
        children_map: Dict[Tuple[str, str, str, str], List[dict]] = {}
        for (corp, cat, org, bldg, code, regno), row in grouped.iterrows():

            code = "9900010001" if regno == "REENE" else code

            if code.startswith("9900") and code != "9900010001":
                quantities = row["credit_certificate_purchase_tco2_amounts"]
                energy_unit_original = row["credit_certificate_unit"]
            else:
                quantities = row["energy_quantities"]
                energy_unit_original = row["energy_unit_original"]

            entry = {
                "energy_code": code,
                "energy_quantity": quantities,
                # "supplier_reg_no":       regno,
                "energy_quantity_sum": round(sum(quantities), 2),
                "energy_unit_original": energy_unit_original,
            }
            key = (corp, cat, org, bldg)
            children_map.setdefault(key, []).append(entry)
        return children_map

    def first_non_null(self, s: pd.Series):
        s_clean = s.apply(
            lambda x: None if pd.isna(x) else (x.strip() if isinstance(x, str) else x)
        )
        filtered = [v for v in s_clean if v not in (None, "")]
        return filtered[0] if filtered else None

    def blank_to_zero_numeric(self, s: pd.Series) -> pd.Series:
        ss = s.astype(str).str.strip()
        ss = ss.replace(
            {"": pd.NA, "None": pd.NA, "nan": pd.NA, "NaN": pd.NA, "NULL": pd.NA}
        )
        ss = ss.str.replace(",", "", regex=False)
        out = pd.to_numeric(ss, errors="coerce")
        return out.fillna(0.0)

    # 建物情報リスト作成
    @component
    def combine_building(
        self, df_parent: pd.DataFrame, children_map: dict[tuple, list], logger=None
    ) -> list[dict]:
        """
        df_parentとchildren_mapを埋め込んでdictリストを返す
        """
        if not isinstance(children_map, Mapping):
            children_map = {}

        if df_parent.empty:
            return [
                {
                    "building_id": "",
                    "building_info": {
                        **{k: "" for k in self.BUILDING_INFO_MAP},
                        "energy_info": [],
                    },
                }
            ]

        results: list[dict] = []
        for rec in df_parent.to_dict(orient="records"):
            key = (
                rec["corporate_number"],
                rec["agreement_category"],
                rec["org_id"],
                rec["building_id"],
            )
            # building_infoを組み立て
            # None／NaN のみ "" に、それ以外（0 など）はそのまま保持
            building_info = {}
            for out_field, in_field in self.BUILDING_INFO_MAP.items():
                val = rec.get(in_field)
                # pandas の NaN も空文字化
                if pd.isna(val):
                    building_info[out_field] = ""
                else:
                    building_info[out_field] = val

            # energy_infoだけ別途付与
            building_info["energy_info"] = children_map.get(key, [])

            results.append(
                {
                    "building_id": rec.get("building_id", ""),
                    "building_info": building_info or [],
                }
            )
        return results

    @component
    def get_industry_classification_mst(self, logger=None):
        """
        産業分類マスタのプルダウン表示用取得メソッド
        """
        logger.info(
            f"{os.path.basename(__file__)}get_industry_classification_mst処理開始。"
        )
        with get_scoped_session() as session:
            qry = session.query(
                MJpStIndustryClassification.division_code,
                MJpStIndustryClassification.major_group_code,
                MJpStIndustryClassification.group_code,
                MJpStIndustryClassification.industry_code,
                MJpStIndustryClassification.division_name,
                MJpStIndustryClassification.major_group_name,
                MJpStIndustryClassification.group_name,
                MJpStIndustryClassification.industry_name,
            ).filter(MJpStIndustryClassification.delete_flag.is_not(True))

            df = pd.read_sql(qry.statement, session.connection()).fillna("")

            # 小分類細分類のペアだけ抽出
            res1 = df[["group_code", "group_name"]].to_dict(orient="records")
            res2 = df[["industry_code", "industry_name"]].to_dict(orient="records")

        logger.info(f"データ: {res1}{res2} ")
        logger.info(
            f"{os.path.basename(__file__)}get_industry_classification_mst処理終了。"
        )

        return res1, res2

    @component
    def get_city_gas_heating_value_mst(self, logger=None):
        """
        都市ガスのプルダウン表示用取得メソッド
        """
        logger.info(
            f"{os.path.basename(__file__)}get_city_gas_heating_value_mst処理開始。"
        )
        with get_scoped_session() as session:
            qry = session.query(
                MCityGasHeatingValue.city_gas_supplier_cd,
                MCityGasHeatingValue.city_gas_supplier_nm,
            ).filter_by(delete_flg=False)

            df = pd.read_sql(qry.statement, session.connection()).fillna("")

            # ペアだけ抽出
            res1 = (
                df[["city_gas_supplier_cd", "city_gas_supplier_nm"]]
                .drop_duplicates(subset="city_gas_supplier_cd")
                .to_dict(orient="records")
            )

        logger.info(f"データ: {res1} ")
        logger.info(
            f"{os.path.basename(__file__)}get_city_gas_heating_value_mst処理終了。"
        )

        return res1

    @component
    def get_heat_supplier_menu_mst(self, logger=None):
        """
        熱事業者のプルダウン表示用取得メソッド
        """
        logger.info(f"{os.path.basename(__file__)}get_heat_supplier_menu_mst処理開始。")
        with get_scoped_session() as session:
            qry = session.query(
                MHeatSupplierMenu.heat_supplier_cd,
                MHeatSupplierMenu.heat_supplier_name,
            ).filter_by(delete_flg=False)

            df = pd.read_sql(qry.statement, session.connection()).fillna("")

            # ペアだけ抽出
            res1 = df[["heat_supplier_cd", "heat_supplier_name"]].to_dict(
                orient="records"
            )
            res1 = (
                df[["heat_supplier_cd", "heat_supplier_name"]]
                .drop_duplicates(subset="heat_supplier_cd")
                .to_dict(orient="records")
            )

        logger.info(f"データ: {res1} ")
        logger.info(f"{os.path.basename(__file__)}get_heat_supplier_menu_mst処理終了。")

        return res1
