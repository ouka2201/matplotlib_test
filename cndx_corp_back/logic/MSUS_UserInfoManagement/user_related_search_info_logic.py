import os

import pandas as pd
from flask import abort, current_app
from sqlalchemy import and_, collate, distinct, func, join, or_, select
from sqlalchemy.orm import aliased

from cndx_corp_back.common.db_base_handler import BaseRepository
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.utils.utils import get_message


class UserRelatedSearchInfoLogic:
    @component
    def get_company_name(self, request_dict, session, role_id, user_id, logger=None):
        """
        企業名検索処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            conditions = []
            # デフォルトのFROM句: MUserOrganizationInfo のみ
            from_clause = MUserOrganizationInfo

            # 権限ID：9(地銀本店管理者) の場合,FROM句をを変更
            if role_id in ("9"):
                from_clause = join(
                    MUserOrganizationInfo,
                    MUser,
                    and_(
                        MUser.org_id == MUserOrganizationInfo.org_id,
                        MUser.user_id == user_id,
                        MUser.delete_flg.is_(False),
                    ),
                )

            # メインクエリ
            sql = (
                select(
                    MUserOrganizationInfo.company_code,
                    MUserOrganizationInfo.bank_code,
                    MUserOrganizationInfo.branch_code,
                    MUserOrganizationInfo.org_id,
                    MUserOrganizationInfo.org_name,
                    MUserOrganizationInfo.company_name,
                    MUserOrganizationInfo.org_type_code,
                )
                .select_from(from_clause)
                .order_by(
                    collate(MUserOrganizationInfo.company_name, "C").asc(),
                    collate(MUserOrganizationInfo.org_name, "C").asc(),
                    collate(MUserOrganizationInfo.org_id, "C").asc(),
                )
            )
            # 条件リストを作る
            conditions.append(MUserOrganizationInfo.delete_flg.is_(False))
            # parent_org_id が NULL のレコードに絞る
            conditions.append(MUserOrganizationInfo.parent_org_id.is_(None))

            # 一括フィルタ
            sql = sql.where(*conditions)
            # ログ出力
            compiled = sql.compile(
                dialect=session.connection().dialect,
                compile_kwargs={"literal_binds": True},
            )
            logger.info(f"実行SQL: {compiled}")
            # SQL実行
            df_corporate = pd.read_sql(sql, session.connection())

        # 予期せぬエラーを捕捉し、上位層に処理を委譲
        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}の処理が失敗しました。")
            raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_corporate.to_dict(orient="records")

    @component
    def get_user_status(self, request_dict, session, logger=None):
        """
        ユーザーステータス検索処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            # メインクエリ
            sql = (
                select(
                    MCorpCodeInfo.code,
                    MCorpCodeInfo.jp_code_name,
                )
                .select_from(MCorpCodeInfo)
                .distinct()
                .order_by(MCorpCodeInfo.code.asc())
                .where(
                    and_(
                        MCorpCodeInfo.code_type == "USER_STATUS",
                        MCorpCodeInfo.delete_flg.is_(False),
                    )
                )
            )
            # ログ出力
            compiled = sql.compile(
                dialect=session.connection().dialect,
                compile_kwargs={"literal_binds": True},
            )
            logger.info(f"実行SQL: {compiled}")
            # SQL実行
            df_corporate = pd.read_sql(sql, session.connection())

        # 予期せぬエラーを捕捉し、上位層に処理を委譲
        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}の処理が失敗しました。")
            raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_corporate.to_dict(orient="records")

    @component
    def get_branch_name(self, request_dict, session, logger=None):
        """
        支店名検索処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            req_org_id = request_dict.get("org_id")
            if not req_org_id or "BNK" not in req_org_id:
                abort(400, description=get_message("NOT_CORRECT", data="組織ID"))

            # メインクエリ
            sql = (
                select(
                    MUserOrganizationInfo.branch_code,
                    MUserOrganizationInfo.branch_name,
                    MUserOrganizationInfo.org_type_code,
                )
                .select_from(MUserOrganizationInfo)
                .distinct()
                .order_by(MUserOrganizationInfo.branch_name.asc())
            )

            # 条件リストを作る
            conditions = []
            conditions.append(MUserOrganizationInfo.delete_flg.is_(False))
            # 親組織と子組織を検索条件に追加
            if req_org_id:
                conditions.append(
                    or_(
                        MUserOrganizationInfo.org_id == req_org_id,
                        MUserOrganizationInfo.parent_org_id == req_org_id,
                    )
                )

            # 一括フィルタ
            branch_name = request_dict.get("branch_name")
            if branch_name:
                conditions.append(
                    MUserOrganizationInfo.branch_name.like(f"%{branch_name}%")
                )
            sql = sql.where(*conditions)

            # ログ出力
            compiled = sql.compile(
                dialect=session.connection().dialect,
                compile_kwargs={"literal_binds": True},
            )
            logger.info(f"実行SQL: {compiled}")
            # SQL実行
            df_corporate = pd.read_sql(sql, session.connection())

        # 予期せぬエラーを捕捉し、上位層に処理を委譲
        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}の処理が失敗しました。")
            raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_corporate.to_dict(orient="records")

    @component
    def get_user_role(self, request_dict, session, logger=None):
        """
        ユーザー権限検索処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            # メインクエリ
            sql = (
                select(
                    MCorpCodeInfo.code,
                    MCorpCodeInfo.jp_code_name,
                )
                .select_from(MCorpCodeInfo)
                .distinct()
                .order_by(MCorpCodeInfo.code.asc())
                .where(
                    and_(
                        MCorpCodeInfo.code_type == "ROLE_TYPE",
                        MCorpCodeInfo.delete_flg.is_(False),
                    )
                )
            )
            # ログ出力
            compiled = sql.compile(
                dialect=session.connection().dialect,
                compile_kwargs={"literal_binds": True},
            )
            logger.info(f"実行SQL: {compiled}")
            # SQL実行
            df_corporate = pd.read_sql(sql, session.connection())

        # 予期せぬエラーを捕捉し、上位層に処理を委譲
        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}の処理が失敗しました。")
            raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_corporate.to_dict(orient="records")
