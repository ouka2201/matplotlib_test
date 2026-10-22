import os
import traceback
from typing import Any, Dict

from flask import current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.kesson_report_create_service import (
    KessonReportCreateService,
)


class KessonReportCreateApi(MethodView):
    """
    欠損レポート（欠損一覧＋エネルギーデータ欠損）を生成し、
    ローカルにExcelファイルを保存してパスを返却する。
    """

    @controller
    def post(self, dict_request_data: Dict[str, Any], logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 欠損レポート作成処理開始")

        message_list: list[str] = []

        try:
            # サービス呼び出し（複数レポート対応に変更）
            result_dict = KessonReportCreateService().execute(
                request_dict=dict_request_data,
                message_list=message_list,
                logger=logger,
            )

            if message_list:
                logger.warning(f"入力エラー: {message_list}")
                return jsonify({"message": message_list}), 400

            logger.info(f"{os.path.basename(__file__)} 欠損レポート作成処理終了")
            return jsonify(result_dict), 200  # ← 2つのpathを含むdictを返す

        except Exception as exc:
            logger.error(f"欠損レポート作成失敗: {exc}")
            logger.debug(traceback.format_exc())
            return jsonify({"error": "サーバーエラーが発生しました"}), 500


# ルーティング登録
kesson_report_create_view = KessonReportCreateApi.as_view("kesson_report_create_api")
# -> /api/report/kesson-report/create
report_bp.add_url_rule(
    "/kesson-report/create", view_func=kesson_report_create_view, methods=["POST"]
)
