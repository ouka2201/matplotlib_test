from flask import jsonify
from flask.views import MethodView

from cndx_corp_back.api.EBMV_Per30minData import per_30min_data_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.EBMV_Per30minData.per_30min_data_service import (
    Per30minDataService,
)
from cndx_corp_back.utils.utils import get_message


class Per30minDataApi(MethodView):

    @controller
    @jwt_user_context_db(refresh=False)
    def get(self, dict_request_data, user_context=None, logger=None):
        """
        GET: 建物IDを元に30分値登録状況を取得
        """
        try:
            org_type_code = user_context.get("org_type_code")
            login_org_id = user_context.get("org_id")
            user_id = user_context.get("user_id")
            role_id = user_context.get("role")
            res = Per30minDataService().get_per_30min_data_list(
                dict_request_data, org_type_code, login_org_id, user_id, role_id
            )
            return jsonify({"result": res}), 200
        except Exception as e:
            logger.error(f"30分値データ取得エラー: {str(e)}")
            return (
                jsonify({"message": get_message("NOT_EXIST", field="30分値データ")}),
                500,
            )


# ルート登録
per_30min_data_view = Per30minDataApi.as_view("per_30min_data_api")
per_30min_data_bp.add_url_rule(
    "/per_30min_data", view_func=per_30min_data_view, methods=["GET"]
)
