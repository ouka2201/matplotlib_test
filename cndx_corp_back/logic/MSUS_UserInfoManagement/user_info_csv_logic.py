import os
from io import StringIO

import numpy as np
import pandas as pd
from flask import current_app
from sqlalchemy import and_, select
from sqlalchemy.orm import aliased

import cndx_corp_back.query.common_queries as Queries
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.entity.t_last_login_info import TLastLoginInfo

# CSV出力のエンコーディングとエラーハンドリングを定義
CSV_ENCODING = "shift_jis"
CSV_ERRORS = "ignore"


class UserInfoCsvLogic:
    @component
    def introduction(
        self, request_dict, session, user_id, role_id, org_id, logger=None
    ):
        """
        ユーザー一覧検索処理
        SELECTした結果を CSVとして返すジェネレータ
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        conditions = []
        # 権限ID：9(地銀本店管理者) の場合
        if role_id is not None and role_id in ("9"):
            role_stmt = Queries.get_user_role(session, user_id, org_id, role_id, logger)
            df_role = pd.read_sql(role_stmt, session.connection(), params=request_dict)
            if str(role_id) == "9" and "child_org_id" in df_role.columns:
                child_org_ids = (
                    df_role["child_org_id"].dropna().astype(str).unique().tolist()
                )
            else:
                child_org_ids = []
            conditions.append(MUser.org_id.in_([org_id] + child_org_ids))

        # メインクエリ
        RoleInfo = aliased(MCorpCodeInfo, name="RoleInfo")
        StatusInfo = aliased(MCorpCodeInfo, name="StatusInfo")
        sql = (
            select(
                MUser.user_id,
                MUserOrganizationInfo.company_name,
                MUserOrganizationInfo.branch_name,
                MUser.user_name,
                MUser.email_address,
                RoleInfo.jp_code_name.label("user_role_name"),
                StatusInfo.jp_code_name.label("user_status_name"),
                MUser.start_date,
                MUser.end_date,
                TLastLoginInfo.last_login_datetime,
                MUser.delete_flg,
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
            .order_by(MUser.company_name.asc())
        )
        sql = sql.where(*conditions)

        try:
            compiled = sql.compile(
                dialect=session.connection().dialect,
                compile_kwargs={"literal_binds": True},
            )
            logger.info(f"実行SQL (MAIN): {compiled}")

            df_corporate = pd.read_sql(sql, session.connection())

        except Exception as e:
            logger.error(f"SQL実行中にエラーが発生しました: {e}")
            raise

        # CSV出力前準備

        # ユーザーIDがNULLの行を排除
        df_corporate = df_corporate.dropna(subset=["user_id"])

        # 対象の日付カラムリストと定義
        datetime_cols = ["start_date", "end_date", "last_login_datetime"]

        # 日付・時刻カラムのJST変換とフォーマット処理
        for col in datetime_cols:
            if col in df_corporate.columns:
                try:
                    dt_series = pd.to_datetime(df_corporate[col], errors="coerce")
                    if dt_series.dt.tz is not None:
                        dt_series = dt_series.dt.tz_localize(None)
                    formatted_series = dt_series.dt.strftime("%Y/%m/%d %H:%M:%S")

                    is_nat = dt_series.isna()
                    df_corporate[col] = formatted_series
                    df_corporate.loc[is_nat, col] = None

                except Exception as e:
                    logger.error(f"Failed to process datetime for column {col}: {e}")
                    pass

        # 欠損値（NaN, NaTなど）を全てPythonのNoneに変換する
        df_corporate = df_corporate.replace({np.nan: None})

        # CSVデータ生成

        # 最終的にCSVに出力するカラム順序と日本語ヘッダーを定義
        csv_columns_map = {
            "company_name": "企業名",
            "branch_name": "支店名",
            "user_name": "氏名",
            "email_address": "メールアドレス",
            "user_role_name": "権限",
            "user_status_name": "ステータス",
            "start_date": "利用開始日",
            "end_date": "利用終了日",
            "last_login_datetime": "最終ログイン日",
            "delete_flg": "削除フラグ",
        }

        # DataFrameを必要なカラムと順序に絞り込み、カラム名を日本語にリネーム
        df_output = df_corporate[list(csv_columns_map.keys())].rename(
            columns=csv_columns_map
        )

        def csv_generator():
            try:
                output_buffer = StringIO()
                # to_csvで全データをバッファに書き込む
                df_output.to_csv(
                    output_buffer,
                    index=False,
                    header=True,
                    encoding="utf-8",
                    sep=",",
                    lineterminator="\r\n",
                )

                # バッファの内容全体を取得し、指定されたSJISにエンコードして yield
                csv_bytes = output_buffer.getvalue().encode(
                    CSV_ENCODING, errors=CSV_ERRORS
                )
                yield csv_bytes

            except Exception as e:
                logger.error(f"CSVデータ生成ジェネレータ内でエラーが発生: {e}")
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        # CSVデータのジェネレータを返す
        return csv_generator()
