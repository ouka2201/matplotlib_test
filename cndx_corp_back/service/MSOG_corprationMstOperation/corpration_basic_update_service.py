import os

from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSOG_corprationMstOperation.corpration_basic_update_component import (
    CorprationBasicUpdateComponent,
)


class CorprationBasicUpdateService:

    @service
    def post_corpration_building_info(self, request_dict: dict, logger=None):
        """
        企業建物情報取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 不要なパラメータを除外
        # ファイル転送 comp を呼出
        return CorprationBasicUpdateComponent().execute(request_dict)
