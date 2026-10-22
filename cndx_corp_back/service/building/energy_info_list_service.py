import os
from collections import OrderedDict, defaultdict
from decimal import Decimal
from typing import Any, Dict, List

from flask import abort, current_app
from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import aliased

from cndx_corp_back.common.database_manager import (
    get_scoped_session,
)
from cndx_corp_back.common.decorators import service
from cndx_corp_back.dto.building.energy_info_list_in_dto import (
    BuildingEnergyInfoListIn,
)
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)


class BuildingEnergyInfoListService:

    @service
    def get_energy_list(self, dto: BuildingEnergyInfoListIn, user_context, logger=None):
        """
        エネルギーリスト取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        login_org_id = user_context.get("org_id")

        # REP、TCSログインの場合
        # if login_org_id != 'TEP':
        #     dto.org_id = login_org_id

        if dto.agreement_category.startswith("0"):
            # dto.org_id = user_context.get("org_id")
            # 地銀の場合
            building_energy_list = self.get_energy_list_bank(dto, user_context, logger)
        else:
            building_energy_list = self.get_energy_list_vis(dto, user_context, logger)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return building_energy_list

    def get_energy_list_bank(
        self, dto: BuildingEnergyInfoListIn, user_context, logger=None
    ) -> list:

        res = None
        login_org_id = user_context.get("org_id")
        org_type_code = user_context.get("org_type_code")
        role_id = user_context.get("role")
        user_id = user_context.get("user_id")

        try:
            with get_scoped_session() as session:
                TCnAppSub = aliased(TCnApplicationInfo)
                max_seq_subq = (
                    select(
                        func.max(TCnAppSub.registration_seq).label(
                            "max_registration_seq"
                        )
                    )
                    .where(
                        TCnAppSub.corporate_number
                        == TCnApplicationInfo.corporate_number,
                        TCnAppSub.agreement_category
                        == TCnApplicationInfo.agreement_category,
                        TCnAppSub.org_id == TCnApplicationInfo.org_id,
                        TCnAppSub.fiscal_year == TCnApplicationInfo.fiscal_year,
                        TCnAppSub.delete_flg.isnot(True),
                    )
                    .correlate(TCnApplicationInfo)
                    .scalar_subquery()
                )

                building_org_exists = exists(
                    select(1)
                    .select_from(TBuildingInfo)
                    .join(
                        MBuilding,
                        and_(
                            TBuildingInfo.corporate_number
                            == MBuilding.corporate_number,
                            TBuildingInfo.agreement_category
                            == MBuilding.agreement_category,
                            TBuildingInfo.building_id == MBuilding.building_id,
                            MBuilding.delete_flg.is_(False),
                        ),
                    )
                    .where(
                        TBuildingInfo.corporate_number
                        == TCnApplicationInfo.corporate_number,
                        TBuildingInfo.agreement_category
                        == TCnApplicationInfo.agreement_category,
                        TBuildingInfo.org_id == TCnApplicationInfo.org_id,
                        TBuildingInfo.fiscal_year == TCnApplicationInfo.fiscal_year,
                        TBuildingInfo.registration_seq
                        == TCnApplicationInfo.registration_seq,
                        TBuildingInfo.delete_flg.is_(False),
                        MBuilding.agreement_org == dto.org_id,
                    )
                    .correlate(TCnApplicationInfo)
                )

                stmt = (
                    select(
                        TCnApplicationInfo.corporate_number,
                        TCnApplicationInfo.agreement_category,
                        TCnApplicationInfo.fiscal_year,
                        TCnApplicationInfo.registration_seq,
                        TCnApplicationInfo.business_office_count,
                        TCnApplicationInfo.report_period_start_year_month,
                        TCnApplicationInfo.report_period_end_year_month,
                        TCnApplicationInfo.entry_draft_flag,
                        TCnApplicationInfo.created_at,
                        TCnApplicationInfo.created_by,
                        max_seq_subq.label("max_registration_seq"),
                        MStaffInfo.user_id,
                        MUser.user_name.label("staff_user_name"),
                        MUserOrganizationInfo.org_id,
                        MUserOrganizationInfo.org_name.label("staff_org"),
                    )
                    .outerjoin(
                        MStaffInfo,
                        and_(
                            TCnApplicationInfo.corporate_number
                            == MStaffInfo.corporate_number,
                            TCnApplicationInfo.agreement_category
                            == MStaffInfo.agreement_category,
                            TCnApplicationInfo.org_id == MStaffInfo.org_id,
                            MStaffInfo.delete_flg.is_(False),
                        ),
                    )
                    .join(
                        MUserOrganizationInfo,
                        TCnApplicationInfo.org_id == MUserOrganizationInfo.org_id,
                    )
                    .outerjoin(MUser, TCnApplicationInfo.created_by == MUser.user_id)
                    .where(
                        TCnApplicationInfo.corporate_number == dto.corporate_number,
                        TCnApplicationInfo.agreement_category == dto.agreement_category,
                        # TCnApplicationInfo.org_id.in_([dto.org_id, login_org_id]),
                        TCnApplicationInfo.delete_flg.isnot(True),
                        # or_(
                        #     TCnApplicationInfo.org_id == dto.org_id,
                        #     building_org_exists,
                        # )
                    )
                    .order_by(
                        TCnApplicationInfo.fiscal_year.desc(),
                        TCnApplicationInfo.registration_seq.desc(),
                    )
                )

                if org_type_code == "02":
                    # mUserOrganizationInfo = select(
                    #     MUserOrganizationInfo.org_id,
                    # ).where(
                    #     MUserOrganizationInfo.parent_org_id == login_org_id,
                    #     MUserOrganizationInfo.delete_flg.is_(False),
                    # )
                    stmt = stmt.where(
                        # or_(
                        #     TCnApplicationInfo.org_id.in_([dto.org_id, login_org_id]),
                        #     TCnApplicationInfo.org_id.in_(mUserOrganizationInfo)
                        # )
                        TCnApplicationInfo.org_id.in_([dto.org_id, login_org_id]),
                    )
                elif org_type_code == "03":
                    stmt = stmt.where(
                        TCnApplicationInfo.org_id == dto.org_id,
                    )
                else:
                    # EP、REP、TCSログインの場合
                    stmt = stmt.where(building_org_exists)

                res = session.execute(stmt).mappings().all()

                unique_keys = set()
                dedup_res = []

                for row in res:
                    key = (
                        row["corporate_number"],
                        row["agreement_category"],
                        row["fiscal_year"],
                        row["registration_seq"],
                        row["org_id"],
                    )
                    if key not in unique_keys:
                        unique_keys.add(key)
                        dedup_res.append(row)

        except Exception as e:
            logger.error(e)
            abort(500)

        if dedup_res is None:
            return []
        else:
            li = [dict(e) for e in dedup_res]
            return li

    def get_energy_list_vis(
        self, dto: BuildingEnergyInfoListIn, user_context, logger: None
    ) -> dict:

        res = None
        # login_org_id=user_context.get("org_id")
        org_type_code = user_context.get("org_type_code")

        # 電気証書エネルギーコード
        co2_subtract_codes = [
            "9900010002",
            "9900010003",
            "9900010004",
            "9900011002",
            "9900011003",
            "9900011004",
            "9900011005",
            "9900011007",
            "9900010006",
            "9900010013",
            "9900011013",
            "9900011001",
        ]
        # 電気証書以外エネルギーコード
        co2_add_codes = [
            "9900011006",
            "9900011008",
            "9900011009",
            "9900011010",
            "9900011011",
            "9900011012",
            "9900011013",
            "9900011014",
        ]
        # 電気CO2排出量合計値
        co2_0200010011 = func.sum(
            case(
                (
                    TMonthlyBuildingEnergyAggregation.energy_code == "0200010011",
                    TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions,
                ),
                else_=0,
            )
        )
        #
        co2_subtract = func.sum(
            case(
                (
                    TMonthlyBuildingEnergyAggregation.energy_code.in_(
                        co2_subtract_codes
                    ),
                    TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions,
                ),
                else_=0,
            )
        )

        co2_additional = func.sum(
            case(
                (
                    TMonthlyBuildingEnergyAggregation.energy_code.in_(co2_add_codes),
                    0,
                ),  # 0固定に変更
                else_=0,
            )
        )

        excluded_codes = ["0200010011"] + co2_subtract_codes + co2_add_codes

        co2_others = func.sum(
            case(
                (
                    ~TMonthlyBuildingEnergyAggregation.energy_code.in_(excluded_codes),
                    TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions,
                ),
                else_=0,
            )
        )

        # 最終的な co2_emissions
        co2_emissions_expr = (
            co2_others
            + func.greatest(co2_0200010011 - co2_subtract, 0)
            + co2_additional
        ).label("co2_emissions")

        try:
            with get_scoped_session() as session:
                conditions = [
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == dto.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == dto.agreement_category,
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                ]
                if org_type_code == "06":
                    conditions.append(
                        TMonthlyBuildingEnergyAggregation.org_id == dto.org_id
                    )
                stmt = (
                    select(
                        TMonthlyBuildingEnergyAggregation.corporate_number,
                        TMonthlyBuildingEnergyAggregation.fiscal_year,
                        MCorporateBasic.company_name.label("corporate_name"),
                        MBuilding.location_identifier_name.label("building_name"),
                        TMonthlyBuildingEnergyAggregation.building_id,
                        TMonthlyBuildingEnergyAggregation.target_year_month.label(
                            "year_month"
                        ),
                        func.sum(
                            case(
                                (
                                    TMonthlyBuildingEnergyAggregation.heat_converted_energy_unit
                                    == "MJ",
                                    TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage
                                    / 1000,
                                ),
                                else_=TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage,
                            )
                        ).label("primary_energy_data"),
                        co2_emissions_expr,
                        TMonthlyBuildingEnergyAggregation.org_id,
                        TMonthlyBuildingEnergyAggregation.agreement_category,
                        MUserOrganizationInfo.business_type,
                        MUserOrganizationInfo.org_name.label("vis_vendor_name"),
                        MBuilding.location_identifier_code.label(
                            "location_identifier_code"
                        ),
                    )
                    .where(*conditions)
                    .join(
                        MCorporateBasic,
                        and_(
                            TMonthlyBuildingEnergyAggregation.corporate_number
                            == MCorporateBasic.corporate_number,
                            MCorporateBasic.delete_flg.is_not(True),
                        ),
                    )
                    .join(
                        MBuilding,
                        and_(
                            TMonthlyBuildingEnergyAggregation.corporate_number
                            == MBuilding.corporate_number,
                            TMonthlyBuildingEnergyAggregation.agreement_category
                            == MBuilding.agreement_category,
                            # TMonthlyBuildingEnergyAggregation.org_id.in_([dto.org_id, login_org_id]),
                            TMonthlyBuildingEnergyAggregation.building_id
                            == MBuilding.building_id,
                            MBuilding.delete_flg.is_not(True),
                        ),
                    )
                    .join(
                        MUserOrganizationInfo,
                        and_(
                            # MUserOrganizationInfo.org_id.in_([dto.org_id, login_org_id]),
                            TMonthlyBuildingEnergyAggregation.org_id
                            == MUserOrganizationInfo.org_id,
                            MUserOrganizationInfo.delete_flg.is_not(True),
                        ),
                    )
                    .group_by(
                        TMonthlyBuildingEnergyAggregation.corporate_number,
                        TMonthlyBuildingEnergyAggregation.fiscal_year,
                        MCorporateBasic.company_name,
                        TMonthlyBuildingEnergyAggregation.agreement_category,
                        MBuilding.location_identifier_name,
                        TMonthlyBuildingEnergyAggregation.building_id,
                        TMonthlyBuildingEnergyAggregation.target_year_month,
                        TMonthlyBuildingEnergyAggregation.org_id,
                        MUserOrganizationInfo.business_type,
                        MUserOrganizationInfo.org_name,
                        MBuilding.location_identifier_code,
                    )
                )

                # if org_type_code == "06":
                # 可視化の場合
                # stmt = stmt.where(
                #     and_(
                #         MUserOrganizationInfo.org_id.in_([dto.org_id, login_org_id]),
                #     )
                # )

                res = session.execute(stmt).mappings().all()

                # if "org_id" in user_context and user_context["org_id"] != "TEP":
                #     #一般者
                #     if "role" in user_context and user_context.get('role') == "1":
                #         user_stmt=session.query(
                #                             MStaffInfo.user_id,
                #                             MUserOrganizationInfo.org_id,
                #                             MUserOrganizationInfo.org_name,
                #                             MStaffInfo.corporate_number,
                #                         ).where(MStaffInfo.user_id == user_context.get('user_id'),
                #                                 MStaffInfo.org_id == user_context.get('org_id'),
                #                                 MStaffInfo.delete_flg.isnot(True)
                #                         ).all()
                #         user_corporates = {row.corporate_number for row in user_stmt}
                #         res = [row for row in res if row["corporate_number"] in user_corporates]
                #     #管理者
                #     else:
                #         res = [row for row in res if row["org_id"] == user_context.get('org_id')]
            # print(
            #     stmt.compile(
            #         dialect=session.connection().dialect,
            #         compile_kwargs={"literal_binds": True},
            #     )
            # )
        except Exception as e:
            logger.error(e)
            abort(500)

        return build_fiscal_arrays(res)


def build_fiscal_arrays(res: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    入力: res = [{ 'year_month': 'YYYYMM', 'building_id': ..., 'building_name': ...,
                   'primary_energy_data': Decimal, 'co2_emissions': Decimal,
                   'org_id': ..., 'agreement_category': ..., 'vis_vendor_name': ...}, ...]
    出力: 指定フォーマットの dict
    """
    if not res:
        return {"agreement_category": "", "data_vendors": [], "org_id": ""}

    # ヘッダ系は先頭から
    # org_id = res[0].get("org_id", "")
    # agreement_category = res[0].get("agreement_category", "")

    # ベンダ → 会計年度 → 建物 → 月(0..11: Apr..Mar) に集計
    # 値は「最後に見た値」を採用（重複が無ければそのまま格納）
    buckets = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: {"building_name": "", "co2": [0.0] * 12, "pe": [0.0] * 12}
            )
        )
    )

    for row in res:
        ym = str(row["year_month"])  # 'YYYYMM'
        yyyy = int(ym[:4])
        mm = int(ym[4:6])

        # 会計年度（4-3）：4-12は +1年、1-3はその年
        fiscal_year = yyyy + 1 if mm >= 4 else yyyy

        # 4月=0, 5=1, ..., 12=8, 1=9, 2=10, 3=11
        month_idx = (mm - 4) % 12

        vendor = row.get("vis_vendor_name", "")
        b_id = row.get("building_id")
        b_name = row.get("building_name", "")
        b_org_id = row.get("org_id", "")
        b_agreement_category = row.get("agreement_category", "")
        b_locIdentifierCd = row.get("location_identifier_code", "")

        pe = _to_float(row.get("primary_energy_data", 0.0))
        co2 = _to_float(row.get("co2_emissions", 0.0))

        bslot = buckets[vendor][fiscal_year][b_id]
        bslot["building_name"] = b_name
        bslot["pe"][month_idx] = pe
        bslot["co2"][month_idx] = co2
        bslot["org_id"] = b_org_id
        bslot["agreement_category"] = b_agreement_category
        bslot["locIdentifierCd"] = b_locIdentifierCd

    # 出力整形（ベンダ→年度→建物の順で安定的に並べたい場合はソート）
    data_vendors = []
    for vendor_name in sorted(buckets.keys()):
        years_dict = buckets[vendor_name]

        data_years = []
        for fy in sorted(years_dict.keys()):
            buildings_dict = years_dict[fy]

            data_buildings = []
            for b_id in sorted(buildings_dict.keys()):
                info = buildings_dict[b_id]
                obj = {
                    "building_id": b_id,
                    "org_id": info["org_id"],
                    "agreement_category": info["agreement_category"],
                    "building_name": info["building_name"],
                    "co2_emissions": info["co2"],
                    "primary_energy_data": info["pe"],
                    "start_year_month": f"{fy-1}04",
                    "locIdentifierCd": info["locIdentifierCd"],
                }

                # 全部0でなければ追加
                if any(v != 0.0 for v in info["co2"]):
                    obj["co2_emissions"] = info["co2"]
                if any(v != 0.0 for v in info["pe"]):
                    obj["primary_energy_data"] = info["pe"]

                data_buildings.append(obj)

            data_years.append(
                {"fiscal_year": str(fy - 1), "data_buildings": data_buildings}
            )

        data_vendors.append({"vis_vendor_name": vendor_name, "data_years": data_years})

    return {
        # "agreement_category": str(agreement_category),
        "data_vendors": data_vendors,
        # "org_id": str(org_id),
    }


def _to_float(x):
    if isinstance(x, Decimal):
        # Decimal('0E-10') 等も 0.0 に
        return float(x.quantize(Decimal("0.0000"))) if x.is_finite() else 0.0
    if x is None:
        return 0.0
    return float(x)
