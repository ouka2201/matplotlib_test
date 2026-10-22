import os
from re import match

import pandas as pd
from flask import current_app

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSUS_UserInfoManagement.user_info_logout_logic import (
    UserInfoLogoutLogic,
)


class UserInfoLogoutService:
    @service
    def upd_user_info(self, request_dict: dict, user_id, logger=None):
        """
        ユーザー一括失効処理
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        logic = UserInfoLogoutLogic()
        with get_scoped_session() as session:
            try:
                result = logic.introduction(request_dict, session, user_id)
            except Exception as e:
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result
