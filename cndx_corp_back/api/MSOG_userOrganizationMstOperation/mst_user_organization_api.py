from flask import jsonify, request
from flask.views import MethodView

from cndx_corp_back.api.MSOG_userOrganizationMstOperation import mst_organization_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.MSOG_userOrganizationMstOperation.user_org_corp_auth_inquiry_service import (
    UserOrgCorpAuthInquiryService,
)
from cndx_corp_back.service.MSOG_userOrganizationMstOperation.user_org_corp_auth_register_serivce import (
    UserOrgCorpAuthRegisterSerivce,
)
from cndx_corp_back.service.MSOG_userOrganizationMstOperation.user_org_corp_auth_update_serivce import (
    UserOrgCorpAuthUpdateSerivce,
)
from cndx_corp_back.service.MSOG_userOrganizationMstOperation.user_org_corps_inquiry_serivce import (
    UserOrgCorpsInquirySerivce,
)


class MstDataManageApi(MethodView):

    # @jwt_required()
    # @controller
    # def post(self, dict_request_data, logger=None):

    #     url = request.path

    #     #企業組織情報新規登録
    #     if 'auth_register' in url:
    #         res = UserOrgCorpAuthRegisterSerivce().user_org_corp_auth_register(
    #             request_dict=dict_request_data)
    #     #企業組織情報更新
    #     if 'auth_update' in url:
    #         res = UserOrgCorpAuthUpdateSerivce().user_org_corp_auth_update(
    #             request_dict=dict_request_data)

    #     return jsonify({"result": "ok"}), 200
    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data=None, user_context=None, logger=None):
        url = request.path

        if dict_request_data is None:
            return jsonify({"error": "リクエストボディが存在しません"}), 400

        if "auth_register" in url:
            UserOrgCorpAuthRegisterSerivce().user_org_corp_auth_register(
                request_dict=dict_request_data, user_context=user_context
            )
        elif "auth_update" in url:
            UserOrgCorpAuthUpdateSerivce().user_org_corp_auth_update(
                request_dict=dict_request_data, user_context=user_context
            )
        else:
            return jsonify({"error": "未知のエンドポイント"}), 404

        return jsonify({"result": "ok"}), 200

    # @jwt_required()
    @controller
    def get(self, dict_request_data, logger=None):

        url = request.path

        # 企業組織詳細情報取得
        if "corpration/detail/auth" in url:
            res = UserOrgCorpAuthInquiryService().get_user_org_corps_info(
                request_dict=dict_request_data
            )

            return jsonify({"detail_auth_list": res}), 200

        # 企業組織情報取得
        if "corprations/auth" in url:
            res = UserOrgCorpsInquirySerivce().get_user_org_corps_info(
                request_dict=dict_request_data
            )

            return jsonify({"auth_list": res}), 200


mst_organization_view = MstDataManageApi.as_view("mst_user_organization_api")

mst_organization_bp.add_url_rule(
    "/corpration/detail/auth", view_func=mst_organization_view, methods=["GET"]
)
mst_organization_bp.add_url_rule(
    "/corprations/auth", view_func=mst_organization_view, methods=["GET"]
)
mst_organization_bp.add_url_rule(
    "/corpration/auth_register", view_func=mst_organization_view, methods=["POST"]
)
mst_organization_bp.add_url_rule(
    "/corpration/auth_update", view_func=mst_organization_view, methods=["POST"]
)
