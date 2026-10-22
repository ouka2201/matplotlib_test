import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from flask import current_app
from sqlalchemy import and_, case, collate, select
from sqlalchemy.orm import aliased

import cndx_corp_back.query.common_queries as Queries
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)
from cndx_corp_back.entity.t_last_login_info import TLastLoginInfo


class UserSearchInfoLogic:
    @component
    # @log_time
    def introduction(
        self, request_dict, session, user_id, role_id, org_id, logger=None
    ):
        """
        ユーザー一覧検索処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            # 共通のフィルタリング条件の作成
            conditions = []
            conditions.append(MUser.delete_flg.is_(False))

            # 検索条件の追加
            comp_info_json = request_dict.get("company_name")
            if comp_info_json:
                # 不具合管理表No61
                # JSON 文字列に変換
                data_dict = json.loads(comp_info_json)
                company_code = data_dict["company_code"]
                bank_code = data_dict["bank_code"]
                conditions.append(MUserOrganizationInfo.company_code == company_code)
                conditions.append(MUserOrganizationInfo.bank_code == bank_code)

            branch_name = request_dict.get("branch_name")
            if branch_name:
                conditions.append(
                    MUserOrganizationInfo.branch_name.like(f"%{branch_name}%")
                )

            user_name = request_dict.get("user_name")
            if user_name:
                conditions.append(MUser.user_name.like(f"%{user_name}%"))

            user_status = request_dict.get("user_status")
            if user_status:
                conditions.append(MUser.user_status.like(f"%{user_status}%"))

            # 権限ID：9(地銀本店管理者) の場合
            if role_id in ("9"):
                role_stmt = Queries.get_child_org_user(session, org_id, role_id, logger)
                df_role = pd.read_sql(
                    role_stmt, session.connection(), params=request_dict
                )
                if str(role_id) == "9" and "child_org_id" in df_role.columns:
                    child_org_ids = (
                        df_role["child_org_id"].dropna().astype(str).unique().tolist()
                    )
                else:
                    child_org_ids = []
                conditions.append(MUser.org_id.in_([org_id] + child_org_ids))

            # メインクエリを作成
            RoleInfo = aliased(MCorpCodeInfo, name="RoleInfo")
            StatusInfo = aliased(MCorpCodeInfo, name="StatusInfo")
            sql = (
                select(
                    MUser.user_id,
                    MUserOrganizationInfo.company_code,
                    MUserOrganizationInfo.company_name,
                    MUserOrganizationInfo.branch_code,
                    MUserOrganizationInfo.branch_name,
                    MUser.user_name,
                    MUser.email_address,
                    MUser.user_role,
                    RoleInfo.jp_code_name.label("user_role_name"),
                    MUser.user_status,
                    StatusInfo.jp_code_name.label("user_status_name"),
                    MUser.start_date,
                    MUser.end_date,
                    TLastLoginInfo.last_login_datetime,
                    MUserOrganizationInfo.bank_code,
                    MUserOrganizationInfo.org_id,
                )
                .select_from(MUser)
                .join(
                    MUserOrganizationInfo,
                    and_(
                        MUser.org_id == MUserOrganizationInfo.org_id,
                        MUserOrganizationInfo.delete_flg.is_(False),
                    ),
                )
                .join(
                    RoleInfo,
                    and_(
                        MUser.user_role == RoleInfo.code,
                        RoleInfo.code_type == "ROLE_TYPE",
                        RoleInfo.delete_flg.is_(False),
                    ),
                )
                .join(
                    StatusInfo,
                    and_(
                        MUser.user_status == StatusInfo.code,
                        StatusInfo.code_type == "USER_STATUS",
                        StatusInfo.delete_flg.is_(False),
                    ),
                )
                .outerjoin(
                    TLastLoginInfo,
                    and_(
                        MUser.user_id == TLastLoginInfo.user_id,
                        TLastLoginInfo.delete_flg.is_(False),
                    ),
                )
                .order_by(
                    # ① 企業名 Unicode順
                    collate(MUserOrganizationInfo.company_name, "C").asc(),
                    # ② 支店名 Unicode順
                    collate(MUserOrganizationInfo.branch_name, "C").asc(),
                    # ③ 管理者を上に表示
                    case((MUser.user_role == "0", 0), else_=1).asc(),
                    # ④ 氏名 Unicode順
                    collate(MUser.user_name, "C").asc(),
                    # ⑤ メールアドレス Unicode順
                    collate(MUser.email_address, "C").asc(),
                )
            )
            sql = sql.where(*conditions)

            # メインクエリの実行
            compiled = sql.compile(
                dialect=session.connection().dialect,
                compile_kwargs={"literal_binds": True},
            )
            logger.info(f"実行SQL (MAIN): {compiled}")
            df_corporate = pd.read_sql(sql, session.connection())

            # 後続処理

            # ユーザーIDがNULLの行を排除
            df_corporate = df_corporate.dropna(subset=["user_id"])

            # 対象の日付カラムリスト
            datetime_cols = ["start_date", "end_date", "last_login_datetime"]
            # 9999/12/31 を表す datetime オブジェクトを定義
            BLANK_DATE = datetime(9999, 12, 31)

            # 日付・時刻カラムのJST変換とフォーマット処理
            for col in datetime_cols:
                if col in df_corporate.columns:
                    try:
                        # カラムをdatetime型に変換。無効なデータは NaT に置換
                        dt_series = pd.to_datetime(df_corporate[col], errors="coerce")
                        if col in ["start_date", "end_date"]:
                            # dt_series が BLANK_DATE と等しい行を None (ブランク) に設定
                            df_corporate.loc[dt_series == BLANK_DATE, col] = None
                            dt_series = pd.to_datetime(
                                df_corporate[col], errors="coerce"
                            )
                        # タイムゾーン情報が付与されている場合は、強制的に解除
                        if dt_series.dt.tz is not None:
                            dt_series = dt_series.dt.tz_localize(None)
                        # フォーマット処理を適用
                        formatted_series = dt_series.dt.strftime("%Y/%m/%d %H:%M:%S")

                        # NaT だった（または None に置き換えられた）行は None に設定
                        is_nat = dt_series.isna()
                        df_corporate[col] = formatted_series
                        df_corporate.loc[is_nat, col] = None

                    except Exception:
                        logger.error(f"Failed to process datetime for column {col}")
                        pass
            # 欠損値（NaN, NaTなど）を全てPythonのNoneに変換する
            df_corporate = df_corporate.replace({np.nan: None})

        # 予期せぬエラーを捕捉し、上位層に処理を委譲
        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}の処理が失敗しました: {str(e)}")
            raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_corporate.to_dict(orient="records")

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_corporate.to_dict(orient="records")
