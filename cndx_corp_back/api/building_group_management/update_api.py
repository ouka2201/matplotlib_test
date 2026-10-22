import os

from common.decorators import jwt_user_context_db
from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.building_group_management import building_group_management_bp
from cndx_corp_back.api.building_group_management.info_api import (
    BuildingGroupManagementInfoApi,
)
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.building_group_management.update_service import (
    BuildingGroupUpdateService,
)


class BuildingGroupApi(MethodView):

    # @jwt_required()
    @controller
    @jwt_user_context_db(refresh=False)
    def post(self, dict_request_data, user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # サービスを呼び出す
        dict_request_data["userId"] = user_context.get("user_id")
        res = BuildingGroupUpdateService().upsert(dict_request_data)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(res), 200


building_group_management_view = BuildingGroupApi.as_view("update_api")
building_group_management_bp.add_url_rule(
    "/master/update", view_func=building_group_management_view, methods=["POST"]
)
