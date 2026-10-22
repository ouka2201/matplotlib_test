from flask import current_app
from sqlalchemy import and_, case, collate, exists, or_
from sqlalchemy.orm import aliased

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.m_prefecture_entity import PrefectureMst
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)


class CorpBuildingInfoComponent:

    @component
    def execute(
        self, request_dict: dict, user_id, role_id, org_id, logger=None
    ) -> list:
        if logger is None:
            logger = current_app.logger

        # org_id = request_dict.get("org_id")
        # org_name = request_dict.get("org_name")
        # user_name = request_dict.get("user_name")
        company_name = request_dict.get("company_name")
        corporate_number = request_dict.get("corporate_number")
        company_address = request_dict.get("company_address")
        agreement_category = request_dict.get("agreement_category")
        ep_customer_number = request_dict.get("ep_customer_number")
        ep_office_code = request_dict.get("ep_office_code")
        supply_point_number = request_dict.get("supply_point_number")
        building_name = request_dict.get("building_name")
        building_address = request_dict.get("building_address")

        try:
            with get_scoped_session() as session:

                # PrefectureMst の別名
                CorpPref = aliased(PrefectureMst)  # 会社住所用
                BldgPref = aliased(PrefectureMst)  # 建物住所用
                OrgForStaff = aliased(MUserOrganizationInfo)

                query = (
                    session.query(
                        MUserOrganizationInfo.org_id,
                        # OrgForStaff.org_name,
                        # MUser.user_name,
                        # MStaffInfo.user_id,
                        MCorporateBasic.company_name,
                        MCorporateBasic.corporate_number,
                        # MCorporateBasic.company_address_prefecture,
                        CorpPref.pref_nm.label("company_address_prefecture"),
                        BldgPref.pref_nm.label("building_address_prefecture"),
                        MCorporateBasic.company_address_city,
                        MBuilding.location_identifier_name.label("building_name"),
                        MBuilding.building_address_city,
                        MBuilding.ep_office_code,
                        MBuilding.ep_customer_number,
                        MBuilding.supply_point_number,
                        MBuilding.building_id,
                        MCorporateDetailsInfo.agreement_category,
                    )
                    .join(
                        MCorporateDetailsInfo,
                        (MCorporateDetailsInfo.org_id == MUserOrganizationInfo.org_id)
                        & (MCorporateDetailsInfo.agreement_category.like("0%"))
                        & (MCorporateDetailsInfo.delete_flg.is_not(True)),
                    )
                    .join(
                        MBuilding,
                        (
                            MCorporateDetailsInfo.corporate_number
                            == MBuilding.corporate_number
                        )
                        & (
                            MCorporateDetailsInfo.agreement_category
                            == MBuilding.agreement_category
                        )
                        & (MCorporateDetailsInfo.org_id == MBuilding.org_id)
                        & (MBuilding.delete_flg.is_not(True)),
                    )
                    .join(
                        MCorporateBasic,
                        (
                            MCorporateDetailsInfo.corporate_number
                            == MCorporateBasic.corporate_number
                        )
                        & (MCorporateBasic.delete_flg.is_not(True)),
                    )
                    # .outerjoin(
                    #     MStaffInfo,
                    #     (MStaffInfo.corporate_number == MCorporateDetailsInfo.corporate_number)
                    #     & (MStaffInfo.agreement_category == MCorporateDetailsInfo.agreement_category)
                    #     & (MStaffInfo.delete_flg.is_not(True))
                    # )
                    # .outerjoin(
                    #     OrgForStaff,
                    #     (OrgForStaff.org_id == MStaffInfo.org_id)
                    #     & (OrgForStaff.delete_flg.is_not(True))
                    # )
                    # .outerjoin(MUser, MStaffInfo.user_id == MUser.user_id)
                    .outerjoin(
                        CorpPref,
                        CorpPref.pref_cd == MCorporateBasic.company_address_prefecture,
                    )
                    .outerjoin(
                        BldgPref,
                        BldgPref.pref_cd == MBuilding.building_address_prefecture,
                    )
                )

                # if org_name and org_name.strip():
                #     org_name_val = f"%{org_name.strip()}%"
                #     query = query.filter(OrgForStaff.org_name.ilike(org_name_val))

                # if user_name:
                #     query = query.filter(MUser.user_name.ilike(f"%{user_name}%"))

                if company_name:
                    query = query.filter(
                        MCorporateBasic.company_name.ilike(f"%{company_name}%")
                    )
                if corporate_number:
                    query = query.filter(
                        MCorporateBasic.corporate_number.ilike(f"%{corporate_number}%")
                    )

                if company_address:
                    query = query.filter(
                        (CorpPref.pref_nm + MCorporateBasic.company_address_city).ilike(
                            f"%{company_address}%"
                        )
                    )

                if agreement_category:
                    query = query.filter(
                        MCorporateDetailsInfo.agreement_category == agreement_category
                    )

                if ep_customer_number:
                    query = query.filter(
                        MBuilding.ep_customer_number.ilike(f"%{ep_customer_number}%")
                    )

                if supply_point_number:
                    query = query.filter(
                        MBuilding.supply_point_number.ilike(f"%{supply_point_number}%")
                    )
                if building_name:
                    query = query.filter(
                        MBuilding.location_identifier_name.ilike(f"%{building_name}%")
                    )

                if ep_office_code:
                    query = query.filter(MBuilding.ep_office_code == ep_office_code)

                if building_address:
                    query = query.filter(
                        (BldgPref.pref_nm + MBuilding.building_address_city).ilike(
                            f"%{building_address}%"
                        )
                    )

                # EP一般ユーザ の場合、
                # 同意書取得経路が地銀のデータにおいて、営業担当がログインユーザーのみで絞り
                if org_id == "TEP" and role_id == "1":
                    if agreement_category is None:
                        query = query.filter(
                            or_(
                                MCorporateDetailsInfo.agreement_category != "01",
                                and_(
                                    MCorporateDetailsInfo.agreement_category == "01",
                                    exists().where(
                                        (
                                            MCorporateDetailsInfo.corporate_number
                                            == MStaffInfo.corporate_number
                                        )
                                        & (
                                            MCorporateDetailsInfo.agreement_category
                                            == MStaffInfo.agreement_category
                                        )
                                        & (MStaffInfo.delete_flg.is_not(True))
                                        & (MStaffInfo.user_id == user_id)
                                    ),
                                ),
                            )
                        )
                    elif agreement_category == "01":
                        query = query.filter(
                            exists().where(
                                (
                                    MCorporateDetailsInfo.corporate_number
                                    == MStaffInfo.corporate_number
                                )
                                & (
                                    MCorporateDetailsInfo.agreement_category
                                    == MStaffInfo.agreement_category
                                )
                                & (MStaffInfo.delete_flg.is_not(True))
                                & (MStaffInfo.user_id == user_id)
                            )
                        )

                agreement_order = case(
                    (MBuilding.agreement_category == "01", 1),
                    (MBuilding.agreement_category == "02", 2),
                    (MBuilding.agreement_category == "00", 3),
                    else_=99,  # 想定外の値は最後
                )
                query = query.order_by(
                    collate(MCorporateBasic.company_name, "C"),
                    collate(MCorporateBasic.corporate_number, "C"),
                    collate(MBuilding.location_identifier_name, "C"),
                    agreement_order,
                    collate(MBuilding.supply_point_number, "C"),
                )

                results = query.all()

            # print(
            #     query.statement.compile(
            #         dialect=session.connection().dialect,
            #         compile_kwargs={"literal_binds": True}
            #     )
            # )

            response = [dict(e._mapping) for e in results]

            return {"result": response}

        except Exception as e:
            logger.error(f"建物一覧取得時エラー: {str(e)}")
            return {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            }
