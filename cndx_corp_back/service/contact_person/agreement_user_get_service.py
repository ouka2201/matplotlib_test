import os

import pandas as pd
from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.contact_person.agreement_user_get_logic import (
    ContactPersonAgreementUserGetLogic,
)


class ContactPersonAgreementUserGetService:

    @service
    def get_buiding_info(self, request_dict: dict, logger=None):
        """
        追加担当者のユーザー情報取得処理
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        ## SQL処理（ユーザー情報取得）
        result = ContactPersonAgreementUserGetLogic.getBuildingInfo(
            self, request_dict, logger
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result
