from collections import OrderedDict
from os import path

import pandas as pd
from flask import abort, current_app
from werkzeug.exceptions import HTTPException

import cndx_corp_back.query.common_queries as Queries
from cndx_corp_back.common.database_manager import get_db_engine, get_scoped_session

# from sqlalchemy import text
from cndx_corp_back.common.decorators import component
from cndx_corp_back.dto.building_group.building_group_update_in_dto import (
    BuildingGroupUpdateInDto,
)
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.query.building_group_management_query import (
    BuildingGroupManagementQuery,
)


# 建物グループマスタ管理画面
class BuildingGroupManagementLogic:
    @component
    def getBuildingGroup(self, params, logger=None):
        """
        同意書取得情報から建物グループマスタ情報の取得処理
        """
        if logger is None:
            logger = current_app.logger
        logger.info(f"{path.basename(__file__)}処理開始。")

        # 建物グループ情報とコードマスタを検索
        with get_db_engine().begin() as conn:

            # グループマスタから取得
            sql = Queries.get_building_group(params)
            df_buildingGroupList: pd.DataFrame = pd.read_sql(sql, conn)

            # 建物情報をリスト化
            result_ordered = OrderedDict(
                [
                    (
                        "building_group_info",
                        df_buildingGroupList.to_dict(orient="records"),
                    )
                ]
            )
            res = OrderedDict([("result", result_ordered)])
            logger.info(f"実行SQL: {sql} ")
            logger.info(f"データ: {res} ")

        logger.info(f"{path.basename(__file__)}処理終了。")

        return res

    @component
    def update_building_group(self, dto: BuildingGroupUpdateInDto, logger=None):
        """
        建物グループマスタの更新処理
        """
        if logger is None:
            logger = current_app.logger
        logger.info(f"{path.basename(__file__)}処理開始。")

        db_filter_dict = dto.model_dump()
        update_dict = db_filter_dict.pop("selected_options", {})
        db_filter_dict.pop("building_ids")

        # 更新処理
        try:
            with get_scoped_session() as session:
                # 更新したいレコードを取得
                rows = (
                    session.query(MBuilding)
                    .filter_by(**db_filter_dict)
                    .filter(MBuilding.building_id.in_(dto.building_ids))
                    .all()
                )

                # 件数が合う場合
                if len(rows) == len(dto.building_ids):
                    # レコード毎に
                    for row in rows:
                        # 該当グループを更新
                        for key, value in update_dict.items():
                            if hasattr(row, f"group{key}"):
                                setattr(row, f"group{key}", value)

                else:
                    abort(404, "レコード存在しません。")

                session.commit()

        except HTTPException as e:
            raise e

        except Exception as e:
            logger.error("データベース接続失敗")
            abort(500)

        logger.info(f"{path.basename(__file__)}処理終了。")
        return
