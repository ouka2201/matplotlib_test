import os

from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.EBMG_BaseEnergy import base_energy_info_inquiry_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.EBMG_BaseEnergy.base_energy_inquiry_service import (
    BaseEnergyInquiryService,
)


class BaseEnergyInfoApi(MethodView):

    @controller
    def post(self, dict_request_data, logger=None):
        """
        POST: 電気事業者検索処理
        """
        url = request.path
        dict_request_data = dict_request_data or {}
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        if "electricCo" in url:
            # サービスを呼び出す
            res = BaseEnergyInquiryService().search_electric_co(dict_request_data)

            logger.info(f"{os.path.basename(__file__)}処理終了。")
            return jsonify(res), 200
        elif "cityGas" in url:
            # City gas supplier master list
            res = BaseEnergyInquiryService().get_city_gas_list()

            logger.info(f"{os.path.basename(__file__)} city_gas_list end")
            return jsonify(res), 200
        elif "heatSupplier" in url:
            # Heat supplier master list
            res = BaseEnergyInquiryService().get_heat_supplier_list()

            logger.info(f"{os.path.basename(__file__)} heat_supplier_list end")
            return jsonify(res), 200
        elif "heat" in url:
            # サービスを呼び出す
            res = BaseEnergyInquiryService().search_heat_supplier(dict_request_data)

            logger.info(f"{os.path.basename(__file__)}処理終了。")
            return jsonify(res), 200


# ルート登録
base_energy_info_view = BaseEnergyInfoApi.as_view("search_electric_company")
base_energy_info_inquiry_bp.add_url_rule(
    "/search/electricCo", view_func=base_energy_info_view, methods=["POST"]
)
base_energy_info_inquiry_bp.add_url_rule(
    "/search/cityGas", view_func=base_energy_info_view, methods=["POST"]
)
base_energy_info_inquiry_bp.add_url_rule(
    "/search/heatSupplier", view_func=base_energy_info_view, methods=["POST"]
)
base_energy_info_inquiry_bp.add_url_rule(
    "/search/heat", view_func=base_energy_info_view, methods=["POST"]
)
