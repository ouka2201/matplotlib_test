import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.report.cn_karte_list_service import CnKarteListService


class CnKarteListApi(MethodView):

    @controller
    @jwt_user_context_db(refresh=False)
    def get(self, dict_request_data, user_context=None, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 処理開始")

        result_list = CnKarteListService().get_cn_karte_list(
            dict_request_data, user_context
        )

        if not result_list:
            logger.info("結果が空です。")
            return jsonify({"cn_karte_list": []}), 200

        logger.info(f"{os.path.basename(__file__)} 処理終了")
        return jsonify({"cn_karte_list": result_list}), 200


# エンドポイント登録
cn_karte_list_view = CnKarteListApi.as_view("cn_karte_list_api")
report_bp.add_url_rule("/cn-karte/list", view_func=cn_karte_list_view, methods=["GET"])
