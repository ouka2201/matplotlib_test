import os
from urllib.parse import quote

import redis
from flask import abort, current_app, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db, log_time
from cndx_corp_back.dto.report.cn_karte_create_vis_in_dto import (
    CreateCnKarteVisInDto as InDto,
)
from cndx_corp_back.service.report.pdf_create_service import (
    ReportPdfCreateService,
)
from cndx_corp_back.utils.utils import get_message


class ReportPdfCreateVisApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    # @log_time
    def post(self, dict_request_data, user_context=None, logger=None):

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 入力チェック
        try:
            dto = InDto.model_validate(dict_request_data, by_name=True, by_alias=True)
        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}：チェックエラー：\n{e}")
            abort(400, description=str(e))

        # サービスを呼び出す
        user_id = user_context.get("user_id")
        login_org_id = user_context.get("org_id")
        dto.user_email = user_context.get("email_address")
        # user_id = "test"
        result_dict = ReportPdfCreateService().execute(
            dto, dict_request_data, user_id, login_org_id, logger=logger
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(result_dict), 200


report_pdf_create_view = ReportPdfCreateVisApi.as_view("cn_karte_vis_create_api")
report_bp.add_url_rule(
    "/cn-karte/create/vis", view_func=report_pdf_create_view, methods=["POST"]
)
