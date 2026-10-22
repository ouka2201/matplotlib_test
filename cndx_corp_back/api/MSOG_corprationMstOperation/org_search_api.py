import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.MSOG_corprationMstOperation import mst_manage_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.MSOG_corprationMstOperation.corpration_basic_inquiry_service import (
    CorprationBasicInquiryService,
)


class OrgSearchApi(MethodView):

    @controller
    def post(self, dict_request_data, logger=None):
        """
        POST: 利用者組織情報から、組織に関する情報取得処理
        """

        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # サービスを呼び出す
        res = CorprationBasicInquiryService().search_agreement_org(dict_request_data)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(res), 200


# ルート登録
mst_manage_view = OrgSearchApi.as_view("org_search_api")
mst_manage_bp.add_url_rule("/org/info", view_func=mst_manage_view, methods=["POST"])
