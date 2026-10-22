import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.building import building_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.building.info_service import BuildingInfoService


class BuildingInfoApi(MethodView):

    # TODO テストで一時コメントアウト
    # @jwt_required()
    @controller
    def get(self, dict_request_data, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # サービスを呼び出す
        res = BuildingInfoService().get_building_info(dict_request_data)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(res), 200


building_info_view = BuildingInfoApi.as_view("info_api")
building_bp.add_url_rule("/info", view_func=building_info_view, methods=["GET"])
