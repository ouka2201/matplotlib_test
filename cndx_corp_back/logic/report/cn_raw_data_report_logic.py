import os
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pandas as pd
from flask import current_app
from sqlalchemy import func, select

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.ext import db


class CnRawDataReportLogic:
    """
    生データ一覧レポート（CSV）作成ロジック
    """

    # @log_time
    def generate_raw_data_csv(
        self, df_building, request_dict: Dict[str, Any], logger=None
    ) -> str:
        if logger is None:
            logger = current_app.logger

        logger.info("生データ一覧レポート生成処理開始")

        # パラメータ取得
        corporate_number = request_dict["corporate_number"]
        agreement_category = request_dict["agreement_category"]
        org_id = request_dict["org_id"]
        consent_route = request_dict["consent_route"]
        start_ym = request_dict["start_year"] + request_dict["start_month"]
        end_ym = request_dict["end_year"] + request_dict["end_month"]

        # 年度別エネルギーデータ取得
        with get_scoped_session() as session:
            energy_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.target_year_month.label("年月"),
                    TMonthlyBuildingEnergyAggregation.energy_category_name.label(
                        "項目"
                    ),
                    TMonthlyBuildingEnergyAggregation.supplier_name.label("供給事業者"),
                    TMonthlyBuildingEnergyAggregation.supply_menu.label("メニュー"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.energy_quantity_for_report
                    ).label("使用量"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                    ).label("co2_sum"),
                    func.round(
                        func.avg(TMonthlyBuildingEnergyAggregation.gross_floor_area), 2
                    ).label("area_avg"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_area_unit
                    ).label("CO2排出原単位（t-CO2/㎡）"),
                    TMonthlyBuildingEnergyAggregation.energy_unit_for_report.label(
                        "使用量（単位）"
                    ),
                    func.max(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emission_factor
                    ).label("CO2排出係数"),
                    TMonthlyBuildingEnergyAggregation.co2_adjusted_emission_factor_source.label(
                        "CO2排出係数データソース"
                    ),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                    ).label("CO2排出量（t-CO2）"),
                    func.max(
                        TMonthlyBuildingEnergyAggregation.heat_conversion_coefficient
                    ).label("熱量換算係数"),
                    TMonthlyBuildingEnergyAggregation.heat_conversion_coefficient_source.label(
                        "熱量換算係数データソース"
                    ),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage
                    ).label("熱量換算エネルギー（GJ）"),
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
                    TMonthlyBuildingEnergyAggregation.target_year_month,
                    TMonthlyBuildingEnergyAggregation.energy_category_name,
                    TMonthlyBuildingEnergyAggregation.supplier_name,
                    TMonthlyBuildingEnergyAggregation.supply_menu,
                    TMonthlyBuildingEnergyAggregation.energy_unit_for_report,
                    TMonthlyBuildingEnergyAggregation.co2_adjusted_emission_factor_source,
                    TMonthlyBuildingEnergyAggregation.heat_conversion_coefficient_source,
                )
                .all()
            )
            # 企業名取得
            company_stmt = session.query(
                TCnApplicationInfo.org_id,
                TCnApplicationInfo.company_name,
                TCnApplicationInfo.energy_benchmark_target_industry,
                TCnApplicationInfo.competitor_industry_co2_avg,
            ).where(
                TCnApplicationInfo.corporate_number == corporate_number,
                TCnApplicationInfo.delete_flg.is_not(True),
            )

        company_df = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in company_stmt
            ],
            dtype=str,
        )
        df_energy = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in energy_stmt
            ],
            dtype=str,
        )

        if df_energy.empty:
            logger.warning(
                "生データ一覧レポートデータが存在しません。CSV出力をスキップします。"
            )
            # return ""
        else:
            merged_df = df_energy.merge(
                df_building, on="building_id", how="inner", suffixes=("", "_right")
            )  # df_energy 側はそのまま

        if merged_df.empty:
            logger.warning(
                "生データ一覧レポートデータが存在しません。CSV出力をスキップします。"
            )
            # return ""
            merged_df = pd.DataFrame(
                columns=[
                    "可視化事業者",
                    "企業名",
                    "拠点識別番号",
                    "拠点識別名",
                    "住所都道府県",
                    "住所",
                    "事業所コード",
                    "お客さま番号",
                    "供給地点特定番号",
                    "業種",
                    "他社比較業種",
                    "平均面積",
                    "グループ1",
                    "グループ2",
                    "グループ3",
                    "グループ4",
                    "グループ5",
                    "年月",
                    "項目",
                    "昼夜間",
                    "供給圧力",
                    "供給事業者",
                    "メニュー",
                    "使用量",
                    "使用量（単位）",
                    "CO2排出原単位（t-CO2/㎡）",
                    "CO2排出係数",
                    "CO2排出係数データソース",
                    "CO2排出量（t-CO2）",
                    "熱量換算係数",
                    "熱量換算係数データソース",
                    "熱量換算エネルギー（GJ）",
                ]
            )
        else:
            # 可視化事業者名を設定
            merged_df["可視化事業者"] = consent_route

            org_company_map = company_df.set_index("org_id")["company_name"].to_dict()
            merged_df["企業名"] = org_company_map.get(org_id, "")

            merged_df["他社比較業種"] = ""

            if merged_df["building_id"].nunique(dropna=False) > 1:
                merged_df["他社比較業種"] = company_df[
                    "competitor_industry_co2_avg"
                ].iloc[0]

            merged_df["昼夜間"] = "ー"
            merged_df["供給圧力"] = ""

            def _to_float(value):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0

            def _format_area(value):
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    return ""
                return f"{numeric:.2f}" if numeric > 0 else ""

            co2_unit_values = []
            for _, row in merged_df.iterrows():
                co2_value = row.get("co2_sum")
                if not co2_value:
                    co2_value = row.get("CO2排出量（t-CO2）")
                co2_sum_float = _to_float(co2_value)
                area_sum_float = _to_float(row.get("area_avg"))
                co2_unit = (
                    round(co2_sum_float / area_sum_float, 2)
                    if area_sum_float > 0
                    else 0.0
                )
                co2_unit_values.append(co2_unit)

            merged_df["CO2排出原単位（t-CO2/㎡）"] = [
                f"{value:.2f}" for value in co2_unit_values
            ]
            merged_df["平均面積"] = merged_df["area_avg"].apply(_format_area)

            # 最終的な列順序
            final_cols = [
                "可視化事業者",
                "企業名",
                "拠点識別番号",
                "拠点識別名",
                "住所都道府県",
                "住所",
                "事業所コード",
                "お客さま番号",
                "供給地点特定番号",
                "業種",
                "他社比較業種",
                "平均面積",
                "グループ1",
                "グループ2",
                "グループ3",
                "グループ4",
                "グループ5",
                "年月",
                "項目",
                "昼夜間",
                "供給圧力",
                "供給事業者",
                "メニュー",
                "使用量",
                "使用量（単位）",
                "CO2排出原単位（t-CO2/㎡）",
                "CO2排出係数",
                "CO2排出係数データソース",
                "CO2排出量（t-CO2）",
                "熱量換算係数",
                "熱量換算係数データソース",
                "熱量換算エネルギー（GJ）",
            ]
            merged_df = merged_df[final_cols]

        # 出力ディレクトリ作成とファイル保存
        # os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        timestamp = now_local.strftime("%Y%m%d_%H%M%S")
        filename = f"raw_data_report_{timestamp}.csv"
        # output_path = os.path.join(self.OUTPUT_DIR, filename)

        csv_str = merged_df.to_csv(index=False, lineterminator="\r\n")
        csv_bytes = csv_str.encode("utf-8-sig")

        # logger.info(f"生データ一覧レポートCSVを出力しました: {output_path}")
        return filename, csv_bytes
