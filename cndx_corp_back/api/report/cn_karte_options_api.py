import os

from flask import current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.report.cn_karte_options_service import CnKarteOptionsService


class CnKarteOptionsApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 処理開始")

        result_data = CnKarteOptionsService().get_options(
            dict_request_data, user_context=user_context
        )

        logger.info(f"{os.path.basename(__file__)} 処理終了")
        return jsonify(result_data), 200


# エンドポイント登録
cn_karte_options_view = CnKarteOptionsApi.as_view("cn_karte_options_api")
report_bp.add_url_rule(
    "/cn-karte/options", view_func=cn_karte_options_view, methods=["GET"]
)
