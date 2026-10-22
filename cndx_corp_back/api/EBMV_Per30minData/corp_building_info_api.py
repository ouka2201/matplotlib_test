from flask import jsonify, request
from flask.views import MethodView

from cndx_corp_back.api.EBMV_Per30minData import corp_building_info_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.EBMV_Per30minData.corp_building_info_service import (
    CorpBuildingInfoService,
)


class CorpBuildingInfoApi(MethodView):
    @jwt_user_context_db(refresh=False)
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):
        """
        GET: 絞り込み条件を元に対象建物・事業所一覧を取得
        """
        dict_request_data["corporate_number"] = request.args.get("corporate_number")
        user_id = user_context.get("user_id")
        role_id = user_context.get("role")
        org_id = user_context.get("org_id")
        res = CorpBuildingInfoService().get_corp_building_info_list(
            dict_request_data, user_id, role_id, org_id
        )
        # return res,
        return jsonify(res), 200


# ルート登録
corp_building_info_view = CorpBuildingInfoApi.as_view("corp_building_info_api")
corp_building_info_bp.add_url_rule(
    "/list", view_func=corp_building_info_view, methods=["GET"]
)
