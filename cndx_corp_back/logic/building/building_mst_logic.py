import re

import numpy as np
import pandas as pd
from flask import abort, current_app
from sqlalchemy import and_, func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.entity.m_consent_route_info_entity import MConsentRouteInfo
from cndx_corp_back.entity.m_prefecture_entity import PrefectureMst


class BuildingMstLogic:

    # 建物情報取得
    @component
    def get_building_mst_info(self, request_dict, logger=None):
        if logger is None:
            logger = current_app.logger

        with get_scoped_session() as session:
            building_stmt = (
                session.query(
                    MBuilding.corporate_number,
                    MBuilding.agreement_category,
                    MBuilding.org_id,
                    MConsentRouteInfo.agreement_name,
                    MBuilding.building_id,
                    MBuilding.location_identifier_name.label("building_name"),
                    MBuilding.location_identifier_name,
                    MBuilding.building_address_prefecture,
                    MBuilding.building_address_city,
                    func.concat(
                        PrefectureMst.pref_nm,
                        MBuilding.building_address_city,
                    ).label("building_address"),
                    MBuilding.industry_class_detail_code,
                    MBuilding.industry_class_detail_name,
                    MBuilding.benchmark_denom,
                    MBuilding.benchmark_val,
                    MBuilding.gross_floor_area,
                    MBuilding.group1,
                    MBuilding.group2,
                    MBuilding.group3,
                    MBuilding.group4,
                    MBuilding.group5,
                )
                .where(
                    MBuilding.corporate_number == request_dict["corporate_number"],
                    MBuilding.agreement_category == request_dict["agreement_code"],
                    # MBuilding.org_id == request_dict["org_id"],
                    MBuilding.building_id == request_dict["building_id"],
                    MBuilding.delete_flg.is_not(True),
                    PrefectureMst.delete_flag == 0,
                    MConsentRouteInfo.delete_flg.is_(False),
                )
                .outerjoin(
                    PrefectureMst,
                    PrefectureMst.pref_cd == MBuilding.building_address_prefecture,
                )
                .outerjoin(
                    MConsentRouteInfo,
                    MConsentRouteInfo.agreement_category
                    == MBuilding.agreement_category,
                )
                .all()
            )

            # グループ名取得
            group_stmt = (
                session.query(
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
                .where(
                    MBuildingGroup.corporate_number
                    == request_dict.get("corporate_number"),
                    MBuildingGroup.agreement_category
                    == request_dict.get("agreement_code"),
                    # MBuildingGroup.org_id == request_dict.get("org_id"),
                    # MBuildingGroup.building_id == request_dict["building_id"],
                    MBuildingGroup.delete_flg.is_not(True),
                )
                .order_by(MBuildingGroup.group_id.asc())
                .all()
            )

        # 絞り対象建物情報取得
        df_building = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in building_stmt
            ],
            dtype=str,
        )

        if not building_stmt:
            abort(400, description="建物マスタ情報は存在しません。")

        try:
            if not group_stmt:
                merged_dict = {
                    "buildingBasicInfo": df_building.iloc[0].to_dict(),
                    "groupSettingInfoItem": [],
                }
            else:
                group_list = []

                df_building_group = pd.DataFrame(
                    [
                        {field: getattr(row, field) for field in row._fields}
                        for row in group_stmt
                    ],
                    dtype=str,
                )
                # グループ名称設定する
                res = set_group_info(df_building, df_building_group)

                for _, row in df_building_group.iterrows():
                    d = {
                        "group_id": row["group_id"],
                        "group_name": row["group_name"],
                        "group_options": [row[f"select_item{i}"] for i in range(1, 8)],
                    }
                    group_list.append(d)

                merged_dict = {
                    "buildingBasicInfo": res.iloc[0].to_dict(),
                    "groupSettingInfoItem": group_list,
                }
        except Exception as e:
            logger.error(e)
            abort(500)

        return merged_dict


def set_group_info(df1, df2):
    KEYS = ["corporate_number", "agreement_category", "org_id"]

    for k in KEYS:
        df1[k] = df1[k].astype(str)
        df2[k] = df2[k].astype(str)

    fw2hw = str.maketrans("０１２３４５６７８９", "0123456789")

    def num_from_name(s):
        m = re.search(r"[0-9０-９]+", str(s))
        return int(m.group(0).translate(fw2hw)) if m else None

    group_cols = [c for c in df1.columns if re.fullmatch(r"group[0-9０-９]+", str(c))]
    group_cols = [c for c in group_cols if 1 <= num_from_name(c) <= 5]

    opt_cols = [c for c in df2.columns if c.startswith("select_item")]
    df2_long = df2.melt(
        id_vars=KEYS + ["group_id"],
        value_vars=opt_cols,
        var_name="select_item_col",
        value_name="select_item_val",
    )
    df2_long["select_item_no"] = (
        df2_long["select_item_col"]
        .str.extract(r"([0-9０-９]+)")[0]
        .str.translate(fw2hw)
        .astype("Int64")
    )

    df2_key = df2_long[KEYS + ["group_id", "select_item_no", "select_item_val"]].copy()

    df2_key["group_id"] = pd.to_numeric(df2_key["group_id"], errors="coerce").astype(
        "Int64"
    )

    for gcol in group_cols:
        gid = num_from_name(gcol)

        tmp = df1[KEYS + [gcol]].copy()
        tmp["_i"] = np.arange(len(tmp))
        tmp["group_id"] = gid
        tmp["select_item_no"] = pd.to_numeric(tmp[gcol], errors="coerce").astype(
            "Int64"
        )

        merged = tmp.merge(
            df2_key,
            on=KEYS + ["group_id", "select_item_no"],
            how="left",
        ).sort_values("_i")

        df1.loc[:, gcol] = merged["select_item_val"].values

    return df1.astype("object").where(pd.notna(df1), None)
