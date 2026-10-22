import os
import traceback
from typing import Any, Dict

from flask import current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.kpi_report_create_service import (
    KpiReportCreateService,
)


class KpiReportCreateApi(MethodView):
    """
    KPI一覧レポートを生成し、ローカルにCSVファイルを保存してパスを返却する。
    """

    @controller
    def post(self, dict_request_data: Dict[str, Any], logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} KPIレポート作成処理開始")

        message_list: list[str] = []

        try:
            # ======= ここは元のコードと同じ =======
            report_path = KpiReportCreateService().execute(
                request_dict=dict_request_data,
                message_list=message_list,
                logger=logger,
            )

            # ======= 【修改 1】入力エラー処理保持 =======
            if message_list:
                logger.warning(f"入力エラー: {message_list}")
                return jsonify({"message": message_list}), 400

            # ======= 【修改 2】KPIデータが存在しない場合の判定追加 =======
            if not report_path:  # 生成結果が空
                msg = "KPI一覧情報が存在しません。"
                logger.warning(msg)
                return jsonify({"message": msg}), 404

            # ======= ここは元のコードと同じ =======
            logger.info(f"{os.path.basename(__file__)} KPIレポート作成処理終了")
            return jsonify({"report_location": report_path}), 200

        except Exception as exc:
            logger.error(f"KPIレポート作成失敗: {exc}")
            logger.debug(traceback.format_exc())
            return jsonify({"error": "サーバーエラーが発生しました"}), 500


# ルーティング登録（この部分は変更なし）
kpi_report_create_view = KpiReportCreateApi.as_view("kpi_report_create_api")
report_bp.add_url_rule(
    "/kpi-report/create", view_func=kpi_report_create_view, methods=["POST"]
)
