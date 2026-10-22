import os
import traceback
from typing import Any, Dict

from flask import current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.cn_report_backdata_create_service import (
    CnReportBackdataCreateService,
)


class CnReportBackdataCreateApi(MethodView):
    """
    CNレポートバックデータを生成し、ローカルにCSVファイルを保存してパスを返却する。
    """

    @controller
    def post(self, dict_request_data: Dict[str, Any], logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} CNレポートバックデータ作成処理開始")

        message_list: list[str] = []

        try:
            # サービス呼び出し
            report_paths = CnReportBackdataCreateService().execute(
                request_dict=dict_request_data,
                message_list=message_list,
                logger=logger,
            )

            if message_list:
                logger.warning(f"入力エラー: {message_list}")
                return jsonify({"message": message_list}), 400

            logger.info(
                f"{os.path.basename(__file__)} CNレポートバックデータ作成処理終了"
            )
            return jsonify({"report_locations": report_paths}), 200

        except Exception as exc:
            logger.error(f"CNレポートバックデータ作成失敗: {exc}")
            logger.debug(traceback.format_exc())
            return jsonify({"error": "サーバーエラーが発生しました"}), 500


# ルーティング登録
cn_report_backdata_create_view = CnReportBackdataCreateApi.as_view(
    "cn_report_backdata_create_api"
)
report_bp.add_url_rule(
    "/cn-report-backdata/create",
    view_func=cn_report_backdata_create_view,
    methods=["POST"],
)
