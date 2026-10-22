import os

from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.EBMV_Per30minData.corp_building_info_component import (
    CorpBuildingInfoComponent,
)


class CorpBuildingInfoService:
    @service
    def get_corp_building_info_list(
        self, request_dict: dict, user_id, role_id, org_id, logger=None
    ):
        """
        企業基本情報 + 建物情報を取得
        同意取得情報の結果をリスト形式で返す
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 処理開始")

        return CorpBuildingInfoComponent().execute(
            request_dict, user_id, role_id, org_id
        )
