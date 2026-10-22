# cndx_corp_back/service/report/power_report_target_months_service.py

import os
from typing import Any, Dict

from flask import abort, current_app

from cndx_corp_back.logic.report.power_report_target_months_component import (
    PowerReportTargetMonthsComponent,
)
from cndx_corp_back.utils.utils import get_message


class PowerReportTargetMonthsService:
    def get_target_months(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        logger = current_app.logger
        logger.debug(f"{os.path.basename(__file__)} get_target_months 開始")

        try:
            # ---- 必須パラメータ ----------------------------------------- #
            corporate_number = request_dict.get("corporate_number", "").strip()
            building_id = request_dict.get("building_id", "").strip()
            start_year = request_dict.get("start_year")
            start_month = request_dict.get("start_month")
            end_year = request_dict.get("end_year")
            end_month = request_dict.get("end_month")

            if not (
                corporate_number
                and building_id
                and start_year
                and start_month
                and end_year
                and end_month
            ):
                logger.warning("必要なパラメータが不足しています。")
                abort(
                    400,
                    description=get_message(
                        "REQUIRED",
                        "corporate_number, building_id, start_year, start_month, end_year, end_month",
                    ),
                )

            # ------------------------------------------------------------ #
            result_dict = PowerReportTargetMonthsComponent().execute(
                request_dict=request_dict, logger=logger
            )

            logger.debug(f"{os.path.basename(__file__)} get_target_months 終了")
            return result_dict

        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"{os.path.basename(__file__)} 想定外エラー発生: {exc}")
            abort(500, description=get_message("SERVER_ERROR"))
