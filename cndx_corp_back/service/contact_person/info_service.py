import os
from re import match

import pandas as pd
from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.contact_person.contact_person_logic import (
    ContactPersonLogic,
)


class ContactPersonInfoService:
    """
    お客様企業一覧&検索の共通処理
    """

    @service
    def get_corpration_info(
        self, request_dict: dict, user_id, role_id, org_type_code, org_id, logger=None
    ):
        """
        企業情報取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        result = ContactPersonLogic.introduction(
            self, request_dict, user_id, role_id, org_type_code, org_id
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result
