# cndx_corp_back/service/report/power_report_list_service.py
import os

from flask import abort, current_app

from cndx_corp_back.logic.report.power_report_list_component import (
    PowerReportListComponent,
)


class PowerReportListService:
    """電力見える化レポート一覧取得サービス

    必須: corporate_number, org_id
    Logic 層: PowerReportListComponent に処理を委譲
    """

    def get_power_report_list(self, request_dict: dict, user_context) -> list | None:
        logger = current_app.logger
        logger.debug(f"{os.path.basename(__file__)} get_power_report_list 開始")

        try:
            corporate_number = request_dict.get("corporate_number", "").strip()
            agreement_category = request_dict.get("agreement_category", "").strip()
            org_id = request_dict.get("org_id", "").strip()

            if not corporate_number or not org_id:
                logger.warning(
                    "法人番号または組織IDが未指定です。空リストを返却します。"
                )
                abort(400)

            result_list = PowerReportListComponent().execute(
                corporate_number, org_id, agreement_category, user_context
            )

            logger.debug(f"{os.path.basename(__file__)} get_power_report_list 終了")
            return result_list

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"{os.path.basename(__file__)} 想定外エラー発生: {e}")
            abort(500)
