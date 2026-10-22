import os
from urllib.parse import quote

from flask import abort, current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.dto.report.electricity_vis_create_in_dto import (
    ElectricityVisCreateInDto as InDto,
)
from cndx_corp_back.service.report.pdf_create_service import (
    ReportPdfCreateService,
)
from cndx_corp_back.utils.utils import get_message


class ElectricityVisCreateApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 入力チェック
        try:
            dto = InDto.model_validate(dict_request_data, by_name=True, by_alias=False)
        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}：チェックエラー：\n{e}")
            abort(400, description=str(e))

        # サービスを呼び出す
        user_id = user_context.get("user_id")
        login_org_id = user_context.get("org_id")
        ReportPdfCreateService().execute(
            dto, dict_request_data, user_id, login_org_id, logger=logger
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify({"ok": True}), 200


electricty_vis_create_view = ElectricityVisCreateApi.as_view(
    "electricty_vis_create_api"
)
report_bp.add_url_rule(
    "/electric_vis/create", view_func=electricty_vis_create_view, methods=["POST"]
)
