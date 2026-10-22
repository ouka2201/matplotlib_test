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
ENERGY_COLUMN = "エネルギー種別"
USAGE_COLUMN = "年間使用量"
HEAT_COLUMN = "熱量換算量(GJ)"
PREV_CO2_COLUMN = "前年CO2排出量"
PREV_HEAT_COLUMN = "前年熱量換算量(GJ)"
CO2_SHARE_COLUMN = "CO2排出量占有率"
HEAT_SHARE_COLUMN = "熱量換算量占有率"
RANK_COLUMN = "順位"
YOY_CO2_COLUMN = "前年比増減率"
YOY_HEAT_COLUMN = "前年比増減率(GJ)"


class CnEnergyRankingReportLogic:
    """エネルギーランキングCSV生成ロジック"""

    OUTPUT_DIR = r"C:\HZY\FILE DOWNLOAD\TEST"

    def generate_energy_ranking_csv(
        self,
        df_building,
        request_dict: Dict[str, Any],
        logger=None,
    ) -> str:
        if logger is None:
            logger = current_app.logger

        logger.info("エネルギーランキングレポート生成処理開始")

        corporate_number = request_dict["corporate_number"]
        agreement_category = request_dict["agreement_category"]
        org_id = request_dict["org_id"]
        start_ym = request_dict["start_year"] + request_dict["start_month"]
        end_ym = request_dict["end_year"] + request_dict["end_month"]
        last_start_ym = str(int(start_ym) - 100)
        last_end_ym = str(int(end_ym) - 100)

        df_current, df_last = self._load_energy_usage_frames(
            corporate_number,
            agreement_category,
            org_id,
            start_ym,
            end_ym,
            last_start_ym,
            last_end_ym,
        )

        if df_current.empty:
            logger.warning("対象データが存在しません、CSV出力をスキップします。")
            return ""

        for column in (USAGE_COLUMN, CO2_COLUMN, HEAT_COLUMN):
            df_current[column] = pd.to_numeric(
                df_current.get(column), errors="coerce"
            ).fillna(0)

        df_current, heat_cert_current = apply_certificate_adjustments(
            df_current, CO2_COLUMN
        )
        df_current = self._apply_heat_certificate_deduction(
            df_current, CO2_COLUMN, heat_cert_current
        )
        if df_current.empty:
            logger.warning(
                "証書調整後の対象データが存在しません、CSV出力をスキップします。"
            )
            return ""

        if not df_last.empty:
            for column in (PREV_CO2_COLUMN, PREV_HEAT_COLUMN):
                df_last[column] = pd.to_numeric(
                    df_last.get(column), errors="coerce"
                ).fillna(0)
            df_last, heat_cert_last = apply_certificate_adjustments(
                df_last, PREV_CO2_COLUMN
            )
            df_last = self._apply_heat_certificate_deduction(
                df_last, PREV_CO2_COLUMN, heat_cert_last
            )

        df_current = df_current.merge(
            df_building,
            on="building_id",
            how="inner",
            suffixes=("", "_right"),
        )
        if df_current.empty:
            logger.warning(
                "対象建物に一致するデータがありません、CSV出力をスキップします。"
            )
            return ""

        if not df_last.empty:
            df_last = df_last.merge(
                df_building,
                on="building_id",
                how="inner",
                suffixes=("", "_right"),
            )

        if df_last.empty:
            combined_df = df_current.copy()
            combined_df[PREV_CO2_COLUMN] = 0
            combined_df[PREV_HEAT_COLUMN] = 0
        else:
            combined_df = df_current.merge(
                df_last,
                on=["building_id", ENERGY_COLUMN],
                how="left",
                suffixes=("", "_prev"),
            )
            combined_df[PREV_CO2_COLUMN] = combined_df[PREV_CO2_COLUMN].fillna(0)
            combined_df[PREV_HEAT_COLUMN] = combined_df[PREV_HEAT_COLUMN].fillna(0)

        grouped = combined_df.groupby(ENERGY_COLUMN, as_index=False)[
            [
                USAGE_COLUMN,
                CO2_COLUMN,
                HEAT_COLUMN,
                PREV_CO2_COLUMN,
                PREV_HEAT_COLUMN,
            ]
        ].sum()

        total_co2 = grouped[CO2_COLUMN].sum()
        total_heat = grouped[HEAT_COLUMN].sum()
        grouped[CO2_SHARE_COLUMN] = (
            grouped[CO2_COLUMN] / total_co2 if total_co2 > 0 else 0.0
        )
        grouped[HEAT_SHARE_COLUMN] = (
            grouped[HEAT_COLUMN] / total_heat if total_heat > 0 else 0.0
        )

        grouped[YOY_CO2_COLUMN] = grouped.apply(
            lambda row: (
                (row[CO2_COLUMN] - row[PREV_CO2_COLUMN]) / row[PREV_CO2_COLUMN]
                if row[PREV_CO2_COLUMN] not in (0, None)
                else "ー"
            ),
            axis=1,
        )
        grouped[YOY_HEAT_COLUMN] = grouped.apply(
            lambda row: (
                (row[HEAT_COLUMN] - row[PREV_HEAT_COLUMN]) / row[PREV_HEAT_COLUMN]
                if row[PREV_HEAT_COLUMN] not in (0, None)
                else "ー"
            ),
            axis=1,
        )

        grouped[RANK_COLUMN] = (
            grouped[CO2_COLUMN].rank(method="first", ascending=False).astype(int)
        )
        grouped = grouped.sort_values(RANK_COLUMN).reset_index(drop=True)

        grouped[CO2_SHARE_COLUMN] = grouped[CO2_SHARE_COLUMN].apply(
            self._format_percentage
        )
        grouped[HEAT_SHARE_COLUMN] = grouped[HEAT_SHARE_COLUMN].apply(
            self._format_percentage
        )
        grouped[YOY_CO2_COLUMN] = grouped[YOY_CO2_COLUMN].apply(self._format_percentage)
        grouped[YOY_HEAT_COLUMN] = grouped[YOY_HEAT_COLUMN].apply(
            self._format_percentage
        )

        for column in (USAGE_COLUMN, CO2_COLUMN, HEAT_COLUMN):
            grouped[column] = grouped[column].round(0).astype(int)

        grouped = grouped[
            [
                RANK_COLUMN,
                ENERGY_COLUMN,
                USAGE_COLUMN,
                CO2_COLUMN,
                CO2_SHARE_COLUMN,
                YOY_CO2_COLUMN,
                HEAT_COLUMN,
                HEAT_SHARE_COLUMN,
                YOY_HEAT_COLUMN,
            ]
        ]

        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        timestamp = now_local.strftime("%Y%m%d_%H%M%S")
        filename = f"energy_ranking_{corporate_number}_{timestamp}.csv"
        csv_str = grouped.to_csv(index=False, lineterminator="\r\n")
        csv_bytes = csv_str.encode("utf-8-sig")

        return filename, csv_bytes

    def _load_energy_usage_frames(
        self,
        corporate_number: str,
        agreement_category: str,
        org_id: str,
        start_ym: str,
        end_ym: str,
        last_start_ym: str,
        last_end_ym: str,
    ):
        with get_scoped_session() as session:
            current_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_code.label("energy_code"),
                    TMonthlyBuildingEnergyAggregation.energy_category_name.label(
                        ENERGY_COLUMN
                    ),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.energy_quantity_for_report
                    ).label(USAGE_COLUMN),
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
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        start_ym, end_ym
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_code,
                    TMonthlyBuildingEnergyAggregation.energy_category_name,
                )
                .all()
            )

            last_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_code.label("energy_code"),
                    TMonthlyBuildingEnergyAggregation.energy_category_name.label(
                        ENERGY_COLUMN
                    ),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                    ).label(PREV_CO2_COLUMN),
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
                    ).label(PREV_HEAT_COLUMN),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        last_start_ym, last_end_ym
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_code,
                    TMonthlyBuildingEnergyAggregation.energy_category_name,
                )
                .all()
            )

        df_current = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in current_stmt
            ]
        )
        df_last = pd.DataFrame(
            [{field: getattr(row, field) for field in row._fields} for row in last_stmt]
        )
        return df_current, df_last

    @staticmethod
    def _format_percentage(value):
        if isinstance(value, (int, float)) and pd.notnull(value):
            return f"{round(value * 100)}%"
        return value if isinstance(value, str) else "ー"

    @staticmethod
    def _apply_heat_certificate_deduction(
        df: pd.DataFrame, co2_column: str, heat_series: pd.Series
    ):
        if df is None or df.empty:
            return df
        if heat_series is None or heat_series.empty:
            return df
        if "building_id" not in df.columns or co2_column not in df.columns:
            return df

        adjusted_df = df.copy()
        heat_series = pd.to_numeric(heat_series, errors="coerce").fillna(0)

        for building_id, certificate_value in heat_series.items():
            if certificate_value <= 0:
                continue

            mask = adjusted_df["building_id"] == building_id
            if not mask.any():
                continue

            building_values = pd.to_numeric(
                adjusted_df.loc[mask, co2_column], errors="coerce"
            ).fillna(0)
            current_total = building_values.sum()
            if current_total <= 0:
                adjusted_df.loc[mask, co2_column] = 0
                continue

            new_total = max(current_total - certificate_value, 0)
            if new_total == 0:
                adjusted_df.loc[mask, co2_column] = 0
            else:
                scale = new_total / current_total
                adjusted_df.loc[mask, co2_column] = building_values * scale

        return adjusted_df
