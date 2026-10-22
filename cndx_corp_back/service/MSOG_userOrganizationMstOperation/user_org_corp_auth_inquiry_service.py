import os

from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSOG_userOrganizationMstOperation.user_org_corp_auth_inquiry_component import (
    UserOrgCorpAuthInquiryComponent,
)


class UserOrgCorpAuthInquiryService:

    @service
    def get_user_org_corps_info(self, request_dict: dict, logger=None):
        """
        企業組織詳細情報取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 不要なパラメータを除外
        # ファイル転送 comp を呼出
        return UserOrgCorpAuthInquiryComponent().execute(request_dict)
