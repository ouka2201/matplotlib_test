# cndx_corp_back/logic/report/power_report_options_component.py

import calendar
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List

from flask import abort, current_app
from sqlalchemy import and_, func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.t_electricity_data_30min_entity import (
    TElectricityData30min,
)
from cndx_corp_back.utils.utils import get_message


class PowerReportOptionsComponent:
    """拠点一覧 + 対象月候補をまとめて返す"""

    @component
    def execute(self, request_dict: Dict[str, Any], logger=None) -> Dict[str, Any]:
        if logger is None:
            logger = current_app.logger

        corp = request_dict.get("corporate_number", "").strip()
        org_id = request_dict.get("org_id", "").strip()
        building_id = request_dict.get("building_id", "").strip()
        agreement_category = request_dict.get("agreement_category", "").strip()

        # 期間（任意） 例: 2024, 12, 2025, 11
        s_year = request_dict.get("start_year")
        s_month = request_dict.get("start_month")
        e_year = request_dict.get("end_year")
        e_month = request_dict.get("end_month")

        if not corp or not org_id:
            logger.warning("corporate_number と org_id は必須です")
            abort(
                400,
                description=get_message(
                    "REQUIRED", item_name="corporate_number, org_id"
                ),
            )

        logger.info(
            f"{os.path.basename(__file__)} execute 開始 corp={corp}, org_id={org_id}"
        )

        try:
            with get_scoped_session() as session:
                # -----------------------------------------------------------------
                # 1) 建物／契約電力リスト
                # -----------------------------------------------------------------
                building_query = session.query(
                    MBuilding.building_id,
                    MBuilding.location_identifier_name.label("building_name"),
                    MBuilding.contracted_power,
                ).filter(
                    MBuilding.corporate_number == corp,
                    MBuilding.agreement_category == agreement_category,
                    MBuilding.delete_flg.is_not(True),
                )

                # org_id が dummy でない場合のみ追加
                if org_id != "dummy":
                    building_query = building_query.filter(
                        MBuilding.agreement_org == org_id
                    )

                building_rows = building_query.order_by(
                    MBuilding.location_identifier_name
                ).all()

                building_list: List[Dict[str, Any]] = [
                    {
                        "building_id": row.building_id,
                        "building_name": row.building_name,
                        "contracted_power": row.contracted_power,
                    }
                    for row in building_rows
                ]

                # -----------------------------------------------------------------
                # 2) 対象月候補（任意：building_id & 期間が渡ってきた場合のみ計算）
                # -----------------------------------------------------------------
                target_months: List[Dict[str, str]] = []

                if building_id and all(
                    v is not None and v != ""
                    for v in (s_year, s_month, e_year, e_month)
                ):
                    # 期間 YYYYMM を文字列で生成
                    start_yyyymm = f"{int(s_year):04d}{int(s_month):02d}"
                    end_yyyymm = f"{int(e_year):04d}{int(e_month):02d}"

                    subq = (
                        session.query(
                            func.substr(
                                TElectricityData30min.acquisition_date, 1, 6
                            ).label("yyyymm")
                        )
                        .filter(
                            TElectricityData30min.corp_number == corp,
                            TElectricityData30min.building_id == building_id,
                            func.substr(
                                TElectricityData30min.acquisition_date, 1, 6
                            ).between(start_yyyymm, end_yyyymm),
                        )
                        .distinct()
                        .subquery()
                    )

                    month_rows = (
                        session.query(subq.c.yyyymm).order_by(subq.c.yyyymm).all()
                    )

                    for (yyyymm,) in month_rows:
                        y = int(yyyymm[:4])
                        m = int(yyyymm[4:6])
                        label = f"{y}年{m}月"
                        target_months.append({"value": yyyymm, "label": label})

                logger.info(f"{os.path.basename(__file__)} execute 正常終了")

                return {
                    "building_list": building_list,
                    "target_months": target_months,
                }

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("PowerReportOptionsComponent 失敗\n" + traceback.format_exc())
            abort(500, description=get_message("SERVER_ERROR"))
