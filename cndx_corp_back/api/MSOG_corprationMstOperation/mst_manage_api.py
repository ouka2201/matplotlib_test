from flask import jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.MSOG_corprationMstOperation import mst_manage_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.MSOG_corprationMstOperation.corpration_basic_inquiry_service import (
    CorprationBasicInquiryService,
)
from cndx_corp_back.service.MSOG_corprationMstOperation.corpration_basic_update_service import (
    CorprationBasicUpdateService,
)

# from flask_jwt_extended import jwt_required


class MstDataManageApi(MethodView):

    # @jwt_required()
    @controller
    @jwt_user_context_db(refresh=False)
    def post(self, dict_request_data, user_context=None, logger=None):
        dict_request_data["user_id"] = user_context.get("user_id")
        res = CorprationBasicUpdateService().post_corpration_building_info(
            request_dict=dict_request_data
        )

        return jsonify({"result": res}), 200

    # @jwt_required(locations=["cookies"])
    @controller
    # @jwt_required()
    @jwt_user_context_db(refresh=False)
    def get(self, dict_request_data, user_context=None, logger=None):

        res = CorprationBasicInquiryService().get_corpration_building_info(
            request_dict=dict_request_data,
            user_id=user_context.get("user_id"),
            user_role=user_context.get("role"),
        )

        return jsonify({"result": res}), 200


mst_manage_view = MstDataManageApi.as_view("mst_manage_api")
mst_manage_bp.add_url_rule(
    "/corpration/info", view_func=mst_manage_view, methods=["GET"]
)
mst_manage_bp.add_url_rule(
    "/corpration/info", view_func=mst_manage_view, methods=["POST"]
)
