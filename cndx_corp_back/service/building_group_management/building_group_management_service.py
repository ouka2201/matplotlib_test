import os
import traceback

# import math
from flask import abort, current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.building_group_management.building_group_management_logic import (
    BuildingGroupManagementLogic,
)


class BuildingGroupManagementService:
    # =============================
    # 建物グループ情報 単体検索処理
    # =============================
    @service
    def get_building_group(self, request: dict, logger=None):
        logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}：建物グループ検索処理開始。")

        try:
            result = BuildingGroupManagementLogic.getBuildingGroup(
                self, request, logger=None
            )
        except Exception as e:
            logger.error(
                f"{os.path.basename(__file__)}：建物グループ検索処理で例外発生。\n{traceback.format_exc()}"
            )
            abort(500, description=str(e))

        logger.info(f"{os.path.basename(__file__)}：建物グループ検索処理終了。")
        return result

    @service
    def update_building_group(self, dto, logger=None):
        logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}：建物グループ更新処理開始。")

        # 更新処理
        result = BuildingGroupManagementLogic.update_building_group(
            self, dto, logger=None
        )

        logger.info(f"{os.path.basename(__file__)}：建物グループ更新処理終了。")
        return result
