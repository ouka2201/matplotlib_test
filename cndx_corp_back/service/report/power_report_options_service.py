# cndx_corp_back/service/report/power_report_options_service.py

import os
from typing import Any, Dict

from flask import abort, current_app

from cndx_corp_back.logic.report.power_report_options_component import (
    PowerReportOptionsComponent,
)
from cndx_corp_back.utils.utils import get_message


class PowerReportOptionsService:
    def get_options(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        logger = current_app.logger
        logger.debug(f"{os.path.basename(__file__)} get_options 開始")

        try:
            # ---- 必須パラメータ ----------------------------------------- #
            corporate_number = request_dict.get("corporate_number", "").strip()
            org_id = request_dict.get("org_id", "").strip()

            if not corporate_number or not org_id:
                logger.warning("法人番号または組織IDが未指定です。")
                abort(
                    400,
                    description=get_message("REQUIRED", "corporate_number と org_id "),
                )

            # ------------------------------------------------------------ #
            result_dict = PowerReportOptionsComponent().execute(
                request_dict=request_dict, logger=logger
            )

            logger.debug(f"{os.path.basename(__file__)} get_options 終了")
            return result_dict

        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"{os.path.basename(__file__)} 想定外エラー発生: {exc}")
            abort(500, description=get_message("SERVER_ERROR"))
