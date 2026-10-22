import os

from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSOG_userOrganizationMstOperation.user_org_corp_auth_register_component import (
    UserOrgCorpAuthRegisterComponent,
)


class UserOrgCorpAuthRegisterSerivce:

    @service
    def user_org_corp_auth_register(
        self, request_dict: dict, user_context, logger=None
    ):
        """
        企業組織一覧情報新規登録
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 不要なパラメータを除外
        # ファイル転送 comp を呼出
        return UserOrgCorpAuthRegisterComponent().execute(request_dict, user_context)
