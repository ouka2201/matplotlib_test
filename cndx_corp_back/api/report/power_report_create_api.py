import io
import os
import subprocess
import traceback
from typing import Any, Dict
from urllib.parse import quote

from flask import Response, current_app, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.power_report_create_service import (
    PowerReportCreateService,
)
from cndx_corp_back.utils.utils import get_message


class PowerReportCreateApi(MethodView):
    """
    POST /api/report/power-report/create
    フロントから受け取った条件で「電力見える化レポート」を生成し、
    保存先（report_save_path など）を DB 更新した上で
    生成ファイルの HDFS／ローカルパスを返却する。
    """

    # 認証が必要ならデコレータを外す
    # @jwt_required()
    @controller
    def post(self, dict_request_data: Dict[str, Any], logger=None):  # noqa: D401
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 電力レポート作成処理開始")

        # ---------- 入力チェック ----------
        message_list: list[str] = []

        try:
            # ---------- サービス呼び出し ----------
            report_location = PowerReportCreateService().execute(
                request_dict=dict_request_data,
                message_list=message_list,
                logger=logger,
            )

            if message_list:
                logger.warning(f"入力エラー: {message_list}")
                return jsonify({"message": message_list}), 400

            logger.info(f"{os.path.basename(__file__)} 電力レポート作成処理終了")
            return jsonify({"report_location": report_location}), 200

        except Exception as exc:  # pylint: disable=broad-except
            # 予期せぬエラーはここで握りつぶして 500 返却
            logger.error(f"電力レポート作成失敗: {exc}")
            logger.debug(traceback.format_exc())
            return jsonify({"error": get_message("SERVER_ERROR")}), 500


# ルーティング登録
power_report_create_view = PowerReportCreateApi.as_view("power_report_create_api")
# -> /api/report/power-report/create
report_bp.add_url_rule(
    "/power-report/create", view_func=power_report_create_view, methods=["POST"]
)
