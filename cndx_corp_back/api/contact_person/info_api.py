import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.contact_person import contact_person_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.contact_person.info_service import (
    ContactPersonInfoService,
)

# 使用していないゴミソース

# class ContactPersonInfoApi(MethodView):

# @jwt_required()
#    @controller
#    def post(self, dict_request_data, logger=None):
#        if logger is None:
#            logger = current_app.logger
#        logger.info(f"{os.path.basename(__file__)}処理開始。")
#        # サービスを呼び出す
#        res = ContactPersonInfoService().get_corpration_info(dict_request_data)

#        logger.info(f"{os.path.basename(__file__)}処理終了。")
#        return jsonify(res), 200


# contact_person_info_view = ContactPersonInfoApi.as_view("info_api")
# contact_person_bp.add_url_rule(
#    "/info/inquiry", view_func=contact_person_info_view, methods=["POST"]
# )
