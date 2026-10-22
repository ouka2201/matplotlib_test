import os
from collections import defaultdict

import pandas as pd
from flask import abort, current_app
from sqlalchemy import and_, literal

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_organization_authority_info_entity import (
    MOrganizationAuthorityInfo,
)
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)
from cndx_corp_back.utils.utils import get_message


# 利用者組織情報照会
class UserOrgCorpAuthInquiryComponent:

    @component
    def execute(self, request_dict: dict, logger=None):

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        with get_scoped_session() as session:
            # 組織IDがある場合、その組織IDの組織情報検索
            if request_dict.get("org_id"):
                org_authority_info_list = (
                    session.query(
                        MUserOrganizationInfo.org_id,
                        MUserOrganizationInfo.org_name,
                        MUserOrganizationInfo.company_code,
                        MUserOrganizationInfo.company_name,
                        MUserOrganizationInfo.bank_code,
                        MUserOrganizationInfo.branch_code,
                        MUserOrganizationInfo.branch_name,
                        MUserOrganizationInfo.org_type_code,
                        MUserOrganizationInfo.org_type,
                        # MUserOrganizationInfo.agreement_code,
                        # MUserOrganizationInfo.agreement_name,
                        MUserOrganizationInfo.business_type,
                        MOrganizationAuthorityInfo.authority_id,
                        MOrganizationAuthorityInfo.authority_code,
                        MOrganizationAuthorityInfo.user_role,
                        MOrganizationAuthorityInfo.screen_name,
                    )
                    .join(
                        MUserOrganizationInfo,
                        and_(
                            MUserOrganizationInfo.org_type_code
                            == MOrganizationAuthorityInfo.org_type_code
                        ),
                    )
                    .where(
                        MUserOrganizationInfo.org_id == request_dict["org_id"],
                        MUserOrganizationInfo.delete_flg == False,
                        MOrganizationAuthorityInfo.delete_flg == False,
                    )
                    .all()
                )
            # 組織IDがない場合、新規登録なので、組織権限情報全件検索
            else:
                org_authority_info_list = (
                    session.query(
                        literal("").label("org_id"),
                        literal("").label("org_name"),
                        MOrganizationAuthorityInfo.org_type_code,
                        MOrganizationAuthorityInfo.org_type,
                        literal("").label("company_code"),
                        literal("").label("company_name"),
                        literal("").label("bank_code"),
                        literal("").label("branch_code"),
                        literal("").label("branch_name"),
                        # literal("").label("agreement_code"),
                        # literal("").label("agreement_name"),
                        literal("").label("business_type"),
                        MOrganizationAuthorityInfo.authority_id,
                        MOrganizationAuthorityInfo.authority_code,
                        MOrganizationAuthorityInfo.user_role,
                        MOrganizationAuthorityInfo.screen_name,
                    )
                    .where(MOrganizationAuthorityInfo.delete_flg == False)
                    .all()
                )

        # マスタリストは空の場合、エラー返す
        if len(org_authority_info_list) == 0:
            abort(
                412, description=get_message("NOT_CORRECT", field="組織情報マスタ情報")
            )

        # listをdfへ変換
        df_org_authority = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in org_authority_info_list
            ]
        )
        # dictへ変換
        dict_org_authority = df_org_authority.to_dict(orient="records")

        # 指定の合併項目オブジェクト精製
        grouped = defaultdict(list)

        # ストラクチャ再構成
        for item in dict_org_authority:
            key = (
                item["org_id"],
                item["org_name"],
                item["company_code"],
                item["company_name"],
                item["bank_code"],
                item["branch_code"],
                item["branch_name"],
                item["org_type_code"],
                item["org_type"],
                # item["agreement_code"],
                # item["agreement_name"],
                item["business_type"],
            )
            grouped[key].append(
                {
                    "authority_id": item["authority_id"],
                    "authority_code": item["authority_code"],
                    "screen_name": item["screen_name"],
                    "user_role": item["user_role"],
                }
            )

        # ターゲットストラクチャ作成
        result = []
        for key, authorities in grouped.items():
            (
                org_id,
                org_name,
                company_code,
                company_name,
                bank_code,
                branch_code,
                branch_name,
                org_type_code,
                org_type,
                # agreement_code,
                # agreement_name,
                business_type,
            ) = key
            result.append(
                {
                    "org_id": org_id,
                    "org_name": org_name,
                    "company_code": company_code,
                    "company_name": company_name,
                    "bank_code": bank_code,
                    "branch_code": branch_code,
                    "branch_name": branch_name,
                    "org_type_code": org_type_code,
                    "org_type": org_type,
                    # "agreement_code": agreement_code,
                    # "agreement_name": agreement_name,
                    "business_type": business_type,
                    "authorities": authorities,
                }
            )

        # 利用者組織情報返す
        return result
