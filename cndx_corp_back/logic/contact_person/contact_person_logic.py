import os

import pandas as pd
from flask import current_app
from sqlalchemy import and_, collate, or_, select

import cndx_corp_back.common.constants_values as constants_values
import cndx_corp_back.query.common_queries as Queries
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo


# 企業基本情報照会
class ContactPersonLogic:
    @component
    def introduction(
        self, request_dict, user_id, role_id, org_type_code, org_id, logger=None
    ):
        """
        共通_お客様情報検索処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        with get_scoped_session() as session:

            sql = Queries.get_basic_information(
                request_dict, user_id, role_id, org_type_code, org_id
            )
            conditions = []
            # 事業者区分：金融機関 REP TCS の場合
            if org_type_code in ("02", "03", "04", "05"):
                # 地銀の絞り込みに必要な情報を取得
                role_stmt = Queries.get_user_role(
                    session, user_id, org_id, role_id, logger
                )
                df_role = pd.read_sql(
                    role_stmt, session.connection(), params=request_dict
                )
                if len(df_role) > 0:
                    row = df_role.iloc[0]
                else:
                    return
                business_type = row["business_type"]
                agreement_category = (
                    df_role["agreement_category"].dropna().astype(str).unique().tolist()
                )
                corporate_number = (
                    df_role["corporate_number"].dropna().astype(str).unique().tolist()
                )
                # role_id が "9" の場合のみ child_org_ids を生成し、それ以外は空リストにする
                if str(role_id) == "9" and "child_org_id" in df_role.columns:
                    child_org_ids = (
                        df_role["child_org_id"].dropna().astype(str).unique().tolist()
                    )
                else:
                    child_org_ids = []

                # 権限対応フィルタ生成（金融機関の場合）
                if business_type == "金融機関":
                    conditions.append(
                        MCorporateDetailsInfo.agreement_category
                        == MStaffInfo.agreement_category
                    )
                    # org_id フィルタ（role=9の場合、子組織も含む）
                    if role_id == "9":
                        conditions.append(
                            MStaffInfo.org_id.in_([org_id] + child_org_ids)
                        )
                    elif role_id == "0":
                        conditions.append(MStaffInfo.org_id == org_id)
                    if role_id == "1":
                        conditions.append(MStaffInfo.user_id == user_id)
                # 権限対応フィルタ生成（REP TCSの場合）
                elif business_type in ("REP", "TCS"):
                    # org_id で絞る
                    # conditions.append(MStaffInfo.org_id == org_id)
                    if role_id == "1":
                        conditions.append(MStaffInfo.user_id == user_id)
                    elif role_id == "0":
                        conditions.append(MStaffInfo.org_id == org_id)

                # corporate_number が渡ってきたら、corporate_number で絞り込む（担当者情報マスタの登録有無確認のため）
                if corporate_number and len(corporate_number) > 0:
                    # リストが空でない場合のみ IN 句を使用
                    conditions.append(
                        MCorporateBasic.corporate_number.in_(corporate_number)
                    )
                elif corporate_number is not None and len(corporate_number) == 0:
                    # リストが空の場合（営業担当登録がない）、空の結果を返す
                    conditions.append(MCorporateBasic.corporate_number.is_(None))
                # corporate_number が None の場合は条件を追加しない（全件検索）

            # 事業者区分：可視化事業者 の場合
            elif org_type_code == "06":
                # org_id ごとの agreement_category マップ
                code_map = {
                    "REP": "11",
                    "ASE": "12",
                    "ZRB": "13",
                    "JFS": "14",
                }
                # org_id がマップにあれば、一度にまとめて追加
                if (cate := code_map.get(org_id)) is not None:
                    conditions.extend(
                        [
                            MCorporateDetailsInfo.agreement_category == cate,
                            # MStaffInfo.user_id == user_id,
                        ]
                    )

            # 追加で、同意書未取得だけ除外
            # conditions.append(MCorporateDetailsInfo.agreement_category != "00")

            # 一括フィルタ
            sql = sql.where(*conditions)
            sql = sql.order_by(
                collate(MCorporateBasic.company_name, "C").asc(),
                collate(MCorporateBasic.corporate_number, "C").asc(),
            )
            # ログ出力
            compiled = sql.compile(
                dialect=session.connection().dialect,
                compile_kwargs={"literal_binds": True},
            )
            logger.info(f"実行SQL: {compiled}")
            # SQL実行
            df_corporate = pd.read_sql(sql, session.connection())

        company_address = (request_dict.get("company_address") or "").strip()

        if company_address:
            df_corporate = df_corporate[
                df_corporate["company_address"].str.contains(
                    company_address, na=False, regex=False
                )
            ]

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        if "staff" in (request_dict.get("page_info") or "").strip():
            df_corporate = df_corporate.drop(
                columns=["agreement_category"], errors="ignore"
            )
            df_corporate = df_corporate.drop_duplicates(subset=["corporate_number"])

        return df_corporate.to_dict(orient="records")

    @component
    def getCompanyInfo(
        self,
        dict_request_data,
        login_user_id=None,
        role_id=None,
        org_type_code=None,
        org_id=None,
        logger=None,
    ):
        """
        企業情報取得処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        with get_scoped_session() as session:
            #            corporate_sql = "".join(QueryMst.CORPORATE_INFO_DETAIL.value)
            #            corporate_sql = corporate_sql + "where corporate_number =" + "'" + corporateNumber + "'"
            #            df_corporate: pd.DataFrame = pd.read_sql(corporate_sql, conn)
            sql = Queries.get_basic_information(
                dict_request_data, login_user_id, role_id, org_type_code, org_id
            )
            df_corporate = pd.read_sql(sql, session.connection())

            logger.info(f"実行SQL: {sql} ")
            logger.info(f"データ: {df_corporate} ")

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return df_corporate.head(1).to_dict(orient="records")

    @component
    def getContactPersonList(self, corporateNumber, org_type_code, logger=None):
        """
        担当者情報取得処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        with get_scoped_session() as session:

            ## 利用者組織情報取得
            #            contact_person_list_sql = "".join(QueryMst.CONTACT_PERSON_LIST.value)
            #            contact_person_list_sql = contact_person_list_sql + "and si.corporate_number =" + "'" + corporateNumber + "'"
            #            df_contact_person: pd.DataFrame = pd.read_sql(contact_person_list_sql, conn)
            sql = (
                select(
                    MStaffInfo.user_id,
                    MUserOrganizationInfo.org_id,
                    MUserOrganizationInfo.org_name,
                    MUser.user_name,
                    MUser.email_address,
                    MStaffInfo.corporate_number,
                    MStaffInfo.agreement_category,
                    MStaffInfo.consent_receipt_date,
                )
                .select_from(MStaffInfo)
                .join(
                    MUserOrganizationInfo,
                    and_(
                        MStaffInfo.org_id == MUserOrganizationInfo.org_id,
                        MUserOrganizationInfo.delete_flg.is_(False),
                    ),
                )
                .join(
                    MUser,
                    and_(
                        MStaffInfo.user_id == MUser.user_id, MUser.delete_flg.is_(False)
                    ),
                )
                .where(
                    MStaffInfo.corporate_number == corporateNumber,
                    MStaffInfo.delete_flg.is_(False),
                )
                .distinct()
                .order_by(MStaffInfo.consent_receipt_date.asc())
            )
            df_contact_person = pd.read_sql(sql, session.connection())
            # 地銀本店の場合、自行のみ情報絞り

            if org_type_code == "02":
                df_contact_person = df_contact_person[
                    df_contact_person["org_id"].str.startswith(
                        constants_values.BANK_ORGANIZATION_MARK
                    )
                ]

            logger.info(f"実行SQL: {sql} ")
            logger.info(f"データ: {df_contact_person} ")

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_contact_person.to_dict(orient="records")

    @component
    def getUserInfo(self, params: dict, user_context, logger=None):
        """
        担当者IDから担当者情報の取得処理
        """
        role_id = user_context.get("org_type_code")

        org_id = user_context.get("org_id")

        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 利用者組織情報テーブルの利用者企業コードと紐付くユーザーの取得
        with get_scoped_session() as session:

            sql = (
                select(
                    MUser.user_id,
                    MUserOrganizationInfo.org_name,
                    MUserOrganizationInfo.org_type_code,
                    MUser.user_name,
                    MUser.org_id,
                    MUser.user_role,
                    MUser.email_address,
                )
                .select_from(MUser)
                .join(
                    MUserOrganizationInfo,
                    and_(
                        MUser.org_id == MUserOrganizationInfo.org_id,
                        MUserOrganizationInfo.delete_flg.is_(False),
                    ),
                )
                .where(
                    MUser.email_address == params.get("email_address"),
                    MUser.delete_flg.is_(False),
                )
                .order_by(MUser.user_id.asc())
            )

            # ---- 追加の絞り込み（role_id == 9 のときのみ）----
            if role_id == "02":
                req_org_id = org_id

                child_org_ids_subq = select(MUserOrganizationInfo.org_id).where(
                    MUserOrganizationInfo.parent_org_id == req_org_id,
                    MUserOrganizationInfo.delete_flg.is_(False),
                )

                sql = sql.where(
                    or_(
                        MUserOrganizationInfo.org_id == req_org_id,
                        MUserOrganizationInfo.org_id.in_(child_org_ids_subq),
                    )
                )

            df_user = pd.read_sql(sql, session.connection())
            logger.debug(f"実行SQL: {sql} ")
            logger.debug(f"データ: {df_user} ")

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_user.to_dict(orient="records")
