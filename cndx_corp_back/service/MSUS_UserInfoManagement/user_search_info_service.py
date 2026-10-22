import os
from re import match

import pandas as pd
from flask import current_app

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSUS_UserInfoManagement.user_search_info_logic import (
    UserSearchInfoLogic,
)


class UserSearchInfoService:
    @service
    def get_user_info(self, request_dict: dict, user_id, role_id, org_id, logger=None):
        """
        ユーザー情報一覧取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        with get_scoped_session() as session:
            try:
                result = UserSearchInfoLogic.introduction(
                    self, request_dict, session, user_id, role_id, org_id
                )
            except Exception as e:
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result
