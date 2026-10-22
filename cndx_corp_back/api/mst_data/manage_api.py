from flask import jsonify
from flask.views import MethodView

from cndx_corp_back.api.mst_data import mst_data_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.mst_data.manage_service import MstDataManageService


class MstDataManageApi(MethodView):

    @controller
    def get(self, dict_request_data, logger=None):

        MstDataManageService().refresh()

        return jsonify({"success": True}), 200

    @controller
    def post(self, dict_request_data, logger=None):

        res = MstDataManageService().inquiry(request_dict=dict_request_data)

        return jsonify({"result": res}), 200


mst_data_manage_view = MstDataManageApi.as_view("mst_data_manage_api")
mst_data_bp.add_url_rule("/refresh", view_func=mst_data_manage_view, methods=["GET"])
mst_data_bp.add_url_rule("/inquiry", view_func=mst_data_manage_view, methods=["POST"])
