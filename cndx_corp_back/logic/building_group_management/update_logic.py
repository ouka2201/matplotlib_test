import os
import traceback
from datetime import datetime

import pandas as pd
from flask import current_app
from sqlalchemy import bindparam, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

import cndx_corp_back.query.common_queries as Queries
from cndx_corp_back.common.database_manager import get_db_engine, get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.query.building_group_management_query import (
    BuildingGroupManagementQuery,
)


class BuildingGroupLogic:

    @component
    def upsert_building_group(self, dict_request_data, user_id, logger=None):

        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 登録・更新処理（UPSERT）
        # INSERT ステートメント作成
        insert_stmt = pg_insert(MBuildingGroup).values(
            **dict_request_data, created_by=user_id, created_at=func.now()
        )
        # EXCLUDED から更新用マッピング
        excluded = insert_stmt.excluded

        # 主キー以外を自動でマッピング
        update_cols = {
            col.name: getattr(excluded, col.name)
            for col in MBuildingGroup.__table__.columns
            if not col.primary_key
            and col.name not in ("created_by", "created_at", "updated_by", "updated_at")
        }
        update_cols["updated_by"] = user_id
        update_cols["updated_at"] = func.now()

        # ON CONFLICT DO UPDATE を組み立て
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                "corporate_number",
                "agreement_category",
                "org_id",
                "group_id",
            ],
            set_=update_cols,
        )

        with get_scoped_session(logger) as session:
            try:
                session.execute(upsert_stmt)
                session.commit()
            except Exception as e:
                logger.error(
                    "建物グループマスタ管理画面_更新時に例外発生\n"
                    + traceback.format_exc()
                )
                raise
        logger.info(f"{os.path.basename(__file__)}処理終了。")

    @component
    def get_building_group(dict_request_data, logger=None):
        """
        グループ名の重複チェック
        """
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        with get_db_engine().begin() as conn:
            sql = Queries.get_building_group(dict_request_data)
            df_buildingGroupList: pd.DataFrame = pd.read_sql(sql, conn)

            compiled = sql.compile(compile_kwargs={"literal_binds": True})
            logger.info(f"実行SQL: {compiled}")
            logger.info(f"データ: {df_buildingGroupList} ")

        resultList = df_buildingGroupList.to_dict(orient="records")
        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return resultList
