import os

from flask import abort, current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.building import building_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.dto.building.energy_info_list_in_dto import (
    BuildingEnergyInfoListIn,
)
from cndx_corp_back.service.building.energy_info_list_service import (
    BuildingEnergyInfoListService,
)


class BuildingEnergyInfoListApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            indto = BuildingEnergyInfoListIn.model_validate(dict_request_data)
        except Exception as e:
            logger.error(e)
            abort(400)

        # サービスを呼び出す
        res = BuildingEnergyInfoListService().get_energy_list(
            dto=indto, user_context=user_context
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"ok": True, "result_list": res}), 200


building_energy_info_view = BuildingEnergyInfoListApi.as_view("energy_info_list_api")
building_bp.add_url_rule(
    "/energy-info-list", view_func=building_energy_info_view, methods=["GET"]
)
