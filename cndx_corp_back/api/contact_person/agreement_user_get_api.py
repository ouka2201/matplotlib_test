import os

from flask import current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.contact_person import contact_person_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.contact_person.agreement_user_get_service import (
    ContactPersonAgreementUserGetService,
)


class ContactPersonAgreementUserGetApi(MethodView):

    @controller
    def post(self, dict_request_data, logger=None):
        """
        # 拠点マスタから、同意書取得組織として登録されているデータを取得
        """
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # サービスを呼び出す
        res = ContactPersonAgreementUserGetService().get_buiding_info(dict_request_data)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(res), 200


agreement_user_get_view = ContactPersonAgreementUserGetApi.as_view(
    "agreement_user_get_api"
)
contact_person_bp.add_url_rule(
    "/agreementuserget", view_func=agreement_user_get_view, methods=["POST"]
)
