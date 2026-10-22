import os
from datetime import datetime

from flask import current_app
from sqlalchemy import text

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.query.contact_person_query import QueryMst


# 企業基本情報更新
class ContactPersonDeleteLogic:

    @component
    def delete(self, target_dict, login_user_id=None, logger=None):

        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        with get_scoped_session() as session:
            for info in target_dict.values():
                session.query(MStaffInfo).filter_by(
                    corporate_number=info["corporate_number"],
                    agreement_category=info["agreement_category"],
                    org_id=info["org_id"],
                    user_id=info["user_id"],
                ).update(
                    {
                        "delete_flg": True,
                        "updated_by": login_user_id,
                    },
                    synchronize_session=False,
                )
            session.commit()
        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return
