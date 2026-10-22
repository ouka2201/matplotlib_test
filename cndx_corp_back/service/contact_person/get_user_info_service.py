import os

import pandas as pd
from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.contact_person.contact_person_logic import ContactPersonLogic


class ContactPersonGetUserInfoService:

    @service
    def get_user_info(self, request_dict: dict, user_context=None, logger=None):
        """
        追加担当者のユーザー情報取得処理
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        ## SQL処理（ユーザー情報取得）
        result = ContactPersonLogic.getUserInfo(self, request_dict, user_context)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result
