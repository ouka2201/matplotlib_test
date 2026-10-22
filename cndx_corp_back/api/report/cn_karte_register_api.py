import os
import traceback
from typing import Any, Dict

from flask import current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.dto.report.cn_karte_create_vis_in_dto import CreateCnKarteVisInDto
from cndx_corp_back.service.report.cn_karte_register_service import (
    CnKarteRegisterService,
)
from cndx_corp_back.utils.utils import get_message


class CnKarteRegisterApi(MethodView):
    """
    POST /api/report/cn-karte/register
    CNカルテの作成条件をDBに登録する。
    """

    @controller
    def post(self, dict_request_data: Dict[str, Any], logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} – CNカルテ条件登録開始")
        message_list: list[str] = []

        try:
            # --- Pydantic DTO validation ---
            try:
                dto = CreateCnKarteVisInDto.model_validate(
                    dict_request_data, by_name=True, by_alias=False
                )
            except Exception as e:
                logger.error(f"入力チェックエラー: {e}")
                return jsonify({"message": str(e)}), 400

            # --- サービス呼び出し ---
            result = CnKarteRegisterService().execute(
                request_dict=dto.model_dump(),
                message_list=message_list,
                logger=logger,
            )

            if message_list:
                logger.warning(f"入力エラー: {message_list}")
                return jsonify({"message": message_list}), 400

            logger.info(f"{os.path.basename(__file__)} – CNカルテ条件登録終了")
            return jsonify({"result": result}), 200

        except Exception as exc:
            logger.error(f"CNカルテ条件登録失敗: {exc}")
            logger.debug(traceback.format_exc())
            return jsonify({"error": get_message("SERVER_ERROR")}), 500


# ルーティング登録
cn_karte_register_view = CnKarteRegisterApi.as_view("cn_karte_register_api")
report_bp.add_url_rule(
    "/cn-karte/register", view_func=cn_karte_register_view, methods=["POST"]
)
