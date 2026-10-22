import traceback

from flask import current_app
from sqlalchemy import bindparam, func, update

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding


class BuildingGroupLogic:

    # グループ一括更新（将来使用）
    @component
    def update_groups(
        self, building_ids: list, group_fields: dict, updated_by: str, logger=None
    ):
        if logger is None:
            logger = current_app.logger

        if not building_ids or not group_fields:
            raise ValueError("建物IDおよび更新対象のグループ項目が必要です。")

        with get_scoped_session(logger) as session:
            for building_id in building_ids:
                logger.info(f"building_id 存在チェック中: {building_id}")

                # group_fields のキーをすべて bindparam にマッピング
                values_map = {field: bindparam(field) for field in group_fields.keys()}
                # updated_by と updated_at も追加
                values_map.update(
                    updated_by=bindparam("updated_by"),
                    updated_at=func.current_timestamp(),
                )
                # UPDATE ステートメントを組み立て
                sql = (
                    update(MBuilding)
                    .where(MBuilding.building_id == bindparam("b_building_id"))
                    .values(**values_map)
                )
                # 実行時に渡すパラメータ辞書
                params = {
                    **group_fields,
                    "updated_by": updated_by,
                    "b_building_id": building_id,
                }

                logger.info(f"実行SQL: {sql}")
                logger.info(f"パラメータ: {params}")

                try:
                    session.execute(sql, params)
                except Exception as e:
                    logger.error("SQL 実行時に例外発生\n" + traceback.format_exc())
                    logger.warning(f"建物ID {building_id} の更新に失敗しました")
                    raise

            session.commit()

    # 単体建物の任意フィールド更新
    @component
    def update_single_building(
        self, keys: dict, update_fields: dict, updated_by: str, logger=None
    ):
        if logger is None:
            logger = current_app.logger

        if not keys or not update_fields:
            raise ValueError("建物の主キー情報および更新対象のフィールドが必要です。")

        # corporate_number = update_fields["corporate_number"]
        # agreement_category = update_fields["agreement_category"]
        # org_id = update_fields["org_id"]

        with get_scoped_session(logger) as session:
            logger.info(f"建物情報単体更新処理開始（keys: {keys}）")

            #            set_clauses = [f"{key} = :{key}" for key in update_fields.keys()]
            #            set_clause_str = ", ".join(set_clauses)

            #            sql = text(
            #                f"""
            #                UPDATE db_corp.m_building
            #                SET {set_clause_str},
            #                    updated_by = :updated_by,
            #                    updated_at = CURRENT_TIMESTAMP
            #                WHERE corporate_number = :corporate_number
            #                AND agreement_category = :agreement_category
            #                AND org_id = :org_id
            #                AND building_id = :building_id
            #            """)

            #            params = {
            #                **update_fields,
            #                "updated_by": updated_by,
            #                **keys
            #            }

            # UPDATE の values() に渡すバインドパラメータを定義
            values_map = {k: bindparam(k) for k in update_fields.keys()}
            values_map.update(
                updated_by=bindparam("updated_by"), updated_at=func.current_timestamp()
            )

            # WHERE 句の条件も bindparam で定義
            sql = (
                update(MBuilding)
                .where(
                    MBuilding.corporate_number == bindparam("b_corporate_number"),
                    MBuilding.agreement_category == bindparam("b_agreement_category"),
                    MBuilding.org_id == bindparam("b_org_id"),
                    MBuilding.building_id == bindparam("b_building_id"),
                )
                .values(**values_map)
            )

            # 実行時に渡すパラメータ辞書
            params = {**update_fields, "updated_by": updated_by, **keys}

            logger.info(f"[単体更新SQL] {sql}")
            logger.info(f"[パラメータ] {params}")

            try:
                session.execute(sql, params)
                session.commit()
            except Exception as e:
                logger.error("建物情報単体更新時に例外発生\n" + traceback.format_exc())
                raise
