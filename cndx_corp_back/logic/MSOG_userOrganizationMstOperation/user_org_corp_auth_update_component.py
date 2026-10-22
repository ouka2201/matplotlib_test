import datetime

import pandas as pd
from flask import abort, current_app

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)
from cndx_corp_back.utils.utils import get_message


# 企業組織基本情報更新コンポネント
class UserOrgCorpAuthUpdateComponent:

    @component
    def execute(self, request_dict: dict, user_context, logger=None):

        if logger is None:
            logger = current_app.logger

        with get_scoped_session() as session:

            # 既存企業組織情報取得
            corporate_organization_info = (
                session.query(MUserOrganizationInfo)
                .filter_by(org_id=request_dict["org_id"])
                .all()
            )

            # 既存情報存在しない場合、エラー
            if len(corporate_organization_info) == 0:
                abort(
                    400,
                    description=get_message("NOT_FOUND", item_name="企業の組織情報"),
                )

            # 企業組織基本情報登録
            self.user_organization_info_update(
                session, corporate_organization_info, request_dict, user_context
            )

            session.commit()

    def user_organization_info_update(
        self, session, corporate_organization_infos, df_orgCorpAuth, user_context
    ):
        """
        企業組織基本情報更新処理
        """
        for row in corporate_organization_infos:
            row.org_id = df_orgCorpAuth["org_id"]  # 組織ID
            row.org_name = df_orgCorpAuth["org_name"]  # 組織名
            # row.org_name = df_orgCorpAuth['parent_org_id']                    #親組織名
            row.company_name = df_orgCorpAuth["company_name"]  # 会社名
            row.company_code = df_orgCorpAuth["company_code"]  # 会社コード
            row.bank_code = df_orgCorpAuth["bank_code"]  # 銀行コード
            row.branch_code = df_orgCorpAuth["branch_code"]  # 支店コード
            row.branch_name = df_orgCorpAuth["branch_name"]  # 支店名
            row.org_type_code = df_orgCorpAuth["org_type_code"]  # 組織種別コード
            row.org_type = df_orgCorpAuth["org_type"]  # 組織種別
            # row.agreement_code = df_orgCorpAuth['agreement_code']             #同意書取得経路コード
            # row.agreement_name = df_orgCorpAuth['agreement_name']             #同意書取得経路
            row.business_type = df_orgCorpAuth["business_type"]  # 事業者区分
            row.updated_by = user_context.get("user_id")  # 更新者
            # row.updated_at = self.get_current_timestamp()                     #更新日時
            # session.add(row)
            break

    def get_current_timestamp(self):

        local_time = datetime.datetime.now()
        return local_time.strftime("%Y-%m-%d %H:%M:%S")
