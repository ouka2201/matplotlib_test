import os

import pandas as pd
from flask import current_app
from sqlalchemy import and_, bindparam, func, select

from cndx_corp_back.common.database_manager import (
    build_query,
    build_sql,
    get_db_engine,
    get_scoped_session,
)
from cndx_corp_back.common.db_base_handler import BaseRepository
from cndx_corp_back.common.decorators import service
from cndx_corp_back.constant.constants import ENERGY_CODE_TO_ENG
from cndx_corp_back.dto.corp.branch_energy_info_dto import BranchEnergyInfoDTO
from cndx_corp_back.entity.m_building_entity import MBuilding

# from cndx_corp_back.logic.building.info_component import BuildingInfoLogic
from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.entity.m_prefecture_entity import PrefectureMst
from cndx_corp_back.query.query_mst import QueryMst
from cndx_corp_back.utils.datetime_utils import format_datetimes
from cndx_corp_back.utils.dto_utils import include
from cndx_corp_back.utils.number_utils import (
    format_decimal_with_scale,
    normalize_decimal_string,
)


class BuildingInfoService:

    @service
    def get_building_info(self, request_dict: dict, logger=None):
        """
        建物情報取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 対象企業のグループマスタと建物情報の照会用SQLを用意
        request_dict["deleted_flg"] = False
        #        sql_corp = build_query(QueryMst.M_BUIDING_GROUP_08_04.value, request_dict)
        #        sql_bld = QueryMst.M_BUILDING_08_04.value.format(**request_dict)

        # 必要なデータを抽出
        with get_scoped_session() as session:

            corp_no = request_dict.get("corporate_number")
            agr_cat = request_dict.get("agreement_category")

            sql_corp = select(
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
            )
            # corporate_number は必須絞り込み
            if corp_no:
                sql_corp = sql_corp.where(MBuildingGroup.corporate_number == corp_no)
            # 削除フラグ絞り込み
            sql_corp = sql_corp.where(MBuildingGroup.delete_flg.is_(False))
            # 　実行
            df_corp: pd.DataFrame = pd.read_sql(sql_corp, session.connection())

            sql_bld = select(
                MBuilding.corporate_number,
                MBuilding.agreement_category,
                MBuilding.org_id,
                MBuilding.building_id,
                MBuilding.ep_customer_number,
                MBuilding.supply_point_number,
                MBuilding.location_identifier_name.label("building_name"),
                MBuilding.location_identifier_name,
                MBuilding.building_address_prefecture,
                MBuilding.building_address_city,
                func.concat(
                    PrefectureMst.pref_nm, MBuilding.building_address_city
                ).label("building_address"),
                MBuilding.industry_class_detail_code,
                MBuilding.industry_class_detail_name,
                MBuilding.benchmark_denom,
                MBuilding.benchmark_val,
                MBuilding.ep_office_code,
                MBuilding.building_consent_flag,
                MBuilding.group1,
                MBuilding.group2,
                MBuilding.group3,
                MBuilding.group4,
                MBuilding.group5,
                MBuilding.created_at,
                MBuilding.updated_at,
            ).outerjoin(
                PrefectureMst,
                and_(
                    PrefectureMst.pref_cd == MBuilding.building_address_prefecture,
                ),
            )
            # corporate_number は必須絞り込み
            if corp_no:
                sql_bld = sql_bld.where(MBuilding.corporate_number == corp_no)
            # agreement_category 絞り込み追加
            sql_bld = sql_bld.where(MBuilding.agreement_category.startswith("1"))
            # 削除フラグ絞り込み
            sql_bld = sql_bld.where(MBuilding.delete_flg.is_(False))
            # ソート
            sql_bld = sql_bld.order_by(
                MBuilding.corporate_number.asc(),
                MBuilding.agreement_category.asc(),
                MBuilding.org_id.asc(),
                MBuilding.building_id.asc(),
            )

            #            df_corp: pd.DataFrame = pd.read_sql(sql_corp, session.connection())
            #            df_corp = pd.DataFrame(records)
            df_bld: pd.DataFrame = pd.read_sql(sql_bld, session.connection())

        # 無効な値を0に変換
        df_bld["benchmark_val"] = df_bld["benchmark_val"].fillna(0)
        df_bld["benchmark_val"] = df_bld["benchmark_val"].apply(
            normalize_decimal_string
        )
        df_bld["benchmark_denom"] = df_bld["benchmark_denom"].apply(
            lambda x: format_decimal_with_scale(x, 3)
        )

        # flat 形式から リストに変更
        option_cols = [f"select_item{i}" for i in range(1, 8)]

        df_corp["group_options"] = df_corp[option_cols].values.tolist()
        df_corp["group_options"] = df_corp["group_options"].apply(
            lambda x: [i for i in x if pd.notna(i)]
        )

        # 要らないものを除外
        result_df = df_corp[
            [
                "corporate_number",
                "agreement_category",
                "org_id",
                "group_id",
                "group_name",
                "group_options",
            ]
        ]

        result = {"group_setting_info": result_df.to_dict(orient="records")}

        # 建物情報を入れる
        result["building_info_list"] = df_bld.to_dict(orient="records")

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return format_datetimes(result)
