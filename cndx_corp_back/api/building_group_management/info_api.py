import os

# import traceback
from flask import abort, current_app, jsonify, request
from flask.views import MethodView
from pydantic import ValidationError

from cndx_corp_back.api.building_group_management import building_group_management_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.building_group_management.building_group_management_service import (
    BuildingGroupManagementService,
)

# from flask_jwt_extended import jwt_required


class BuildingGroupManagementInfoApi(MethodView):

    # @jwt_required()
    @controller
    def get(self, dict_request_data, logger=None):
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 建物グループマスタを検索
        res = BuildingGroupManagementService().get_building_group(dict_request_data)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(res), 200

    # @jwt_required()
    @controller
    def post(self, dict_request_data, logger=None):

        from cndx_corp_back.dto.building_group.building_group_update_in_dto import (
            BuildingGroupUpdateInDto as InDto,
        )

        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        try:
            dto = InDto.model_validate(dict_request_data)
        except ValidationError as e:
            logger.error(f"{os.path.basename(__file__)}：チェックエラー：\n{e}")
            abort(400, description=str(e.errors()))

        # 建物グループマスタを検索
        BuildingGroupManagementService().update_building_group(dto)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"ok": True}), 200


building_group_management_view = BuildingGroupManagementInfoApi.as_view(
    "building_group_management_api"
)
building_group_management_bp.add_url_rule(
    "/master/detail", view_func=building_group_management_view, methods=["GET"]
)
building_group_management_bp.add_url_rule(
    "/master/detail", view_func=building_group_management_view, methods=["POST"]
)
