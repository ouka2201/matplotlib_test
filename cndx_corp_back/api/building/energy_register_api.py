import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.building import building_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.building_energy.building_energy_register_service import (
    BuildingEnergyRegisterService,
)


class BuildingEnergyRegisterApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # サービスを呼び出す
        res = BuildingEnergyRegisterService().save_from_page(
            dict_request_data, user_context
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"ok": True, "registration_seq": int(res)}), 200


building_energy_reg_view = BuildingEnergyRegisterApi.as_view("energy_register_api")
building_bp.add_url_rule(
    "/energy-register", view_func=building_energy_reg_view, methods=["POST"]
)
