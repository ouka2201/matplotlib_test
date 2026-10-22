import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.contact_person import contact_person_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.contact_person.detail_service import (
    ContactPersonDetailService,
)


class ContactPersonDetailApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):
        """
        担当者編集画面_初期表示
        """
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")

        role_id = user_context.get("role_id")
        org_type_code = user_context.get("org_type_code")
        org_id = user_context.get("org_id")

        # サービスを呼び出す
        res = ContactPersonDetailService().get_contact_pserson_info(
            dict_request_data,
            login_user_id=user_context.get("user_id"),
            role_id=role_id,
            org_type_code=org_type_code,
            org_id=org_id,
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(res), 200


contact_person_info_view = ContactPersonDetailApi.as_view("detail_api")
contact_person_bp.add_url_rule(
    "/detail", view_func=contact_person_info_view, methods=["GET"]
)
