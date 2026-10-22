import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pandas as pd
from flask import current_app
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import scoped_session

from cndx_corp_back.dto.report.cn_karte_create_vis_in_dto import (
    CreateCnKarteVisInDto as VisInDto,
)
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)


class KPIReportCreateLogic:
    OUTPUT_DIR = r"C:\HZY\FILE DOWNLOAD\TEST"

    def _calculate_additional_kpi_values(self, session, df: pd.DataFrame, dto) -> dict:
        """
        update_building_info_for_kpi関数の計算ロジックを基にした追加KPI値の計算
        """
        try:
            from cndx_corp_back.common import constants_values
            from cndx_corp_back.entity.t_cn_application_info_entity import (
                TCnApplicationInfo,
            )

            energy_saving_denominator = 0
            energy_benchmark_indicator_avg = 0
            print_mode = 0  # デフォルト企業全体(地銀も)
            fiscal_years = df["fiscal_year"].dropna().unique().tolist()

            if isinstance(dto, VisInDto):
                # 可視化側：条件によって分岐
                # 単拠点の場合
                if (
                    hasattr(dto, "building_ids_for_single")
                    and dto.building_ids_for_single
                ):
                    print_mode = 2
                elif hasattr(dto, "is_for_multibuilding") and dto.is_for_multibuilding:
                    if (
                        hasattr(dto, "group_for_multibuilding")
                        and dto.group_for_multibuilding
                    ):
                        # グループの場合
                        print_mode = 1

            # 企業全体の場合
            if print_mode == 0:
                # CN申請情報取得
                cnapp_info_list = (
                    session.query(TCnApplicationInfo)
                    .filter(
                        TCnApplicationInfo.corporate_number == dto.corporate_number,
                        TCnApplicationInfo.agreement_category
                        == getattr(dto, "agreement_category", "01"),
                        TCnApplicationInfo.org_id == dto.org_id,
                        TCnApplicationInfo.registration_seq
                        == int(df["registration_seq"].iloc[0]),
                        # TCnApplicationInfo.fiscal_year==getattr(dto, 'fiscal_year', getattr(dto, 'start_year', 2024))
                        TCnApplicationInfo.fiscal_year.in_(fiscal_years),
                    )
                    .all()
                )

                if not cnapp_info_list:
                    return {
                        "kpi_energy_saving_rate": None,
                        "kpi_electrification_rate": None,
                        "kpi_energy_creation_rate": None,
                        "kpi_renewable_network_rate": None,
                    }
                # energy_saving_denominator = getattr(cnapp_info_list[0], 'energy_saving_denominator', 0)
                # competitor_industry_co2_avg = getattr(cnapp_info_list[0], 'competitor_industry_co2_avg', 0)
                # 平均値取得
                energy_saving_denominator = (
                    statistics.mean(
                        [
                            item.energy_saving_denominator
                            for item in cnapp_info_list
                            if item.energy_saving_denominator is not None
                        ]
                    )
                    if any(
                        item.energy_saving_denominator is not None
                        for item in cnapp_info_list
                    )
                    else None
                )

                energy_benchmark_indicator_avg = (
                    statistics.mean(
                        [
                            float(item.energy_benchmark_indicator)
                            for item in cnapp_info_list
                            if item.energy_benchmark_indicator is not None
                        ]
                    )
                    if any(
                        float(item.energy_benchmark_indicator) is not None
                        for item in cnapp_info_list
                    )
                    else None
                )

            # グループ、単拠点の場合
            else:
                # 対象拠点id取得
                building_ids = df["building_id"].dropna().unique().tolist()
                # 建物情報取得
                t_building_info_list = (
                    session.query(TBuildingInfo)
                    .filter(
                        TBuildingInfo.corporate_number == dto.corporate_number,
                        TBuildingInfo.agreement_category
                        == getattr(dto, "agreement_category", "01"),
                        TBuildingInfo.org_id == dto.org_id,
                        TBuildingInfo.registration_seq
                        == int(df["registration_seq"].iloc[0]),
                        # TBuildingInfo.fiscal_year==getattr(dto, 'fiscal_year', getattr(dto, 'start_year', 2024)),
                        TBuildingInfo.fiscal_year.in_(fiscal_years),
                        TBuildingInfo.building_id.in_(building_ids),
                    )
                    .all()
                )

                if not t_building_info_list:
                    return {
                        "kpi_energy_saving_rate": None,
                        "kpi_electrification_rate": None,
                        "kpi_energy_creation_rate": None,
                        "kpi_renewable_network_rate": None,
                    }
                # 平均値取得
                energy_saving_denominator = (
                    statistics.mean(
                        [
                            item.energy_saving_denominator
                            for item in t_building_info_list
                            if item.energy_saving_denominator is not None
                        ]
                    )
                    if any(
                        item.energy_saving_denominator is not None
                        for item in t_building_info_list
                    )
                    else None
                )

                energy_benchmark_indicator_avg = (
                    statistics.mean(
                        [
                            float(item.energy_benchmark_indicator)
                            for item in t_building_info_list
                            if item.energy_benchmark_indicator is not None
                        ]
                    )
                    if any(
                        float(item.energy_benchmark_indicator) is not None
                        for item in t_building_info_list
                    )
                    else None
                )

            # 各種エネルギー使用量計算
            # 電力コード定数の取得
            try:
                electric_power_code = constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
            except AttributeError:
                # デフォルトの電力エネルギーコード
                electric_power_code = "0200010001"  # 一般的な電力コード

            # 電力熱量換算値
            heat_consumption_total_electric_power = (
                float(
                    df[df["energy_code"] == electric_power_code][
                        "heat_converted_energy_usage"
                    ].sum()
                )
                if "heat_converted_energy_usage" in df.columns
                else 0.0
            )

            # 全エネルギー熱量換算値
            heat_consumption_total = (
                float(df["heat_converted_energy_usage"].sum())
                if "heat_converted_energy_usage" in df.columns
                else 0.0
            )

            # 創エネエネルギー消費量
            energy_consumption_self_electric_power = (
                float(
                    df[df["supplier_reg_no"] == "REENE"][
                        "energy_quantity_for_law"
                    ].sum()
                )
                if "energy_quantity_for_law" in df.columns
                else 0.0
            )

            # 全電力エネルギー消費量
            energy_consumption_total_electric_power = (
                float(
                    df[df["energy_code"].str.startswith("02")][
                        "energy_quantity_for_law"
                    ].sum()
                )
                if "energy_quantity_for_law" in df.columns
                else 0.0
            )

            # 証書・クレジット購入量
            credit_certificate_purchase_tco2_total = (
                float(df["CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT"].sum())
                if "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT" in df.columns
                else 0.0
            )

            # 電力CO2換算値
            co2_total_electric_power = (
                float(
                    df[df["energy_code"] == electric_power_code][
                        "co2_adjusted_emissions"
                    ].sum()
                )
                if "co2_adjusted_emissions" in df.columns
                else 0.0
            )

            # 電力平均CO2換算値
            co2_total_electric_power_avg = (
                float(
                    df[
                        (df["energy_code"] == electric_power_code)
                        & (df["supplier_reg_no"] != "REENE")
                    ]["co2_adjusted_emissions_avg"].sum()
                )
                if "co2_adjusted_emissions_avg" in df.columns
                else 0.0
            )

            # KPI計算
            # 省エネ率実績割合
            kpi_energy_saving_rate = 0
            # val = getattr(cnapp_info_list[0], 'energy_saving_denominator', None)
            if (
                energy_saving_denominator is not None
                and energy_benchmark_indicator_avg is not None
                and energy_saving_denominator > 0
            ):
                kpi_energy_saving_rate = float(
                    float(energy_saving_denominator)
                    - energy_benchmark_indicator_avg / float(energy_saving_denominator)
                )
            else:
                kpi_energy_saving_rate = 0

            # 電化率実績割合
            kpi_electrification_rate = 0
            if heat_consumption_total > 0:
                kpi_electrification_rate = float(
                    heat_consumption_total_electric_power / heat_consumption_total
                )

            # 創エネ率実績割合
            kpi_energy_creation_rate = 0
            if energy_consumption_total_electric_power > 0:
                kpi_energy_creation_rate = float(
                    energy_consumption_self_electric_power
                    / energy_consumption_total_electric_power
                )
            else:
                kpi_energy_creation_rate = 0

            # CN外部調達
            kpi_renewable_network_rate = 0
            renewable_rate = co2_total_electric_power_avg - co2_total_electric_power
            if renewable_rate < 0:
                renewable_rate = 0.0
            if co2_total_electric_power_avg > 0:
                kpi_renewable_network_rate = float(
                    (renewable_rate + credit_certificate_purchase_tco2_total)
                    / co2_total_electric_power_avg
                )

            # レーダー図不具合対応のため処理
            values = [
                kpi_energy_saving_rate,
                kpi_electrification_rate,
                kpi_energy_creation_rate,
                kpi_renewable_network_rate,
            ]

            # 0（0.0含み）の位置確定
            zero_indices = [i for i, v in enumerate(values) if v == 0]

            # 唯一1の場合のみNoneにする
            if len(zero_indices) == 1:
                values[zero_indices[0]] = None

            (
                kpi_energy_saving_rate,
                kpi_electrification_rate,
                kpi_energy_creation_rate,
                kpi_renewable_network_rate,
            ) = values

            return {
                "kpi_energy_saving_rate": kpi_energy_saving_rate,
                "kpi_electrification_rate": kpi_electrification_rate,
                "kpi_energy_creation_rate": kpi_energy_creation_rate,
                "kpi_renewable_network_rate": kpi_renewable_network_rate,
            }

        except Exception as e:
            self.log.warning(f"追加KPI計算でエラーが発生しました: {e}")
            raise e

    def generate_csv_report(self, request_dict: Dict[str, Any], logger=None) -> str:
        """
        KPI一覧レポート（CSV）生成処理
        単拠点の場合は対象拠点のみ、グループ・企業全体の場合は全拠点を対象
        """
        if logger is None:
            logger = current_app.logger
        self.log = logger  # _calculate_additional_kpi_valuesで使用するためloggerを設定
        logger.info("KPI一覧レポート生成処理開始")

        # --- リクエストパラメータ取得 ---
        corporate_number = request_dict["corporate_number"]
        agreement_category = request_dict["agreement_category"]
        org_id = request_dict["org_id"]
        building_id_filter = request_dict.get(
            "building_id", None
        )  # 単拠点指定（ALLの場合は全体）

        # --- DBセッション取得 ---
        session: scoped_session = db.session
        engine = session.get_bind()

        # --- 建物マスタ情報取得SQL生成 ---
        building_stmt = select(
            MBuilding.building_id,
            MBuilding.location_identifier_code.label("拠点識別番号"),
            MBuilding.location_identifier_name.label("拠点識別名"),
            MBuilding.gross_floor_area.label("延床面積"),
            MBuilding.energy_benchmark_indicator.label("ベンチマーク指標"),
        ).where(
            and_(
                MBuilding.corporate_number == corporate_number,
                MBuilding.agreement_category == agreement_category,
                MBuilding.org_id == org_id,
            )
        )

        # --- 単拠点指定時は絞り込み ---
        if building_id_filter and building_id_filter != "0":
            building_stmt = building_stmt.where(
                MBuilding.building_id == building_id_filter
            )

        # --- SQL実行 ---
        df_building = pd.read_sql(building_stmt, engine)

        results = []

        # --- 各建物ごとにKPI計算 ---
        for _, row in df_building.iterrows():
            building_id = row["building_id"]
            floor_area = row["延床面積"]

            # --- 月別建物エネルギー集計情報 ---
            energy_stmt = select(
                # CO2調整後排出量（tｰCO2）
                func.sum(
                    TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions
                ).label("co2_sum"),
                # 証書・クレジット購入量（tｰCO2）
                func.sum(
                    TMonthlyBuildingEnergyAggregation.credit_certificate_purchase_tco2_amount
                ).label("credit_sum"),
                # 熱量換算エネルギー使用量
                func.sum(
                    TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage
                ).label("heat_energy_total"),
                func.max(
                    TMonthlyBuildingEnergyAggregation.heat_converted_energy_unit
                ).label("heat_energy_unit"),
                func.sum(
                    case(
                        (
                            TMonthlyBuildingEnergyAggregation.energy_category_name
                            == "電気",
                            TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage,
                        ),
                        else_=0,
                    )
                ).label("heat_energy_electric"),
            ).where(
                and_(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.building_id == building_id,
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
            )
            e = session.execute(energy_stmt).first()

            # --- KPI計算（None対策付き）---
            co2_sum = float(e.co2_sum) if e.co2_sum is not None else 0.0
            credit_sum = float(e.credit_sum) if e.credit_sum is not None else 0.0
            heat_energy_total = (
                float(e.heat_energy_total) if e.heat_energy_total is not None else 0.0
            )
            heat_energy_unit = (
                e.heat_energy_unit if hasattr(e, "heat_energy_unit") else None
            )
            heat_energy_electric = (
                float(e.heat_energy_electric)
                if e.heat_energy_electric is not None
                else 0.0
            )
            floor_area_val = float(floor_area) if floor_area is not None else 0.0

            # CO2排出原単位 (t-CO2/㎡)
            co2_unit = (
                max((co2_sum - credit_sum) / floor_area_val, 0)
                if floor_area_val > 0
                else None
            )
            # 一次エネルギー(MJ)
            primary_energy = (
                heat_energy_total * 1000
                if (heat_energy_unit and str(heat_energy_unit).upper() == "GJ")
                else heat_energy_total
            )
            # 省エネ率（ベンチマーク指標 ÷ 100, 値が無ければNone）
            try:
                benchmark_value = (
                    float(row["ベンチマーク指標"])
                    if row["ベンチマーク指標"] not in (None, "")
                    else None
                )
            except ValueError:
                benchmark_value = None
            energy_saving_rate = (
                (benchmark_value / 100.0) if benchmark_value is not None else None
            )

            # KPI値を_calculate_additional_kpi_valuesメソッドから取得
            # 建物ごとのエネルギーデータ取得用SQL
            building_energy_stmt = select(
                TMonthlyBuildingEnergyAggregation.energy_code,
                TMonthlyBuildingEnergyAggregation.fiscal_year,
                TMonthlyBuildingEnergyAggregation.registration_seq,
                TMonthlyBuildingEnergyAggregation.building_id,
                TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage,
                TMonthlyBuildingEnergyAggregation.energy_quantity_for_law,
                TMonthlyBuildingEnergyAggregation.supplier_reg_no,
                TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions,
                TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_avg,
                TMonthlyBuildingEnergyAggregation.credit_certificate_purchase_tco2_amount.label(
                    "CREDIT_CERTIFICATE_PURCHASE_TCO2_AMOUNT"
                ),
            ).where(
                and_(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.building_id == building_id,
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
            )

            # DataFrameを作成
            building_energy_df = pd.read_sql(building_energy_stmt, engine)

            # DTO作成（_calculate_additional_kpi_valuesで必要な属性を持つ）
            class KpiCalcDto:
                def __init__(self, corporate_number, agreement_category, org_id):
                    self.corporate_number = corporate_number
                    self.agreement_category = agreement_category
                    self.org_id = org_id

            kpi_dto = KpiCalcDto(corporate_number, agreement_category, org_id)

            # _calculate_additional_kpi_valuesを呼び出してKPI値を取得
            # 元のコードでは以下の4つの値がダミーまたは簡易計算だったため、これらを置き換える
            try:
                if not building_energy_df.empty:
                    kpi_values = self._calculate_additional_kpi_values(
                        session, building_energy_df, kpi_dto
                    )
                    # 元の335-338行の4つの値を置き換え
                    energy_saving_rate = kpi_values.get(
                        "kpi_energy_saving_rate"
                    )  # 元の計算値を上書き
                    electrification_rate = kpi_values.get("kpi_electrification_rate")
                    energy_creation_rate = kpi_values.get("kpi_energy_creation_rate")
                    network_rate = kpi_values.get("kpi_renewable_network_rate")
                else:
                    # DataFrameが空の場合は従来の計算を使用
                    electrification_rate = (
                        (heat_energy_electric / heat_energy_total)
                        if heat_energy_total
                        else None
                    )
                    energy_creation_rate = None
                    network_rate = None
            except Exception as e:
                logger.warning(
                    f"KPI計算でエラーが発生しました (building_id={building_id}): {e}"
                )
                # エラー時は従来の計算を使用
                electrification_rate = (
                    (heat_energy_electric / heat_energy_total)
                    if heat_energy_total
                    else None
                )
                energy_creation_rate = None
                network_rate = None

            results.append(
                {
                    "拠点識別番号": row["拠点識別番号"],
                    "拠点識別名": row["拠点識別名"],
                    "延床面積（㎡）": floor_area,
                    "CO2排出原単位（t-CO2/㎡）": co2_unit,
                    "一次エネルギー(MJ)": primary_energy,
                    "省エネ率": energy_saving_rate,
                    "電化率": electrification_rate,
                    "創エネ率": energy_creation_rate,
                    "ﾈｯﾄﾜｰｸ率": network_rate,
                }
            )

        # --- DataFrame生成 ---
        df = pd.DataFrame(results)

        # === 変更点: 空データ対応と列存在チェックを追加 ===
        if df.empty:
            logger.warning(
                "KPI一覧レポートに出力するデータがありません。空ファイルを出力します。"
            )
        else:
            # 数値フォーマット関数
            def fmt_percent(x):
                return f"{x:.0%}" if pd.notnull(x) else ""

            def fmt_num(x):
                return f"{x:,.0f}" if pd.notnull(x) else ""

            # 列存在チェック付きフォーマット
            if "延床面積（㎡）" in df.columns:
                df["延床面積（㎡）"] = df["延床面積（㎡）"].apply(fmt_num)
            if "一次エネルギー(MJ)" in df.columns:
                df["一次エネルギー(MJ)"] = df["一次エネルギー(MJ)"].apply(fmt_num)
            for col in ["省エネ率", "電化率", "創エネ率", "ﾈｯﾄﾜｰｸ率"]:
                if col in df.columns:
                    df[col] = df[col].apply(fmt_percent)

        # --- CSV出力 ---
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        filename = f"kpi_report_{now_local.strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = os.path.join(self.OUTPUT_DIR, filename)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(f"KPI一覧レポートを出力しました: {output_path}")
        return output_path
