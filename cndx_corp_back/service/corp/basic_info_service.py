import os

import pandas as pd
from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.corp.basic_info_component import (
    CorpBuildingInfoComponent,
)
from cndx_corp_back.utils.dto_utils import include


class CorpBasicInfoService:

    allowed_key_get = {
        "bank_code",
        "branch_code",
        "corporate_number",
        "fiscal_year",
        "registration_seq",
    }

    @service
    def get_corp_basic_info(
        self,
        request_dict: dict,
        login_org_id,
        org_type_code,
        role_id,
        user_id,
        logger=None,
    ):
        """
        企業情報取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # TODO サニタイジング

        branches_energy_info = CorpBuildingInfoComponent().get(
            request_dict, login_org_id, org_type_code, role_id, user_id
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return branches_energy_info

    @service
    def post_corp_basic_info(self, request_dict: dict, user_id, org_id, logger=None):
        """
        企業情報更新
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # TODO サニタイジング

        # jwt_user_context_db デコレーターが user_context を注入するため、第2引数は不要
        CorpBuildingInfoComponent().post(request_dict, user_id, org_id)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
