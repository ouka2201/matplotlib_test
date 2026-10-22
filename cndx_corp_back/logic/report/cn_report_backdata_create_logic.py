import os
from datetime import datetime, timezone
from typing import Any, Dict, Set
from zoneinfo import ZoneInfo

import pandas as pd
from flask import current_app
from sqlalchemy import case, func, literal

import cndx_corp_back.common.constants_values as constants_values
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.logic.report.certificate_utils import (
    ELECTRIC_CERTIFICATE_CODES,
    HEAT_CERTIFICATE_CODES,
    apply_certificate_adjustments,
)
from cndx_corp_back.service.report.kpi_report_create_service import (
    calculate_additional_kpi_values,
)


def generate_month_list(start_ym: str, end_ym: str) -> Set[str]:
    """
    指定期間内の全月リストを生成する

    Args:
        start_ym: 開始年月 (YYYYMM形式)
        end_ym: 終了年月 (YYYYMM形式)

    Returns:
        Set[str]: 期間内の全月のセット (YYYYMM形式)
    """
    start_year = int(start_ym[:4])
    start_month = int(start_ym[4:6])
    end_year = int(end_ym[:4])
    end_month = int(end_ym[4:6])

    months = set()
    current_year = start_year
    current_month = start_month

    while (current_year < end_year) or (
        current_year == end_year and current_month <= end_month
    ):
        months.add(f"{current_year}{current_month:02d}")
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1

    return months


CERTIFICATE_CODE_SET = ELECTRIC_CERTIFICATE_CODES.union(HEAT_CERTIFICATE_CODES)


def _fetch_co2_certificate_df(
    session, corporate_number, agreement_category, org_id, start_ym, end_ym
):
    rows = (
        session.query(
            TMonthlyBuildingEnergyAggregation.building_id,
            TMonthlyBuildingEnergyAggregation.energy_code,
            func.sum(TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions).label(
                "co2_sum"
            ),
            func.sum(
                TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_zeb
            ).label("co2_zeb_sum"),
        )
        .where(
            TMonthlyBuildingEnergyAggregation.corporate_number == corporate_number,
            TMonthlyBuildingEnergyAggregation.agreement_category == agreement_category,
            TMonthlyBuildingEnergyAggregation.org_id == org_id,
            TMonthlyBuildingEnergyAggregation.registration_seq == 0,
            TMonthlyBuildingEnergyAggregation.target_year_month.between(
                str(start_ym), str(end_ym)
            ),
            TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
        )
        .group_by(
            TMonthlyBuildingEnergyAggregation.building_id,
            TMonthlyBuildingEnergyAggregation.energy_code,
        )
        .all()
    )

    if not rows:
        return pd.DataFrame(
            columns=["building_id", "energy_code", "co2_sum", "co2_zeb_sum"]
        )

    return pd.DataFrame(
        [{field: getattr(row, field) for field in row._fields} for row in rows]
    )


def _series_to_float_map(series: pd.Series) -> Dict[str, float]:
    if series is None or series.empty:
        return {}
    return {str(idx): float(value) for idx, value in series.items()}


def _calculate_adjusted_co2_totals(df: pd.DataFrame):
    if df is None or df.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    working_df = df.copy()
    working_df["building_id"] = working_df["building_id"].astype(str)
    working_df["energy_code"] = working_df["energy_code"].astype(str)
    working_df["co2_sum"] = pd.to_numeric(
        working_df["co2_sum"], errors="coerce"
    ).fillna(0.0)
    working_df["co2_zeb_sum"] = pd.to_numeric(
        working_df["co2_zeb_sum"], errors="coerce"
    ).fillna(0.0)

    co2_input = working_df.rename(columns={"co2_sum": "co2"})[
        ["building_id", "energy_code", "co2"]
    ]
    adjusted_df, heat_series = apply_certificate_adjustments(co2_input, "co2")
    if adjusted_df is None or adjusted_df.empty:
        adjusted_co2 = pd.Series(dtype=float)
    else:
        adjusted_co2 = adjusted_df.groupby("building_id")["co2"].sum()
    if heat_series is None or heat_series.empty:
        heat_series = pd.Series(dtype=float)
    adjusted_co2 = adjusted_co2.subtract(heat_series, fill_value=0.0).clip(lower=0.0)

    non_certificate_mask = ~working_df["energy_code"].isin(CERTIFICATE_CODE_SET)
    if non_certificate_mask.any():
        adjusted_co2_zeb = (
            working_df.loc[non_certificate_mask]
            .groupby("building_id")["co2_zeb_sum"]
            .sum()
        )
    else:
        adjusted_co2_zeb = pd.Series(dtype=float)
    adjusted_co2_zeb = adjusted_co2_zeb.clip(lower=0.0)

    return adjusted_co2, adjusted_co2_zeb


def _build_cn_status_dataframe(
    rows, adjusted_co2_series: pd.Series, adjusted_co2_zeb_series: pd.Series
):
    columns = ["building_id", "CN Status　エネルギー消費量", "CN Status　再エネ調達量"]
    if not rows:
        return pd.DataFrame(columns=columns)

    co2_map = _series_to_float_map(adjusted_co2_series)
    co2_zeb_map = _series_to_float_map(adjusted_co2_zeb_series)
    records = []

    for row in rows:
        building_id = getattr(row, "building_id", None)
        if building_id is None:
            continue
        building_id_str = str(building_id)
        heat_total = getattr(row, "heat_usage_total", 0)
        heat_total = float(heat_total or 0.0)
        co2_zeb_total = co2_zeb_map.get(building_id_str, 0.0)
        co2_total = co2_map.get(building_id_str, 0.0)
        procurement = 0.0
        if co2_zeb_total > 0:
            difference = max(co2_zeb_total - co2_total, 0.0)
            procurement = heat_total * difference / co2_zeb_total
        records.append(
            {
                "building_id": building_id_str,
                "CN Status　エネルギー消費量": heat_total,
                "CN Status　再エネ調達量": procurement,
            }
        )

    return pd.DataFrame(records, columns=columns)


class CnReportBackdataCreateLogic:
    """
    CNレポートバックデータ（CSV）作成ロジック
    """

    # @log_time
    def generate_csv_report(
        self, df_building, request_dict: Dict[str, Any], logger=None
    ) -> str:
        if logger is None:
            logger = current_app.logger

        logger.info("CNレポートバックデータ生成処理開始")

        # パラメータ取得
        corporate_number = request_dict["corporate_number"]
        agreement_category = request_dict["agreement_category"]
        org_id = request_dict["org_id"]
        consent_route = request_dict["consent_route"]
        start_ym = request_dict["start_year"] + request_dict["start_month"]
        end_ym = request_dict["end_year"] + request_dict["end_month"]
        last_start_ym = (
            str(int(request_dict["start_year"]) - 1) + request_dict["start_month"]
        )
        last_end_ym = str(int(request_dict["end_year"]) - 1) + request_dict["end_month"]
        period = (
            request_dict["start_year"]
            + "年"
            + request_dict["start_month"]
            + "月"
            + "～"
            + request_dict["end_year"]
            + "年"
            + request_dict["end_month"]
            + "月"
        )
        last_period = (
            str(int(request_dict["start_year"]) - 1)
            + "年"
            + request_dict["start_month"]
            + "月"
            + "～"
            + str(int(request_dict["end_year"]) - 1)
            + "年"
            + request_dict["end_month"]
            + "月"
        )
        # DataFrame初期化
        merged_year_energy_df = merged_energy_unit_df = merged_cn_status_current_df = (
            merged_cn_status_last_df
        ) = merged_kpi_df = merged_month_energy_df = pd.DataFrame()
        cn_status_current_df = pd.DataFrame()
        cn_status_last_df = pd.DataFrame()

        # エネルギーデータ取得
        with get_scoped_session() as session:
            # 熱量換算エネルギーを GJ 換算する式（MJ は 1/1000）
            heat_usage_gj_expr = case(
                (
                    func.upper(
                        func.trim(
                            TMonthlyBuildingEnergyAggregation.heat_converted_energy_unit
                        )
                    )
                    == literal("MJ"),
                    TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage
                    / literal(1000.0),
                ),
                else_=TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage,
            )

            year_energy_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    literal(period).label("期間"),
                    literal("使用実績（年次）").label("グラフ種別"),
                    TMonthlyBuildingEnergyAggregation.energy_category_name.label(
                        "項目"
                    ),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.energy_quantity_for_law
                    ).label("実績値"),
                    TMonthlyBuildingEnergyAggregation.energy_unit_for_law.label(
                        "実績値（単位）"
                    ),
                    func.sum(heat_usage_gj_expr).label("熱量換算エネルギー（GJ）"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                    ).label("CO2排出量（t-CO2）"),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        str(start_ym), str(end_ym)
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_category_name,
                    TMonthlyBuildingEnergyAggregation.energy_unit_for_law,
                )
                .all()
            )

            month_energy_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.target_year_month.label("期間"),
                    literal("使用実績（月次）").label("グラフ種別"),
                    TMonthlyBuildingEnergyAggregation.energy_category_name.label(
                        "項目"
                    ),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.energy_quantity_for_law
                    ).label("実績値"),
                    TMonthlyBuildingEnergyAggregation.energy_unit_for_law.label(
                        "実績値（単位）"
                    ),
                    func.sum(heat_usage_gj_expr).label("熱量換算エネルギー（GJ）"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                    ).label("CO2排出量（t-CO2）"),
                    func.max(
                        TMonthlyBuildingEnergyAggregation.temperature_building
                    ).label("平均気温"),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        str(start_ym), str(end_ym)
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_category_name,
                    TMonthlyBuildingEnergyAggregation.energy_unit_for_law,
                    TMonthlyBuildingEnergyAggregation.target_year_month,
                )
                .all()
            )

            energy_unit_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    literal(period).label("期間"),
                    literal("CO2排出量原単位の分布").label("グラフ種別"),
                    literal("CO2排出原単位").label("項目"),
                    func.round(
                        case(
                            (
                                func.avg(
                                    TMonthlyBuildingEnergyAggregation.gross_floor_area
                                )
                                == 0,
                                literal(0.0),
                            ),
                            (
                                func.avg(
                                    TMonthlyBuildingEnergyAggregation.gross_floor_area
                                ).is_(None),
                                literal(0.0),
                            ),
                            else_=(
                                func.sum(
                                    TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                                )
                                / func.avg(
                                    TMonthlyBuildingEnergyAggregation.gross_floor_area
                                )
                            ),
                        ),
                        3,
                    ).label("実績値"),
                    literal("t-CO2/㎡").label("実績値（単位）"),
                    literal("ー").label("熱量換算エネルギー（GJ）"),
                    literal("ー").label("CO2排出量（t-CO2）"),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        str(start_ym), str(end_ym)
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                )
                .all()
            )

            current_certificate_df = _fetch_co2_certificate_df(
                session,
                corporate_number,
                agreement_category,
                org_id,
                start_ym,
                end_ym,
            )
            current_adjusted_co2, current_adjusted_co2_zeb = (
                _calculate_adjusted_co2_totals(current_certificate_df)
            )

            cn_status_current_rows = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage_zeb
                    ).label("heat_usage_total"),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        str(start_ym), str(end_ym)
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                )
                .all()
            )
            cn_status_current_df = _build_cn_status_dataframe(
                cn_status_current_rows,
                current_adjusted_co2,
                current_adjusted_co2_zeb,
            )

            # 前年度期間の全月リストを生成
            required_last_year_months = generate_month_list(last_start_ym, last_end_ym)

            # DBに存在する前年度の月を取得
            existing_last_year_months_query = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.target_year_month.distinct()
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        str(last_start_ym), str(last_end_ym)
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
                .all()
            )

            existing_last_year_months = set(
                [row[0] for row in existing_last_year_months_query]
            )

            # 前年度の全月が存在するかチェック
            has_complete_last_year_data = required_last_year_months.issubset(
                existing_last_year_months
            )

            if has_complete_last_year_data:
                logger.info(
                    f"前年度期間 ({last_start_ym}～{last_end_ym}) の全月データが存在します。前年度CN Statusデータを取得します。"
                )
                last_certificate_df = _fetch_co2_certificate_df(
                    session,
                    corporate_number,
                    agreement_category,
                    org_id,
                    last_start_ym,
                    last_end_ym,
                )
                last_adjusted_co2, last_adjusted_co2_zeb = (
                    _calculate_adjusted_co2_totals(last_certificate_df)
                )

                cn_status_last_rows = (
                    session.query(
                        TMonthlyBuildingEnergyAggregation.building_id,
                        func.sum(
                            TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage_zeb
                        ).label("heat_usage_total"),
                    )
                    .where(
                        TMonthlyBuildingEnergyAggregation.corporate_number
                        == corporate_number,
                        TMonthlyBuildingEnergyAggregation.agreement_category
                        == agreement_category,
                        TMonthlyBuildingEnergyAggregation.org_id == org_id,
                        TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                        TMonthlyBuildingEnergyAggregation.target_year_month.between(
                            str(last_start_ym), str(last_end_ym)
                        ),
                        TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                    )
                    .group_by(
                        TMonthlyBuildingEnergyAggregation.corporate_number,
                        TMonthlyBuildingEnergyAggregation.agreement_category,
                        TMonthlyBuildingEnergyAggregation.org_id,
                        TMonthlyBuildingEnergyAggregation.building_id,
                    )
                    .all()
                )
                cn_status_last_df = _build_cn_status_dataframe(
                    cn_status_last_rows,
                    last_adjusted_co2,
                    last_adjusted_co2_zeb,
                )
            else:
                missing_months = required_last_year_months - existing_last_year_months
                logger.warning(
                    f"前年度期間 ({last_start_ym}～{last_end_ym}) に欠落月が存在します: {sorted(missing_months)}。前年度CN Statusデータをスキップします。"
                )
                cn_status_last_df = pd.DataFrame()

            # 注意：変数名を period_count に変更（period は既に文字列として定義済み）
            period_count = (
                session.query(
                    func.count(TMonthlyBuildingEnergyAggregation.target_year_month),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        str(last_start_ym), str(last_end_ym)
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
                .group_by(TMonthlyBuildingEnergyAggregation.target_year_month)
                .all()
            )

            # 企業名取得
            company_stmt = (
                session.query(
                    TCnApplicationInfo.org_id,
                    TCnApplicationInfo.company_name,
                    TCnApplicationInfo.competitor_industry_co2_avg,
                )
                .where(
                    TCnApplicationInfo.corporate_number == corporate_number,
                    TCnApplicationInfo.registration_seq == 0,
                )
                .all()
            )

            # KPI計算のためのエネルギーデータ取得
            building_ids = df_building["building_id"].dropna().tolist()
            kpi_energy_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_code,
                    TMonthlyBuildingEnergyAggregation.supplier_reg_no,
                    TMonthlyBuildingEnergyAggregation.fiscal_year,
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                    ).label("co2_sum"),
                    func.round(
                        func.avg(TMonthlyBuildingEnergyAggregation.gross_floor_area), 2
                    ).label("area_avg"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.credit_certificate_purchase_tco2_amount
                    ).label("credit_sum"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage
                    ).label("heat_energy_total"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.energy_quantity_for_law
                    ).label("energy_quantity_law"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_avg
                    ).label("co2_sum_avg"),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.building_id.in_(building_ids),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        start_ym, end_ym
                    ),
                )
                .group_by(
                    TMonthlyBuildingEnergyAggregation.corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id,
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_code,
                    TMonthlyBuildingEnergyAggregation.supplier_reg_no,
                    TMonthlyBuildingEnergyAggregation.fiscal_year,
                )
                .all()
            )

            # t_building_info から省エネ率分母/ベンチマーク指標を取得し、building_id単位で最新年度を優先して結合
            tbi_rows = (
                session.query(
                    TBuildingInfo.building_id,
                    TBuildingInfo.fiscal_year,
                    TBuildingInfo.energy_benchmark_indicator.label(
                        "省エネ法ベンチマーク指標"
                    ),
                    TBuildingInfo.energy_saving_denominator.label("省エネ率分母"),
                )
                .where(
                    TBuildingInfo.corporate_number == corporate_number,
                    TBuildingInfo.agreement_category == agreement_category,
                    TBuildingInfo.org_id == org_id,
                    TBuildingInfo.registration_seq == 0,
                    TBuildingInfo.building_id.in_(building_ids),
                )
                .all()
            )

            area_avg_map = {}
            for row in kpi_energy_stmt:
                building_id = getattr(row, "building_id", None)
                area_avg_value = getattr(row, "area_avg", None)
                if building_id is None or area_avg_value is None:
                    continue
                key = str(building_id)
                if key in area_avg_map:
                    continue
                try:
                    area_avg_map[key] = f"{float(area_avg_value):.2f}"
                except (TypeError, ValueError):
                    area_avg_map[key] = str(area_avg_value)

            if area_avg_map and "延床面積" in df_building.columns:
                df_building["延床面積"] = df_building["延床面積"].replace(
                    {"None": None}
                )
                blank_mask = (
                    df_building["延床面積"].fillna("").astype(str).str.strip().eq("")
                )
                missing_mask = df_building["延床面積"].isna() | blank_mask
                df_building.loc[missing_mask, "延床面積"] = df_building.loc[
                    missing_mask, "building_id"
                ].map(area_avg_map)

            # KPI計算
            df_kpi_energy = pd.DataFrame(
                [
                    {field: getattr(row, field) for field in row._fields}
                    for row in kpi_energy_stmt
                ],
                dtype=str,
            )

            # 省エネ率分母/ベンチマーク指標の結合（列名は計算関数が期待する日本語名に合わせる）
            try:
                if tbi_rows:
                    df_tbi = pd.DataFrame(
                        [
                            {field: getattr(row, field) for field in row._fields}
                            for row in tbi_rows
                        ]
                    )
                    if not df_tbi.empty:
                        # 年度が文字列の場合に備え、降順ソートして最新を採用
                        try:
                            df_tbi = df_tbi.sort_values(
                                by=["fiscal_year"], ascending=False
                            )
                        except Exception:
                            pass
                        df_tbi = df_tbi.drop_duplicates(
                            subset=["building_id"], keep="first"
                        )
                        df_kpi_energy = df_kpi_energy.merge(
                            df_tbi[
                                [
                                    "building_id",
                                    "省エネ法ベンチマーク指標",
                                    "省エネ率分母",
                                ]
                            ],
                            on="building_id",
                            how="left",
                        )
            except Exception:
                # 分母/指標の結合はベストエフォート。失敗しても後続で0扱いになる。
                pass

            if not df_kpi_energy.empty:
                # 判定フラグを取得（df_buildingに含まれる想定）
                judgeFlag = (
                    str(df_building["判定フラグ"].iloc[0])
                    if "判定フラグ" in df_building.columns and not df_building.empty
                    else "0"
                )
                df_kpi_energy = calculate_additional_kpi_values(
                    session, df_kpi_energy, judgeFlag, logger
                )
                kpi_value_columns = [
                    "KPI省エネ率",
                    "KPI電化率",
                    "KPI創エネ率",
                    "KPICN率",
                ]
                #  kpi_value_columnsがフラットリストであるのを確認する
                if kpi_value_columns and isinstance(kpi_value_columns[0], list):
                    kpi_value_columns = [
                        item for sublist in kpi_value_columns for item in sublist
                    ]
                df_kpi_selected = df_kpi_energy[["building_id"] + kpi_value_columns]
                # 既存のKPI列は最新値で置き換えるため一旦削除してからマージする
                df_building = df_building.drop(
                    columns=kpi_value_columns, errors="ignore"
                )
                df_building = df_building.merge(
                    df_kpi_selected, on="building_id", how="left"
                )
            else:
                # KPI計算データがない場合は0で埋める
                df_building["KPI省エネ率"] = None
                df_building["KPI電化率"] = None
                df_building["KPI創エネ率"] = None
                df_building["KPICN率"] = None

        kpi_df = kpi_df_data(df_building, period)

        # DataFrameへ変換
        year_energy_df = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in year_energy_stmt
            ],
            dtype=str,
        )
        energy_unit_df = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in energy_unit_stmt
            ],
            dtype=str,
        )
        company_df = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in company_stmt
            ],
            dtype=str,
        )
        month_energy_df = get_temprature_data(month_energy_stmt)
        # 直近1年
        if not cn_status_current_df.empty:
            cn_status_current_df = cn_status(cn_status_current_df, period)
        # 過年度
        # if not cn_status_last_df.empty and period == 12:
        if not cn_status_last_df.empty:
            cn_status_last_df = cn_status(cn_status_last_df, last_period)

        # 可視化事業者
        df_building["可視化事業者"] = consent_route
        if company_stmt:
            # 企業名取得
            df_building["企業名"] = company_df["company_name"].iloc[0]
        else:
            df_building["企業名"] = None
        # 検索情報拠点情報絞り
        if not year_energy_df.empty:
            merged_year_energy_df = df_building.merge(
                year_energy_df, on="building_id", how="inner", suffixes=("", "_right")
            )
        if not month_energy_df.empty:
            merged_month_energy_df = df_building.merge(
                month_energy_df, on="building_id", how="inner", suffixes=("", "_right")
            )
        if not energy_unit_df.empty:
            merged_energy_unit_df = df_building.merge(
                energy_unit_df, on="building_id", how="inner", suffixes=("", "_right")
            )
        if not kpi_df.empty:
            merged_kpi_df = df_building.merge(
                kpi_df, on="building_id", how="inner", suffixes=("", "_right")
            )
        if not cn_status_current_df.empty:
            merged_cn_status_current_df = df_building.merge(
                cn_status_current_df,
                on="building_id",
                how="inner",
                suffixes=("", "_right"),
            )
        # if not cn_status_last_df.empty and period == 12:
        if not cn_status_last_df.empty:
            merged_cn_status_last_df = df_building.merge(
                cn_status_last_df,
                on="building_id",
                how="inner",
                suffixes=("", "_right"),
            )

        # 最終的な列順序
        final_cols = [
            "可視化事業者",
            "企業名",
            "グループ1",
            "グループ2",
            "グループ3",
            "グループ4",
            "グループ5",
            "拠点識別番号",
            "拠点識別名",
            "住所都道府県",
            "住所",
            "お客さま番号",
            "供給地点特定番号",
            "業種",
            "省エネ法ベンチマーク業種",
            "他社比較業種",
            "延床面積",
            "グラフ種別",
            "期間",
            "項目",
            "実績値",
            "実績値（単位）",
            "熱量換算エネルギー（GJ）",
            "CO2排出量（t-CO2）",
        ]

        # 対象列の絞り込み
        if not year_energy_df.empty:
            merged_year_energy_df = merged_year_energy_df[final_cols]
        if not energy_unit_df.empty:
            merged_energy_unit_df = merged_energy_unit_df[final_cols]
        if not kpi_df.empty:
            merged_kpi_df = merged_kpi_df[final_cols]
        if not month_energy_df.empty:
            merged_month_energy_df = merged_month_energy_df[final_cols]
        if not cn_status_current_df.empty:
            merged_cn_status_current_df = merged_cn_status_current_df[final_cols]
        # if not cn_status_last_df.empty and period == 12:
        if not cn_status_last_df.empty:
            merged_cn_status_last_df = merged_cn_status_last_df[final_cols]

        # CN Status データを拠点識別番号ごとに並び替え
        # 同一拠点の場合、当年度データの直後に前年度データを配置
        merged_cn_status_df = pd.DataFrame()
        if not merged_cn_status_current_df.empty or not merged_cn_status_last_df.empty:
            # 両方のデータフレームを結合
            cn_status_combined = pd.concat(
                [merged_cn_status_current_df, merged_cn_status_last_df],
                ignore_index=True,
            )

            # 重複行を削除（全列が同じ行を削除）
            cn_status_combined = cn_status_combined.drop_duplicates(
                subset=final_cols, keep="first"
            )

            # 拠点識別番号と期間でソート
            # 期間を降順にすることで、同一拠点の当年度が前年度の前に来る
            cn_status_combined["_period_sort"] = cn_status_combined["期間"].apply(
                lambda x: 1 if "2024" in str(x) or "2025" in str(x) else 0
            )
            merged_cn_status_df = (
                cn_status_combined.sort_values(
                    by=["拠点識別番号", "_period_sort", "項目"],
                    ascending=[True, False, True],
                )
                .drop(columns=["_period_sort"])
                .reset_index(drop=True)
            )

        merged_df = pd.concat(
            [
                merged_year_energy_df,
                merged_energy_unit_df,
                merged_cn_status_df,
                merged_kpi_df,
                merged_month_energy_df,
            ],
            ignore_index=True,
        )

        # 数値列を四捨五入して整数に変換
        def round_to_int(value):
            # 特殊値（"ー"など）はそのまま返す
            if pd.isna(value) or value in ["ー", "-", "", "None", None]:
                return value

            # 文字列の場合、%を削除してから処理
            if isinstance(value, str):
                # %付きの値を処理（例: "0.00%" → 0）
                if "%" in value:
                    try:
                        # %を削除して数値化
                        num_str = value.replace("%", "").strip()
                        num = float(num_str)
                        return str(int(round(num)))
                    except (ValueError, TypeError):
                        return value

            # 数値に変換を試みる
            try:
                num = pd.to_numeric(value, errors="coerce")
                if pd.notna(num):
                    return str(int(round(num)))
                return value
            except (ValueError, TypeError):
                return value

        # 出力列すべてに四捨五入処理を適用（除外列はスキップ）
        round_exclude_columns = {"他社比較業種"}
        for column_name in merged_df.columns:
            if column_name in round_exclude_columns:
                continue
            merged_df[column_name] = merged_df[column_name].apply(round_to_int)

        # CSV 出力
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        timestamp = now_local.strftime("%Y%m%d_%H%M%S")
        filename = f"cn_report_backdata_{timestamp}.csv"

        csv_str = merged_df.to_csv(index=False, lineterminator="\r\n")
        csv_bytes = csv_str.encode("utf-8-sig")

        return filename, csv_bytes


def kpi_df_data(df_building, period):
    # 必要列の数値化（NaNは残す）
    kpi_cols = ["KPI省エネ率", "KPI電化率", "KPI創エネ率", "KPICN率"]
    tmp = df_building.copy()

    # KPI値を百分比に変換（×100、小数点2桁、%付き）
    def to_percentage(value):
        try:
            return f"{float(value) * 100:.2f}%"
        except (ValueError, TypeError):
            return "0.00%"

    # KPI電化率は整数に四捨五入（column21）
    def to_percentage_int(value):
        try:
            result = round(float(value) * 100)
            return str(result)
        except (ValueError, TypeError):
            return "0"

    for c in kpi_cols:
        if c in tmp.columns:
            if c == "KPI電化率":
                # 電化率は整数（単位なし、column22に%があるため）
                tmp[c] = tmp[c].apply(
                    lambda x: to_percentage_int(x) if pd.notnull(x) else "0"
                )
            else:
                tmp[c] = tmp[c].apply(
                    lambda x: to_percentage(x) if pd.notnull(x) else "0.00%"
                )

    # ワイド→ロング（building_id ごとに 4 行）
    kpi_df = tmp.melt(
        id_vars=["building_id"],
        value_vars=kpi_cols,
        var_name="項目",
        value_name="実績値",
    )

    # 付加列・並び
    # period が空またはリストの場合のハンドリング
    if isinstance(period, (list, tuple)):
        period_value = period[0] if len(period) > 0 else ""
    else:
        period_value = str(period) if period is not None else ""

    kpi_df["期間"] = period_value
    kpi_df["グラフ種別"] = "KPI"
    kpi_df["実績値（単位）"] = "%"
    kpi_df["熱量換算エネルギー（GJ）"] = "ー"
    kpi_df["CO2排出量（t-CO2）"] = "ー"
    kpi_df = kpi_df[
        [
            "building_id",
            "期間",
            "グラフ種別",
            "項目",
            "実績値",
            "実績値（単位）",
            "熱量換算エネルギー（GJ）",
            "CO2排出量（t-CO2）",
        ]
    ]

    return kpi_df


def cn_status(cn_status_df, period):

    cn_status_cols = ["CN Status　エネルギー消費量", "CN Status　再エネ調達量"]
    tmp = cn_status_df.copy()
    for c in cn_status_cols:
        tmp[c] = pd.to_numeric(tmp[c], errors="coerce")

    # ワイド→ロング（building_id ごとに 4 行）
    cn_status_df = tmp.melt(
        id_vars=["building_id"],
        value_vars=cn_status_cols,
        var_name="項目",
        value_name="実績値",
    )

    # period が空またはリストの場合のハンドリング
    if isinstance(period, (list, tuple)):
        period_value = period[0] if len(period) > 0 else ""
    else:
        period_value = str(period) if period is not None else ""

    cn_status_df["期間"] = period_value
    cn_status_df["グラフ種別"] = "CN Status"
    cn_status_df["実績値（単位）"] = "GJ"
    cn_status_df["熱量換算エネルギー（GJ）"] = "ー"
    cn_status_df["CO2排出量（t-CO2）"] = "ー"

    cn_status_df = cn_status_df[
        [
            "building_id",
            "期間",
            "グラフ種別",
            "項目",
            "実績値",
            "実績値（単位）",
            "熱量換算エネルギー（GJ）",
            "CO2排出量（t-CO2）",
        ]
    ]

    return cn_status_df


# @log_time
def get_temprature_data(month_energy_stmt):
    # 列名の並び替え
    cols = [
        "building_id",
        "期間",
        "グラフ種別",
        "項目",
        "実績値",
        "実績値（単位）",
        "熱量換算エネルギー（GJ）",
        "CO2排出量（t-CO2）",
        "平均気温",
    ]
    df = pd.DataFrame.from_records(month_energy_stmt, columns=cols)

    # 期間 202304 -> "2023年4月"
    def ym_to_label(ym):
        s = str(ym)
        y, m = int(s[:4]), int(s[4:6])
        return f"{y}年{m}月"

    df["期間"] = df["期間"].map(ym_to_label)

    # 3) "平均気温"行を生成（名称は「項目」に、数値は「実績値」に、単位は ℃）
    # building_idごとに気温を設定
    # 修正：building_id と期間でグループ化し、最初の非NULL気温値を取得
    temp_rows = (
        df[["building_id", "期間", "平均気温"]]
        .groupby(["building_id", "期間"], as_index=False)
        .agg(
            {"平均気温": lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else None}
        )
        .rename(columns={"平均気温": "実績値"})
        .assign(
            グラフ種別="使用実績（月次）",
            項目="平均気温",
            **{"実績値（単位）": "℃"},
            **{"熱量換算エネルギー（GJ）": None},
            **{"CO2排出量（t-CO2）": None},
        )
    )

    energy_rows = df.drop(columns=["平均気温"])

    energy_cols = energy_rows.columns
    result = pd.concat([energy_rows, temp_rows[energy_cols]], ignore_index=True)

    final_cols = [
        "building_id",
        "グラフ種別",
        "期間",
        "項目",
        "実績値",
        "実績値（単位）",
        "熱量換算エネルギー（GJ）",
        "CO2排出量（t-CO2）",
    ]
    result = result.reindex(columns=[c for c in final_cols if c in result.columns])

    result = result.where(pd.notna(result), None)

    _ym = result["期間"].str.extract(r"(?P<Y>\d{4})年(?P<M>\d{1,2})月").astype(int)
    result["_ym_sort"] = _ym["Y"] * 100 + _ym["M"]

    result["_is_temp"] = (result["項目"] == "平均気温").astype(int)

    # 平均気温の並び替え
    result = (
        result.sort_values(
            ["building_id", "_ym_sort", "_is_temp", "項目"],
            ascending=[True, True, True, True],
        )
        .drop(columns=["_ym_sort", "_is_temp"])
        .reset_index(drop=True)
    )

    return result
