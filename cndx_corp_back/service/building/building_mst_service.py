import math
import os
import traceback

from flask import abort, current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.building.building_mst_logic import BuildingMstLogic
from cndx_corp_back.utils.utils import get_message


class BuildingMstService:

    # =============================
    # グループ一括更新
    # =============================
    @service
    def get_building_mst_info(self, request_dict, logger=None):
        """
        エネルギー取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        building_mst_info = BuildingMstLogic().get_building_mst_info(request_dict)

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return building_mst_info
