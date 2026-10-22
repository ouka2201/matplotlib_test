# cndx_corp_back/logic/report/power_report_target_months_component.py

import os
import traceback
from typing import Any, Dict, List

from flask import abort, current_app
from sqlalchemy import func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.t_electricity_data_30min_entity import (
    TElectricityData30min,
)
from cndx_corp_back.utils.utils import get_message


class PowerReportTargetMonthsComponent:
    """指定された条件に基づいて対象月リストを返す"""

    @component
    def execute(self, request_dict: Dict[str, Any], logger=None) -> Dict[str, Any]:
        if logger is None:
            logger = current_app.logger

        corp = request_dict.get("corporate_number", "").strip()
        building_id = request_dict.get("building_id", "").strip()
        s_year = request_dict.get("start_year")
        s_month = request_dict.get("start_month")
        e_year = request_dict.get("end_year")
        e_month = request_dict.get("end_month")

        logger.info(
            f"{os.path.basename(__file__)} execute 開始 corp={corp}, building_id={building_id}"
        )

        try:
            if (
                not corp
                or not building_id
                or not all([s_year, s_month, e_year, e_month])
            ):
                logger.warning("パラメータが不足しています")
                abort(
                    400,
                    description=get_message(
                        "REQUIRED", item_name="corporate_number, building_id, 対象年月"
                    ),
                )

            start_yyyymm = f"{int(s_year):04d}{int(s_month):02d}"
            end_yyyymm = f"{int(e_year):04d}{int(e_month):02d}"

            target_months: List[Dict[str, str]] = []

            # 期間内の月数を計算
            s_year = int(s_year)
            s_month = int(s_month)
            e_year = int(e_year)
            e_month = int(e_month)
            total_months = (e_year - s_year) * 12 + (e_month - s_month + 1)

            with get_scoped_session() as session:
                subq = (
                    session.query(
                        func.substr(TElectricityData30min.acquisition_date, 1, 6).label(
                            "yyyymm"
                        )
                    )
                    .filter(
                        TElectricityData30min.corp_number == corp,
                        TElectricityData30min.building_id == building_id,
                        func.substr(
                            TElectricityData30min.acquisition_date, 1, 6
                        ).between(start_yyyymm, end_yyyymm),
                        TElectricityData30min.delete_flg.is_(False),
                    )
                    .distinct()
                    .subquery()
                )

                month_rows = session.query(subq.c.yyyymm).order_by(subq.c.yyyymm).all()

                for (yyyymm,) in month_rows:
                    y = int(yyyymm[:4])
                    m = int(yyyymm[4:6])
                    label = f"{y}年{m}月"
                    target_months.append({"value": yyyymm, "label": label})

            # --- メッセージ判定 ---
            found_months = len(target_months)
            if found_months == 0:
                message = "この期間の電力情報は未登録です。"
            elif found_months < total_months:
                message = "この期間の電力情報は一部未登録です。"
            else:
                message = ""

            logger.info(f"{os.path.basename(__file__)} execute 正常終了")
            return {"target_months": target_months, "message": message}

        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "PowerReportTargetMonthsComponent 失敗\n" + traceback.format_exc()
            )
            abort(500, description=get_message("SERVER_ERROR"))
