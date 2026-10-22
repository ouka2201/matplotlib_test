import math
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pandas as pd
from flask import current_app
from sqlalchemy import case, func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.logic.report.certificate_utils import apply_certificate_adjustments

CO2_COLUMN = "CO2排出量(t-CO2)"
HEAT_COLUMN = "熱量換算量(GJ)"
UNIT_COLUMN = "CO2排出量原単位(t-CO2/㎡)"
SITE_NAME_COLUMN = "拠点名"
RANK_COLUMN = "順位"
AREA_COLUMN = "平均延床面積"
CO2_SHARE_COLUMN = "CO2排出量占有率"


class CnSiteRankingReportLogic:
    """拠点ランキングレポートCSV生成ロジック"""

    OUTPUT_DIR = r"C:\HZY\FILE DOWNLOAD\TEST"

    # @log_time
    def generate_site_ranking_csv(
        self,
        df_building,
        request_dict: Dict[str, Any],
        logger=None,
    ) -> str:
        if logger is None:
            logger = current_app.logger

        logger.info("拠点ランキングレポート生成処理開始")

        corporate_number = request_dict["corporate_number"]
        agreement_category = request_dict["agreement_category"]
        org_id = request_dict["org_id"]
        start_ym = request_dict["start_year"] + request_dict["start_month"]
        end_ym = request_dict["end_year"] + request_dict["end_month"]

        output_columns = [
            RANK_COLUMN,
            SITE_NAME_COLUMN,
            CO2_COLUMN,
            CO2_SHARE_COLUMN,
            HEAT_COLUMN,
            AREA_COLUMN,
            UNIT_COLUMN,
        ]

        with get_scoped_session() as session:
            energy_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.building_name.label(
                        SITE_NAME_COLUMN
                    ),
                    TMonthlyBuildingEnergyAggregation.energy_code.label("energy_code"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                    ).label(CO2_COLUMN),
                    func.sum(
                        # TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage
                        case(
                            (
                                TMonthlyBuildingEnergyAggregation.heat_converted_energy_unit
                                == "MJ",
                                TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage
                                / 1000,
                            ),
                            else_=TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage,
                        )
                    ).label(HEAT_COLUMN),
                    func.round(
                        func.avg(TMonthlyBuildingEnergyAggregation.gross_floor_area), 3
                    ).label("area_avg"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_area_unit
                    ).label(UNIT_COLUMN),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        str(start_ym), str(end_ym)
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.building_name,
                    TMonthlyBuildingEnergyAggregation.energy_code,
                )
                .all()
            )

            df_energy = pd.DataFrame(
                [
                    {field: getattr(row, field) for field in row._fields}
                    for row in energy_stmt
                ]
            )

        if df_energy.empty:
            logger.warning(
                "拠点ランキングレポートデータが存在しません、CSV出力をスキップします。"
            )
            merged_df = pd.DataFrame(columns=output_columns)
        else:
            for column_name in (CO2_COLUMN, HEAT_COLUMN, UNIT_COLUMN):
                df_energy[column_name] = pd.to_numeric(
                    df_energy[column_name], errors="coerce"
                ).fillna(0)

            df_energy, heat_certificate_series = apply_certificate_adjustments(
                df_energy, CO2_COLUMN
            )
            if df_energy.empty:
                logger.warning(
                    "証書調整後の拠点データが存在しません、CSV出力をスキップします。"
                )
                merged_df = pd.DataFrame(columns=output_columns)
            else:
                grouped_df = df_energy.groupby(
                    ["building_id", SITE_NAME_COLUMN], as_index=False
                ).agg(
                    {
                        CO2_COLUMN: "sum",
                        HEAT_COLUMN: "sum",
                        "area_avg": "mean",
                        UNIT_COLUMN: "sum",
                    }
                )

                if (
                    heat_certificate_series is not None
                    and not heat_certificate_series.empty
                ):
                    heat_certificate_series = heat_certificate_series.rename(
                        "heat_certificate_total"
                    )
                    grouped_df = grouped_df.merge(
                        heat_certificate_series.reset_index(),
                        on="building_id",
                        how="left",
                    )
                else:
                    grouped_df["heat_certificate_total"] = 0.0

                grouped_df["heat_certificate_total"] = pd.to_numeric(
                    grouped_df["heat_certificate_total"], errors="coerce"
                ).fillna(0.0)
                grouped_df[CO2_COLUMN] = (
                    grouped_df[CO2_COLUMN] - grouped_df["heat_certificate_total"]
                )
                grouped_df.loc[grouped_df[CO2_COLUMN] < 0, CO2_COLUMN] = 0
                grouped_df = grouped_df.drop(columns=["heat_certificate_total"])

                merged_df = grouped_df.merge(
                    df_building,
                    on="building_id",
                    how="inner",
                    suffixes=("", "_right"),
                )

                if merged_df.empty:
                    logger.warning(
                        "拠点ランキングレポートデータが存在しません、CSV出力をスキップします。"
                    )
                    merged_df = pd.DataFrame(columns=output_columns)
                else:
                    merged_df = merged_df.sort_values(by=CO2_COLUMN, ascending=False)
                    merged_df[RANK_COLUMN] = range(1, len(merged_df) + 1)

                    merged_df[CO2_COLUMN] = pd.to_numeric(
                        merged_df[CO2_COLUMN], errors="coerce"
                    )

                    total_co2 = merged_df[CO2_COLUMN].sum(skipna=True)
                    merged_df[CO2_SHARE_COLUMN] = 0.0
                    if pd.notnull(total_co2) and total_co2 > 0:
                        merged_df[CO2_SHARE_COLUMN] = (
                            merged_df[CO2_COLUMN].fillna(0.0) / float(total_co2) * 100
                        )

                    merged_df = merged_df.sort_values(
                        RANK_COLUMN, ascending=True
                    ).reset_index(drop=True)

                    area_series = pd.to_numeric(
                        merged_df.get("area_avg"), errors="coerce"
                    )
                    merged_df[AREA_COLUMN] = area_series
                    valid_area = area_series.where(area_series > 0)
                    co2_numeric = merged_df[CO2_COLUMN].fillna(0.0)
                    unit_series = co2_numeric.div(valid_area).fillna(0.0)
                    merged_df[UNIT_COLUMN] = unit_series

                    numeric_cols = [
                        CO2_COLUMN,
                        CO2_SHARE_COLUMN,
                        HEAT_COLUMN,
                        AREA_COLUMN,
                        UNIT_COLUMN,
                    ]
                    merged_df[numeric_cols] = merged_df[numeric_cols].apply(
                        pd.to_numeric, errors="coerce"
                    )

                    merged_df[CO2_COLUMN] = (
                        merged_df[CO2_COLUMN].round(0).astype("Int64")
                    )
                    merged_df[HEAT_COLUMN] = (
                        merged_df[HEAT_COLUMN].round(0).astype("Int64")
                    )

                    merged_df[CO2_SHARE_COLUMN] = merged_df[CO2_SHARE_COLUMN].apply(
                        lambda value: f"{round(value)}%" if pd.notnull(value) else ""
                    )

                    merged_df[AREA_COLUMN] = merged_df[AREA_COLUMN].apply(
                        lambda value: (
                            round(value) if pd.notnull(value) and value > 0 else ""
                        )
                    )

                    merged_df[UNIT_COLUMN] = (
                        merged_df[UNIT_COLUMN]
                        .fillna(0.0)
                        .apply(lambda value: f"{math.floor(value * 1000) / 1000:.3f}")
                    )

        merged_df = merged_df.reindex(columns=output_columns)

        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        timestamp = now_local.strftime("%Y%m%d_%H%M%S")
        filename = f"site_ranking_report_{timestamp}.csv"
        csv_str = merged_df.to_csv(index=False, lineterminator="\r\n")
        csv_bytes = csv_str.encode("utf-8-sig")

        return filename, csv_bytes
