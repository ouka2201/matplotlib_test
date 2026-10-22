import os

import pandas as pd
from flask import current_app
from sqlalchemy import literal
from sqlalchemy.sql import collate, func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)


# 利用者組織情報照会
class UserOrgCorpsInquiryComponent:

    @component
    def execute(self, request_dict, logger=None):

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        org_name = request_dict.get("org_name", "")
        org_type_code = request_dict.get("org_type_code", "")
        org_id = request_dict.get("org_id", "")

        with get_scoped_session() as session:
            query = (
                session.query(
                    MUserOrganizationInfo.org_id,
                    MUserOrganizationInfo.org_name,
                    MUserOrganizationInfo.org_type,
                    MUserOrganizationInfo.org_type_code,
                    MUserOrganizationInfo.company_name,
                )
                .filter(MUserOrganizationInfo.delete_flg == False)
                .order_by(
                    collate(MUserOrganizationInfo.company_name, "C").asc(),
                    # MUserOrganizationInfo.org_name,
                    collate(MUserOrganizationInfo.org_id, "C").asc(),
                )
            )

            # 空の場合、検索条件にならない
            if org_name:
                query = query.filter(
                    MUserOrganizationInfo.org_name.ilike(f"%{org_name}%")
                )

            if org_type_code:
                query = query.filter(
                    MUserOrganizationInfo.org_type_code.ilike(f"%{org_type_code}%")
                )

            if org_id:
                query = query.filter(MUserOrganizationInfo.org_id.ilike(f"%{org_id}%"))

            m_user_organization_infos = query.all()

            # listをdfへ変換
            res = pd.DataFrame(
                [
                    {field: getattr(row, field) for field in row._fields}
                    for row in m_user_organization_infos
                ]
            )

            # dictの形式で
            return res.to_dict(orient="records")
