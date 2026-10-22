import os
import traceback
from datetime import datetime

import pandas as pd
from flask import abort, current_app
from sqlalchemy import and_, bindparam, collate, func, or_, select
from sqlalchemy.orm import aliased

from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import (
    MCorporateDetailsInfo,
)
from cndx_corp_back.entity.m_prefecture_entity import PrefectureMst
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)


def get_basic_information(request_dict, user_id, role_id, org_type_code, org_id):
    address = (
        select(
            MCorporateBasic.corporate_number,
            func.concat(
                PrefectureMst.pref_nm, MCorporateBasic.company_address_city
            ).label("company_address"),
        )
        .outerjoin(
            PrefectureMst,
            MCorporateBasic.company_address_prefecture == PrefectureMst.pref_cd,
        )
        .subquery()
    )
    stmt = (
        select(
            collate(MCorporateBasic.corporate_number, "C").label("corporate_number"),
            collate(MCorporateBasic.company_name, "C").label("company_name"),
            address.c.company_address,
            MCorporateBasic.company_name_kana,
            MCorporateDetailsInfo.agreement_category,
        )
        .select_from(MCorporateBasic)
        .join(
            MCorporateDetailsInfo,
            and_(
                MCorporateBasic.corporate_number
                == MCorporateDetailsInfo.corporate_number,
                MCorporateDetailsInfo.delete_flg.is_(False),
            ),
        )
        .outerjoin(
            MStaffInfo,
            and_(
                MCorporateBasic.corporate_number == MStaffInfo.corporate_number,
                MStaffInfo.delete_flg.is_(False),
            ),
        )
        .join(
            address,
            and_(
                MCorporateBasic.corporate_number == address.c.corporate_number,
                MCorporateBasic.delete_flg.is_(False),
            ),
        )
        .distinct()
        # .order_by( MCorporateBasic.company_name_kana.asc())
    )

    if role_id == "1" and org_type_code == "01":
        stmt = stmt.where(
            or_(
                MCorporateDetailsInfo.agreement_category != "01",
                and_(
                    MCorporateDetailsInfo.agreement_category == "01",
                    MStaffInfo.user_id == user_id,
                ),
            )
        )

    stmt = (
        stmt.distinct()
        # .order_by(MCorporateBasic.company_name_kana.asc())
    )

    # 条件リストを作る
    conditions = []
    corp_no = request_dict.get("corporate_number")
    if corp_no:
        conditions.append(MCorporateBasic.corporate_number.like(f"%{corp_no}%"))

    comp_name = request_dict.get("company_name")
    if comp_name:
        conditions.append(MCorporateBasic.company_name.like(f"%{comp_name}%"))

    comp_addr = request_dict.get("company_address")
    if comp_addr:
        conditions.append(address.c.company_address.like(f"%{comp_addr}%"))

        # 条件が１つ以上あればANDでまとめてfilter()
    if conditions:
        stmt = stmt.filter(*conditions)
    return stmt


def get_building_group(request_dict):
    stmt = select(
        MBuildingGroup.corporate_number,
        MBuildingGroup.agreement_category,
        MBuildingGroup.org_id,
        MBuildingGroup.group_id,
        MBuildingGroup.group_name,
        MBuildingGroup.select_item1,
        MBuildingGroup.select_item2,
        MBuildingGroup.select_item3,
        MBuildingGroup.select_item4,
        MBuildingGroup.select_item5,
        MBuildingGroup.select_item6,
        MBuildingGroup.select_item7,
    ).order_by(
        MBuildingGroup.agreement_category.asc(),
        MBuildingGroup.org_id.asc(),
        MBuildingGroup.group_id.asc(),
    )
    # 条件リストを作る
    conditions = []
    conditions.append(MBuildingGroup.delete_flg.is_(False))
    agre_ca = request_dict.get("agreement_category")
    if agre_ca:
        conditions.append(MBuildingGroup.agreement_category == agre_ca)
    corp_no = request_dict.get("corporate_number")
    if corp_no:
        conditions.append(MBuildingGroup.corporate_number.like(f"%{corp_no}%"))
    #    user_role = request_dict.get('user_role')
    #    if user_role in ('0', '9'):
    org_id = request_dict.get("org_id")
    if org_id:
        conditions.append(MBuildingGroup.org_id == org_id)
    # 条件が１つ以上あればANDでまとめてfilter()
    if conditions:
        stmt = stmt.filter(*conditions)
    return stmt


def get_user_role(session, userId, org_id, role_id, logger=None):
    """
    権限判定に使用する値を取得
    MUserOrganizationInfo を基点とする
    ・role == "9" のときのみ ChildOrg (muoi1) を LEFT JOIN して child_org_id を SELECT に追加
    ・Pands実行用のステートメントを返す
    """

    # 親組織エイリアス
    muoi = aliased(MUserOrganizationInfo)
    # 子組織エイリアス
    muoi1 = aliased(MUserOrganizationInfo)
    msi = MStaffInfo

    # 共通 SELECT 列（child_org_id は role==9 のときに追加）
    select_items = [
        muoi.business_type,
        msi.corporate_number,
        msi.agreement_category,
    ]

    # 基点クエリ: 親組織 muoi を FROM にする
    stmt = (
        select(*select_items)
        .select_from(muoi)
        .where(
            muoi.org_id == org_id,
            muoi.delete_flg.is_(False),
        )
    )

    # role ごとの JOIN 条件構築
    if str(role_id) == "9":
        # 子組織を LEFT JOIN して child_org_id 列を追加
        stmt = stmt.outerjoin(
            muoi1,
            and_(
                muoi1.parent_org_id == muoi.org_id,
                muoi1.delete_flg.is_(False),
            ),
        )
        # child_org_id を SELECT に追加
        cols = list(select_items) + [muoi1.org_id.label("child_org_id")]
        stmt = stmt.with_only_columns(*cols)

        # msi の ON 条件：delete_flg FALSE and (org_id = parent OR org_id = child)
        msi_on = and_(
            msi.delete_flg.is_(False),
            or_(
                msi.org_id == muoi.org_id,
                msi.org_id == muoi1.org_id,
            ),
        )

    elif str(role_id) == "0":
        # 管理者: 自組織のみ
        msi_on = and_(msi.delete_flg.is_(False), msi.org_id == muoi.org_id)

    elif str(role_id) == "1":
        # 一般: user_id で絞る（org は使わない）
        msi_on = and_(msi.delete_flg.is_(False), msi.user_id == userId)

    # msi を JOIN（ON 条件を直接指定）
    stmt = stmt.join(msi, msi_on)

    stmt = stmt.distinct()

    # ログ出力
    compiled = stmt.compile(
        dialect=session.connection().dialect, compile_kwargs={"literal_binds": True}
    )
    if logger:
        logger.info(f"地銀権限判断SQL: {compiled}")

    return stmt


def get_child_org_user(session, org_id, role_id, logger=None):
    """
    子組織ユーザーを取得する
    """

    # 親組織エイリアス
    muoi = aliased(MUserOrganizationInfo)
    # 子組織エイリアス
    muoi1 = aliased(MUserOrganizationInfo)

    # 共通 SELECT 列（child_org_id は role==9 のときに追加）
    select_items = [
        muoi.business_type,
    ]

    # 基点クエリ: 親組織 muoi を FROM にする
    stmt = (
        select(*select_items)
        .select_from(muoi)
        .where(
            muoi.org_id == org_id,
            muoi.delete_flg.is_(False),
        )
    )

    # role ごとの JOIN 条件構築
    if str(role_id) == "9":
        # 子組織を LEFT JOIN して child_org_id 列を追加
        stmt = stmt.outerjoin(
            muoi1,
            and_(
                muoi1.parent_org_id == muoi.org_id,
                muoi1.delete_flg.is_(False),
            ),
        )
        # child_org_id を SELECT に追加
        cols = list(select_items) + [muoi1.org_id.label("child_org_id")]
        stmt = stmt.with_only_columns(*cols)

    stmt = stmt.distinct()

    # ログ出力
    compiled = stmt.compile(
        dialect=session.connection().dialect, compile_kwargs={"literal_binds": True}
    )
    if logger:
        logger.info(f"子組織ユーザー取得SQL: {compiled}")

    return stmt  # ログ出力
