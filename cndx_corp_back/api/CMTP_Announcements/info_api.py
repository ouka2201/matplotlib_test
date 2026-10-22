import os

from flask import current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.CMTP_Announcements import announcements_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.CMTP_Announcements.info_service import (
    AnnouncementsInfoService,
)


class AnnouncementsInfoApi(MethodView):

    # @jwt_required()
    @controller
    def get(self, dict_request_data, logger=None):
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # サービスを呼び出す
        res = AnnouncementsInfoService().get_announcements_info(dict_request_data)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(res), 200


announcements_info_view = AnnouncementsInfoApi.as_view("info_api")
announcements_bp.add_url_rule(
    "/inquiry", view_func=announcements_info_view, methods=["GET"]
)
