import os

import pandas as pd
from flask import current_app
from sqlalchemy import and_, bindparam, collate, func, literal_column, or_, select

import cndx_corp_back.query.common_queries as QueryMst
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
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


# 企業基本情報照会
class CorprationBasicInquiryComponent:

    @component
    def execute(self, request_dict: dict, user_id, user_role, logger=None):
        """レポート情報取得"""

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        #        # 対象のパラメータ
        #        params = {"corporate_number", "company_name"}

        #        # 条件文を組立
        #        where_clause = " ".join(
        #            [address_patch(k) for k in request_dict.keys() if k in params]
        #        )

        is_show_detail: bool = False
        # フィルタ一覧を生成
        filters = []
        if "company_name" in request_dict:
            filters.append(MCorporateBasic.company_name.like(bindparam("company_name")))
        if "corporate_number" in request_dict:
            is_show_detail = True
            filters.append(
                MCorporateBasic.corporate_number.like(bindparam("corporate_number"))
            )
        filters.append(MCorporateBasic.delete_flg.is_(False))
        filters.append(MCorporateBasic.delete_flg.is_(False))

        # user_roleがEP一般の場合、地銀を含めない
        if str(user_role) == "1":
            # 自分が担当者として登録されているかを確認するサブクエリ
            staff_exists_subq = (
                select(1)
                .where(
                    MStaffInfo.corporate_number == MCorporateBasic.corporate_number,
                    MStaffInfo.user_id == user_id,
                    MStaffInfo.delete_flg.is_(False),
                )
                .exists()
            )

            filters.append(
                or_(
                    # 条件A: 地銀が含まれていない
                    or_(
                        MBuilding.agreement_org.not_like("%BNK%"),
                        MBuilding.agreement_org.is_(None),
                    ),
                    # 条件B: 条件Aに該当しなくても、自分が担当者なら該当
                    staff_exists_subq,
                )
            )

        # ワイルドカードを追加
        for key in request_dict:
            if key == "company_address":
                continue  # スキップ
            request_dict[key] = f"%{request_dict[key]}%"

        #        m_building_sql = QueryMst.CORP_JOIN_BLD_08_01.value.format(where=where_clause)

        # 同意書取得組織名取得
        org_name_subq = (
            select(MUserOrganizationInfo.org_name)
            .where(
                MUserOrganizationInfo.org_id == MBuilding.agreement_org,
                MUserOrganizationInfo.delete_flg.is_(False),
            )
            .scalar_subquery()
        )
        with get_scoped_session() as session:

            stmt = (
                select(
                    MCorporateBasic.corporate_number,
                    MCorporateBasic.company_name,
                    MCorporateBasic.company_name_kana,
                    MCorporateBasic.company_address_prefecture,
                    MCorporateBasic.company_address_city,
                    func.concat(
                        PrefectureMst.pref_nm, MCorporateBasic.company_address_city
                    ).label("company_address"),
                    MBuilding.agreement_category,
                    MBuilding.building_id,
                    MBuilding.ep_office_code,
                    MBuilding.ep_customer_number,
                    MBuilding.supply_point_number,
                    # MBuilding.building_name,
                    MBuilding.location_identifier_name,
                    MBuilding.building_address_prefecture,
                    MBuilding.building_address_city,
                    MBuilding.group1,
                    MBuilding.group2,
                    MBuilding.group3,
                    MBuilding.group4,
                    MBuilding.group5,
                    MBuilding.agreement_org,
                    org_name_subq.label("org_name"),
                )
                .select_from(MCorporateBasic)
                .outerjoin(
                    MBuilding,
                    and_(
                        MCorporateBasic.corporate_number == MBuilding.corporate_number,
                        MBuilding.delete_flg.is_(False),
                    ),
                )
                .outerjoin(
                    PrefectureMst,
                    MCorporateBasic.company_address_prefecture == PrefectureMst.pref_cd,
                )
                #                .join(
                #                    MUserOrganizationInfo,
                #                    MUserOrganizationInfo.org_id == MBuilding.agreement_org,
                #                )
                #                .filter(MUserOrganizationInfo.delete_flg.is_(False))
                .where(and_(*filters))
            )

            if is_show_detail:
                # 詳細画面のソート
                stmt = stmt.order_by(MBuilding.created_at.asc())
            else:
                # 一覧画面のソート
                stmt = stmt.order_by(
                    collate(MCorporateBasic.company_name, "C").asc(),
                    collate(MCorporateBasic.corporate_number, "C").asc(),
                )
            logger.info(f"データ: {stmt} ")

            sql_params = dict(request_dict)
            # 親組織管理者ではEPで既に担当者を追加した企業のみ表示する
            df = pd.read_sql(stmt, session.connection(), params=sql_params)

        company_address = request_dict.get("company_address")
        # 住所検索フィルター
        if company_address:
            df = df[
                df["company_address"].str.contains(
                    company_address, na=False, regex=False
                )
            ]

        # grouped = df.groupby(
        #     [
        #         "corporate_number",
        #         "company_name",
        #         "company_name_kana",
        #         "company_address",
        #         "agreement_category",
        #     ]
        # )

        # 企業情報をグループ化
        res = nest_dataframe(
            df,
            parent_keys=[
                "corporate_number",
                "company_name",
                "company_name_kana",
                "company_address",
                "company_address_prefecture",
                "company_address_city",
            ],
            child_name="office_info_list",
        )

        # テーブル結合で出た None オブジェクトを除去
        for corp_i in res:
            if (
                corp_i["office_info_list"].__len__() == 1
                and corp_i["office_info_list"][0]["building_id"] == None
            ):
                corp_i["office_info_list"].clear()

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return res


def address_patch(key):
    # if key == "company_address":
    #     return f"concat(mcb.company_address_prefecture, mcb.company_address_city) LIKE :{key} AND"
    # else:
    return f"mcb.{key} LIKE :{key} AND"


def nest_dataframe(
    df: pd.DataFrame,
    parent_keys: list,
    child_keys: list = None,
    child_name: str = "children",
):
    if child_keys is None:
        # child_keysを推定
        child_keys = [col for col in df.columns if col not in parent_keys]

    result = {}
    for _, row in df.iterrows():
        parent_id = row[parent_keys[0]]
        if parent_id not in result:
            result[parent_id] = {k: row[k] for k in parent_keys}
            result[parent_id][child_name] = []

        child_item = {k: row[k] for k in child_keys}
        result[parent_id][child_name].append(child_item)

    return list(result.values())
