import os

import pandas as pd
from flask import current_app, jsonify
from sqlalchemy import and_, or_, select

import cndx_corp_back.common.constants_values as constants_values
import cndx_corp_back.query.common_queries as Queries
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo


class ContactPersonAgreementUserGetLogic:

    # component
    # def getBuildingInfo(self, request_dict, logger=None):
    #     """
    #     拠点マスタから、同意書取得組織として登録されているデータを取得検索処理
    #     """
    #     try:
    #         with get_scoped_session() as session:
    #             stmt = session.query(MBuilding).where(
    #                 and_(
    #                     MBuilding.corporate_number == request_dict["corporate_number"],
    #                     MBuilding.agreement_org.in_(request_dict["org_id"]),
    #                     MBuilding.delete_flg.is_not(True)
    #                 )
    #             )

    #             compiled = stmt.statement.compile(
    #                 compile_kwargs={"literal_binds": True}
    #             )
    #             logger.info(f"実行SQL: {compiled}")

    #             building_stmt = stmt.all()
    #             logger.info(f"件数: {len(building_stmt)}")

    #             return building_stmt.to_dict(orient="records")
    #     except Exception as e:
    #         # エラー時は空リスト返す（必要に応じてログ出力）
    #         print(e)
    #         return []

    # def getBuildingInfo(self, request_dict, logger=None):
    #     """
    #     拠点マスタから、同意書取得組織として登録されているデータを取得検索処理
    #     """

    #     if logger is None:
    #         logger = current_app.logger

    #     try:
    #         with get_scoped_session() as session:

    #             stmt = (
    #                 session.query(MUserOrganizationInfo, MBuilding)
    #                 .join(
    #                     MBuilding,
    #                     or_(
    #                         MUserOrganizationInfo.org_id == MBuilding.agreement_org,
    #                         MUserOrganizationInfo.parent_org_id == MBuilding.agreement_org
    #                     ),
    #                     isouter=True  # LEFT JOIN
    #                 )
    #                 .filter(
    #                     MBuilding.corporate_number == request_dict["corporate_number"],
    #                     MUserOrganizationInfo.org_id == request_dict["org_id"],
    #                     MBuilding.delete_flg.is_not(True)
    #                 )
    #             )

    #             compiled = stmt.statement.compile(
    #                 dialect=session.connection().dialect,
    #                 compile_kwargs={"literal_binds": True}
    #             )
    #             logger.info(f"実行SQL: {compiled}")

    #             df_building = pd.read_sql(
    #                 stmt.statement,
    #                 session.connection()
    #             )

    #             logger.info(f"件数: {len(df_building)}")

    #             return df_building.to_dict(orient="records")

    #     except Exception as e:
    #         logger.exception("getBuildingInfo エラー")
    #         return []
    def getBuildingInfo(self, request_dict, logger=None):
        """
        拠点マスタから、同意書取得組織として登録されているデータを取得検索処理
        """
        if logger is None:
            logger = current_app.logger

        results = []

        try:
            with get_scoped_session() as session:
                for org_id in request_dict["org_id"]:
                    stmt = (
                        session.query(MBuilding.corporate_number)
                        .select_from(MBuilding)
                        .outerjoin(
                            MUserOrganizationInfo,
                            or_(
                                MUserOrganizationInfo.org_id == MBuilding.agreement_org,
                                MUserOrganizationInfo.parent_org_id
                                == MBuilding.agreement_org,
                            ),
                        )
                        .filter(
                            MBuilding.corporate_number
                            == request_dict["corporate_number"],
                            MUserOrganizationInfo.org_id == org_id,
                            MBuilding.delete_flg.is_not(True),
                        )
                    )

                    compiled = stmt.statement.compile(
                        dialect=session.connection().dialect,
                        compile_kwargs={"literal_binds": True},
                    )
                    logger.info(f"[org_id={org_id}] 実行SQL: {compiled}")

                    df = pd.read_sql(stmt.statement, session.connection())

                    logger.info(f"[org_id={org_id}] 件数: {len(df)}")

                    if len(df) > 0:
                        results.append(df)
                    else:
                        return df.to_dict(orient="records")

                if results:
                    final_df = pd.concat(results, ignore_index=True)
                    return final_df.to_dict(orient="records")
                else:
                    return []

        except Exception:
            logger.exception("getBuildingInfo エラー")
            return []
