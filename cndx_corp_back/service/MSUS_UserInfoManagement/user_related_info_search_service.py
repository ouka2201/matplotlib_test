import os
from re import match

import pandas as pd
from flask import current_app

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSUS_UserInfoManagement.user_related_search_info_logic import (
    UserRelatedSearchInfoLogic,
)


class UserRelatedSearchInfoService:
    @service
    def get_company_name_info(self, request_dict: dict, role_id, user_id, logger=None):
        """
        企業名プルダウン用取得関数
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        logic = UserRelatedSearchInfoLogic()
        with get_scoped_session() as session:
            try:
                result = logic.get_company_name(request_dict, session, role_id, user_id)
            except Exception as e:
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result

    @service
    def get_branch_name_info(self, request_dict: dict, logger=None):
        """
        支店名プルダウン用取得関数
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        logic = UserRelatedSearchInfoLogic()
        with get_scoped_session() as session:
            try:
                result = logic.get_branch_name(request_dict, session)
            except Exception as e:
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result

    @service
    def get_user_role_info(self, request_dict: dict, logger=None):
        """
        ユーザー権限プルダウン用取得関数
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        logic = UserRelatedSearchInfoLogic()
        with get_scoped_session() as session:
            try:
                result = logic.get_user_role(request_dict, session)
            except Exception as e:
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result

    @service
    def get_user_status_info(self, request_dict: dict, logger=None):
        """
        ユーザーステータスプルダウン用取得関数
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        logic = UserRelatedSearchInfoLogic()
        with get_scoped_session() as session:
            try:
                result = logic.get_user_status(request_dict, session)
            except Exception as e:
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result
