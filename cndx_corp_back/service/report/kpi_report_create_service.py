# cndx_corp_back/service/report/kpi_report_create_service.py
# -*- coding: utf-8 -*-
"""
KPI一覧レポート生成（CSV）サービス
- これ一つで「入力チェック」→「DBアクセス」→「KPI集計」→「CSV出力」までを完結
- 呼び出し側は本サービスの execute(...) を呼ぶだけでOK
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pandas as pd
from flask import current_app
from sqlalchemy import case, func, literal

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)


class KpiReportCreateService:
    """
    KPI一覧レポート生成サービスクラス（CSV版・単体）
    - 旧: Service（execute） + Logic（generate_csv_report）を統合
    """

    # @log_time
    def execute(
        self,
        df_building,
        request_dict: Dict[str, Any],
        message_list: list,
        logger=None,
    ) -> Dict[str, str]:
        """
        KPIレポートのCSVを生成してパスを返す（DBへの登録は呼び出し元で実施）

        Args:
            request_dict (dict): リクエストボディ（creation_id / building_id 等を含む）
            message_list (list): エラーメッセージ格納用のリスト（呼び出し元で用意）
            logger: ロガー（省略時は current_app.logger）

        Returns:
            dict: {"kpi_report_path": 保存先パス} もしくは {"error": "必須パラメータ不足", "details": [...]} を返す
        """
        if logger is None:
            logger = current_app.logger

        # ----------- 必須パラメータチェック -----------
        required_keys = [
            "creation_id",
            "building_id",  # "ALL" / "GROUP" / 実拠点ID
            "corporate_number",
            "agreement_category",
            "org_id",
            "start_year",
            "start_month",
            "creation_format",
        ]
        for key in required_keys:
            if key not in request_dict or not request_dict[key]:
                message_list.append(f"必須パラメータが不足しています：{key}")

        if message_list:
            logger.error(f"KPI Service: 必須パラメータ不足: {message_list}")
            return {"error": "必須パラメータ不足", "details": message_list}

        # ----------- CSV生成本体 -----------
        filename, csv_bytes = self._generate_csv_report(
            df_building, request_dict=request_dict, logger=logger
        )

        return filename, csv_bytes

    # ===================== 内部処理（旧 Logic 部分） =====================

    # @log_time
    def _generate_csv_report(
        self, df_building, request_dict: Dict[str, Any], logger=None
    ) -> str:
        """
        KPI一覧レポート（CSV）生成処理
        - 単拠点：対象拠点のみ
        - グループ：group_items(= group1..5 条件) に一致する全拠点
        - 企業全体：全拠点
        """
        if logger is None:
            logger = current_app.logger
        logger.info("KPI一覧レポート生成処理開始")

        # --- リクエストパラメータ取得 ---
        corporate_number = request_dict["corporate_number"]
        agreement_category = request_dict["agreement_category"]
        org_id = request_dict["org_id"]
        # building_id_filter = request_dict.get("building_id", None)  # "ALL" / 仮想ID / 実ID / "GROUP"
        # group_items = request_dict.get("group_items") or []          # ★ 追加：グループ条件
        start_ym = request_dict["start_year"] + request_dict["start_month"]
        end_ym = request_dict["end_year"] + request_dict["end_month"]

        results = []

        # --- 各建物ごとにKPI計算 ---
        # list化にする
        building_ids = df_building["building_id"].dropna().tolist()
        with get_scoped_session() as session:
            # user = session.query(MUser).filter(
            #     MUser.user_id == user_id,
            #     MUser.delete_flg.isnot(True)
            # ).first()
            energy_stmt = (
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
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.credit_certificate_purchase_tco2_amount
                    ).label("credit_sum"),
                    # heat_converted_energy_usage を行ごとに MJ に換算してから合計
                    func.sum(
                        case(
                            (
                                func.upper(
                                    TMonthlyBuildingEnergyAggregation.heat_converted_energy_unit
                                )
                                == "GJ",
                                TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage
                                * 1000,
                            ),
                            else_=TMonthlyBuildingEnergyAggregation.heat_converted_energy_usage,
                        )
                    ).label("heat_energy_total"),
                    # すべて MJ ベースにしているため、単位は固定で MJ
                    literal("MJ").label("heat_energy_unit"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.energy_quantity_for_law
                    ).label("energy_quantity_law"),
                    func.sum(
                        TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions_avg
                    ).label("co2_sum_avg"),
                    # func.round(
                    #     func.sum(TMonthlyBuildingEnergyAggregation.co2_adjusted_emissions) /
                    #     func.avg(TMonthlyBuildingEnergyAggregation.gross_floor_area),
                    #     2
                    # ).label("co2_sum_unit")
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

        df_energy = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in energy_stmt
            ]
        )

        # --- 建物ごとの平均面積（area_avg）を別途算出 ---
        with get_scoped_session() as session:
            area_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    (
                        func.floor(
                            func.avg(TMonthlyBuildingEnergyAggregation.gross_floor_area)
                            * 100
                        )
                        / 100
                    ).label("area_avg"),
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
                    TMonthlyBuildingEnergyAggregation.building_id,
                )
                .all()
            )

        df_area = (
            pd.DataFrame(
                [
                    {field: getattr(row, field) for field in row._fields}
                    for row in area_stmt
                ]
            )
            if area_stmt
            else pd.DataFrame(columns=["building_id", "area_avg"])
        )

        # df_energy に building_id 単位の平均面積を付与
        if not df_energy.empty and not df_area.empty:
            df_energy = df_energy.merge(df_area, on="building_id", how="left")

        if df_energy.empty:
            logger.warning(
                "KPI一覧レポートデータが存在しません。CSV出力をスキップします。"
            )
            df = pd.DataFrame(
                columns=[
                    "拠点識別番号",
                    "拠点識別名",
                    "平均面積",
                    "CO2排出原単位（t-CO2/㎡）",
                    "一次エネルギー(MJ)",
                    "省エネ率",
                    "電化率",
                    "創エネ率",
                    "ﾈｯﾄﾜｰｸ率",
                ]
            )
        else:
            # 判定フラグを取得（df_buildingに含まれる想定）
            judgeFlag = (
                str(df_building["判定フラグ"].iloc[0])
                if "判定フラグ" in df_building.columns and not df_building.empty
                else "0"
            )

            # logger.info(f"[DEBUG] df_building shape: {df_building.shape}")
            # logger.info(f"[DEBUG] df_building building_ids: {df_building['building_id'].unique().tolist() if 'building_id' in df_building.columns else 'NO building_id column'}")

            df_merged = df_energy.merge(
                df_building,
                on="building_id",
                how="inner",
                suffixes=("", "_right"),  # df_energy 側はそのまま
            )

            # logger.info(f"[DEBUG] df_merged shape after merge: {df_merged.shape}")
            # if not df_merged.empty:
            # logger.info(f"[DEBUG] df_merged columns: {df_merged.columns.tolist()}")
            # logger.info(f"[DEBUG] df_merged building_ids: {df_merged['building_id'].unique().tolist()}")

            df_merged = calculate_additional_kpi_values(
                None, df_merged, judgeFlag, logger
            )

            logger.info(
                f"[DEBUG] df_merged shape after calculate_additional_kpi_values: {df_merged.shape}"
            )

            for idx, row in df_merged.iterrows():
                # co2_sum_unit を計算: co2_sum / area_avg（小数点3桁、math.floor使用）
                co2_sum = float(row.get("co2_sum") or 0)
                area_avg = float(row.get("area_avg") or 0)
                co2_sum_unit = (
                    math.floor((co2_sum / area_avg) * 1000) / 1000
                    if area_avg > 0
                    else 0
                )

                # デバッグ: KPI値の確認
                logger.info(f"[DEBUG KPI値] 拠点: {row.get('拠点識別名', 'N/A')}")
                logger.info(f"  KPI省エネ率(raw): {row.get('KPI省エネ率', 'N/A')}")
                logger.info(f"  KPI電化率(raw): {row.get('KPI電化率', 'N/A')}")
                logger.info(f"  KPI創エネ率(raw): {row.get('KPI創エネ率', 'N/A')}")
                logger.info(f"  KPICN率(raw): {row.get('KPICN率', 'N/A')}")

                # KPI値を百分比に変換（×100、四捨五入して整数、%付き）
                def to_percentage(value):
                    try:
                        return f"{float(value) * 100:.0f}%"
                    except (ValueError, TypeError):
                        return "0%"

                results.append(
                    {
                        "拠点識別番号": row["拠点識別番号"],
                        "拠点識別名": row["拠点識別名"],
                        # "延床面積（㎡）": row["延床面積"],
                        # 整数を取るように変更
                        "平均面積": int(float(row.get("area_avg", 0))),
                        "CO2排出原単位（t-CO2/㎡）": co2_sum_unit,
                        "一次エネルギー(MJ)": (
                            int(float(row["heat_energy_total"] or 0) * 1000)
                            if str(row.get("heat_energy_unit", "")).upper() == "GJ"
                            else int(float(row["heat_energy_total"] or 0))
                        ),
                        "省エネ率": to_percentage(row["KPI省エネ率"]),
                        "電化率": to_percentage(row["KPI電化率"]),
                        "創エネ率": to_percentage(row["KPI創エネ率"]),
                        "ﾈｯﾄﾜｰｸ率": to_percentage(row["KPICN率"]),
                    }
                )

            # --- DataFrame 生成 ---
            df = pd.DataFrame(results)

            # --- 空データ対応＆列存在チェック ---
            if df.empty:
                logger.warning(
                    "KPI一覧レポートに出力するデータがありません。空ファイルを出力します。"
                )
            else:
                # CSV出力用にフォーマット（数値を文字列に変換）
                if "平均面積" in df.columns:
                    df["平均面積"] = df["平均面積"].apply(
                        lambda x: str(int(x)) if pd.notnull(x) else ""
                    )
                # 3桁小数を取るように変える
                if "CO2排出原単位（t-CO2/㎡）" in df.columns:
                    df["CO2排出原単位（t-CO2/㎡）"] = df[
                        "CO2排出原単位（t-CO2/㎡）"
                    ].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "")

                if "一次エネルギー(MJ)" in df.columns:
                    df["一次エネルギー(MJ)"] = df["一次エネルギー(MJ)"].apply(
                        lambda x: str(int(x)) if pd.notnull(x) else ""
                    )

        # --- CSV出力 ---
        utc_time = datetime.now(timezone.utc)
        # tokyoの時間に替える
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        # csvの互換性を高めるための処理
        filename = f"kpi_report_{now_local.strftime('%Y%m%d_%H%M%S')}.csv"
        # 行インデックスをエクスポートしないようにする
        csv_str = df.to_csv(index=False, lineterminator="\r\n")
        csv_bytes = csv_str.encode("utf-8-sig")

        return filename, csv_bytes


# @log_time
def calculate_additional_kpi_values(
    session, df: pd.DataFrame, judgeFlag, logger=None
) -> dict:
    """追加KPI計算のための拠点別指標を生成する"""
    try:
        from cndx_corp_back.common import constants_values
        from cndx_corp_back.entity.t_cn_application_info_entity import (  # noqa: F401 (保持: 互換性)
            TCnApplicationInfo,
        )

        building_ids = df["building_id"].dropna().unique().tolist()
        if not building_ids:
            for col in ["KPI省エネ率", "KPI電化率", "KPI創エネ率", "KPICN率"]:
                df[col] = None
            return {
                "kpi_energy_saving_rate": {},
                "kpi_electrification_rate": {},
                "kpi_energy_creation_rate": {},
                "kpi_renewable_network_rate": {},
            }

        building_index = pd.Index(building_ids, name="building_id")
        zero_series = pd.Series(0.0, index=building_index, dtype=float)

        if logger:
            logger.info(f"[DEBUG KPI] Input df shape: {df.shape}")
            logger.info(f"[DEBUG KPI] building_ids: {building_ids}")

        def blank_series():
            return zero_series.copy()

        def ensure_series(series: pd.Series) -> pd.Series:
            if not isinstance(series, pd.Series) or series.empty:
                return blank_series()
            numeric_series = pd.to_numeric(series, errors="coerce").fillna(0.0)
            return numeric_series.reindex(building_index, fill_value=0.0)

        def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
            denominator = denominator.mask(denominator == 0)
            return numerator.div(denominator).fillna(0.0)

        numeric_columns = [
            "heat_energy_total",
            "energy_quantity_law",
            "credit_sum",
            "co2_sum",
            "co2_sum_avg",
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        if "energy_code" in df.columns:
            df["energy_code"] = df["energy_code"].fillna("").astype(str)
        else:
            df["energy_code"] = ""

        if "supplier_reg_no" in df.columns:
            df["supplier_reg_no"] = df["supplier_reg_no"].fillna("").astype(str)
        else:
            df["supplier_reg_no"] = ""

        # 証書・クレジット購入量(A) 集計対象となるエネルギーコード
        codes = [
            "9900010002",
            "9900010003",
            "9900010004",
            "9900010001",
            "9900010006",
            "9900010013",
            "9900011013",
            "9900011002",
            "9900011003",
            "9900011004",
            "9900011007",
            "9900011005",
            "9900011001",
        ]

        try:
            electric_power_code = constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
        except AttributeError:
            electric_power_code = "0200010001"

        heat_consumption_total_electric_power_by_building = ensure_series(
            df[df["energy_code"] == electric_power_code]
            .groupby("building_id")["heat_energy_total"]
            .sum()
        )

        heat_consumption_total_by_building = ensure_series(
            df.groupby("building_id")["heat_energy_total"].sum()
        )
        if "energy_quantity_law" in df.columns:
            # 創エネの分子
            energy_consumption_self_electric_power_by_building = ensure_series(
                df[df["supplier_reg_no"] == "REENE"]
                .groupby("building_id")["energy_quantity_law"]
                .sum()
            )
            # 創エネの分母
            energy_consumption_total_electric_power_by_building = ensure_series(
                df[df["energy_code"].str.startswith("02", na=False)]
                .groupby("building_id")["energy_quantity_law"]
                .sum()
            )
        else:
            energy_consumption_self_electric_power_by_building = blank_series()
            energy_consumption_total_electric_power_by_building = blank_series()

        # A: 証書・クレジット購入量（t-CO2）
        #   = 直近1年間(0-1)の証書・クレジット購入量（tｰCO2）の合計値
        #   ※ 集計対象は指定のエネルギーコード(codes)に準じる
        if "credit_sum" in df.columns and "energy_code" in df.columns:
            credit_certificate_purchase_tco2_total_by_building = ensure_series(
                df[df["energy_code"].isin(codes)]
                .groupby("building_id")["credit_sum"]
                .sum()
            )
        else:
            credit_certificate_purchase_tco2_total_by_building = blank_series()

        if "co2_sum" in df.columns:
            # B：購入先の係数で算定したCO2排出量（電気・買電量）
            #    energy_code == electric_power_code かつ
            #    供給事業者登録番号が REENE / SCOPE1 以外（= 買電量）
            co2_total_electric_power_by_building = ensure_series(
                df[
                    (df["energy_code"] == electric_power_code)
                    & (~df["supplier_reg_no"].isin(["REENE", "SCOPE1"]))
                ]
                .groupby("building_id")["co2_sum"]
                .sum()
            )
        else:
            co2_total_electric_power_by_building = blank_series()

        if "co2_sum_avg" in df.columns:
            # C：全国平均係数で算定したCO2排出量（電気・買電量）
            #    energy_code == electric_power_code かつ
            #    供給事業者登録番号が REENE / SCOPE1 以外（= 買電量）
            co2_total_electric_power_avg_by_building = ensure_series(
                df[
                    (df["energy_code"] == electric_power_code)
                    & (~df["supplier_reg_no"].isin(["REENE", "SCOPE1"]))
                ]
                .groupby("building_id")["co2_sum_avg"]
                .sum()
            )
        else:
            co2_total_electric_power_avg_by_building = blank_series()

        # 省エネ率の計算（列が存在する場合のみ）
        if "省エネ法ベンチマーク指標" in df.columns and "省エネ率分母" in df.columns:
            df["省エネ法ベンチマーク指標"] = pd.to_numeric(
                df["省エネ法ベンチマーク指標"], errors="coerce"
            )
            df["省エネ率分母"] = pd.to_numeric(df["省エネ率分母"], errors="coerce")
            kpi_energy_saving_rate_series = df.groupby("building_id").apply(
                lambda g: (
                    g["省エネ法ベンチマーク指標"].sum() / g["省エネ率分母"].sum()
                    if g["省エネ率分母"].sum() > 0
                    else 0.0
                )
            )
        else:
            # 列が存在しない場合は0で初期化
            kpi_energy_saving_rate_series = blank_series()

        # if energy_saving_denominator is not None and energy_saving_denominator > 0:
        #     kpi_energy_saving_rate_series = pd.Series(
        #         float((energy_benchmark_indicator_avg or 0) /  float(energy_saving_denominator)),
        #         index=building_index,
        #         dtype=float,
        #     )
        # else:
        #     kpi_energy_saving_rate_series = blank_series()

        # TBuildingInfo から省エネ率分母とベンチマーク指標の平均値を取得し、新仕様の省エネ率で上書きする
        try:
            import statistics

            from cndx_corp_back.common.database_manager import (
                get_scoped_session as _session_scope_for_kpi,
            )
            from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo

            fiscal_years = (
                df["fiscal_year"].dropna().unique().tolist()
                if "fiscal_year" in df.columns
                else []
            )
            corporate_number = (
                df["corporate_number"].iloc[0]
                if "corporate_number" in df.columns
                else None
            )
            agreement_category = (
                df["agreement_category"].iloc[0]
                if "agreement_category" in df.columns
                else None
            )
            org_id = df["org_id"].iloc[0] if "org_id" in df.columns else None

            energy_saving_denominator = None
            energy_benchmark_indicator_avg = None

            if corporate_number and agreement_category and org_id and fiscal_years:
                with _session_scope_for_kpi() as s:
                    t_building_info_list = (
                        s.query(TBuildingInfo)
                        .filter(
                            TBuildingInfo.corporate_number == corporate_number,
                            TBuildingInfo.agreement_category == agreement_category,
                            TBuildingInfo.org_id == org_id,
                            TBuildingInfo.registration_seq == 0,
                            TBuildingInfo.fiscal_year.in_(fiscal_years),
                            TBuildingInfo.building_id.in_(building_ids),
                        )
                        .all()
                    )

                if t_building_info_list:
                    if any(
                        item.energy_saving_denominator is not None
                        for item in t_building_info_list
                    ):
                        energy_saving_denominator = statistics.mean(
                            [
                                item.energy_saving_denominator
                                for item in t_building_info_list
                                if item.energy_saving_denominator is not None
                            ]
                        )

                    if any(
                        item.energy_benchmark_indicator is not None
                        for item in t_building_info_list
                    ):
                        energy_benchmark_indicator_avg = statistics.mean(
                            [
                                float(item.energy_benchmark_indicator)
                                for item in t_building_info_list
                                if item.energy_benchmark_indicator is not None
                            ]
                        )

            if (
                energy_saving_denominator is not None
                and energy_saving_denominator > 0
                and energy_benchmark_indicator_avg is not None
            ):
                # グループ別：（省エネ率分母 − 省エネ法ベンチマーク指標平均値） ÷ 省エネ率分母
                denom_value = float(energy_saving_denominator)
                # 正しい式: (分母 - 指標) / 分母
                group_rate = float(
                    (denom_value - energy_benchmark_indicator_avg) / denom_value
                )
            else:
                group_rate = 0.0

            # グループで算出した省エネ率を拠点ごとに横展開
            kpi_energy_saving_rate_series = pd.Series(
                group_rate,
                index=building_index,
                dtype=float,
            )
        except Exception:
            # 取得や計算で問題があった場合は既存ロジックの結果をそのまま利用
            pass

        # 新仕様: building_id ごとに TBuildingInfo から省エネ率を再計算して上書き
        try:
            import statistics as _statistics_for_kpi

            from cndx_corp_back.common.database_manager import (
                get_scoped_session as _session_scope_for_kpi_per_building,
            )
            from cndx_corp_back.entity.t_building_info_entity import (
                TBuildingInfo as _TBuildingInfoForKpi,
            )

            fiscal_years = (
                df["fiscal_year"].dropna().unique().tolist()
                if "fiscal_year" in df.columns
                else []
            )
            corporate_number = (
                df["corporate_number"].iloc[0]
                if "corporate_number" in df.columns
                else None
            )
            agreement_category = (
                df["agreement_category"].iloc[0]
                if "agreement_category" in df.columns
                else None
            )
            org_id = df["org_id"].iloc[0] if "org_id" in df.columns else None

            building_rate_map = {}

            if corporate_number and agreement_category and org_id and fiscal_years:
                with _session_scope_for_kpi_per_building() as s:
                    t_building_info_list = (
                        s.query(_TBuildingInfoForKpi)
                        .filter(
                            _TBuildingInfoForKpi.corporate_number == corporate_number,
                            _TBuildingInfoForKpi.agreement_category
                            == agreement_category,
                            _TBuildingInfoForKpi.org_id == org_id,
                            _TBuildingInfoForKpi.registration_seq == 0,
                            _TBuildingInfoForKpi.fiscal_year.in_(fiscal_years),
                            _TBuildingInfoForKpi.building_id.in_(building_ids),
                        )
                        .all()
                    )

                if t_building_info_list:
                    for building_id in building_ids:
                        related_items = [
                            item
                            for item in t_building_info_list
                            if item.building_id == building_id
                        ]
                        if not related_items:
                            continue

                        denom_values = [
                            float(item.energy_saving_denominator)
                            for item in related_items
                            if item.energy_saving_denominator is not None
                        ]
                        indicator_values = [
                            float(item.energy_benchmark_indicator)
                            for item in related_items
                            if item.energy_benchmark_indicator is not None
                        ]

                        if not denom_values or not indicator_values:
                            continue

                        denom_avg = _statistics_for_kpi.mean(denom_values)
                        indicator_avg = _statistics_for_kpi.mean(indicator_values)

                        if denom_avg and denom_avg > 0:
                            denom_value = float(denom_avg)
                            building_rate_map[building_id] = float(
                                (denom_value - indicator_avg) / denom_value
                            )

            if building_rate_map:
                override_series = pd.Series(building_rate_map, dtype=float)
                override_series = override_series.reindex(building_index)
                kpi_energy_saving_rate_series = kpi_energy_saving_rate_series.where(
                    override_series.isna(), override_series
                )
        except Exception:
            # ここでの失敗時も、直前までに算出済みの値をそのまま利用する
            pass

        kpi_electrification_rate_series = safe_ratio(
            heat_consumption_total_electric_power_by_building,
            heat_consumption_total_by_building,
        )

        kpi_energy_creation_rate_series = safe_ratio(
            energy_consumption_self_electric_power_by_building,
            energy_consumption_total_electric_power_by_building,
        )

        renewable_rate = (
            co2_total_electric_power_avg_by_building
            - co2_total_electric_power_by_building
        ).clip(lower=0.0)

        kpi_renewable_network_rate_series = safe_ratio(
            renewable_rate + credit_certificate_purchase_tco2_total_by_building,
            co2_total_electric_power_avg_by_building,
        )
        # KPI列を事前にdfに追加（groupby前に）
        df["KPI省エネ率"] = (
            df["building_id"].map(kpi_energy_saving_rate_series).fillna(0.0)
        )
        df["KPI電化率"] = (
            df["building_id"].map(kpi_electrification_rate_series).fillna(0.0)
        )
        df["KPI創エネ率"] = (
            df["building_id"].map(kpi_energy_creation_rate_series).fillna(0.0)
        )
        df["KPICN率"] = (
            df["building_id"].map(kpi_renewable_network_rate_series).fillna(0.0)
        )

        # 除外カラム名(集計対象の数値列とグループ化に不要な列)
        exclude_cols = [
            "energy_code",
            "supplier_reg_no",
            "fiscal_year",
            "energy_quantity_law",
            "co2_sum_avg",
        ]
        df["heat_energy_total"] = df["heat_energy_total"].astype(float)
        df["co2_sum"] = df["co2_sum"].astype(float)
        df["credit_sum"] = df["credit_sum"].astype(float)

        # 拠点単位でグループ化するため、building_idと拠点情報のみを使用
        # 数値列(co2_sum, credit_sum, heat_energy_total)は合計し、
        # その他の列(面積、グループ、拠点名など)は最初の値を使う

        group_key = "building_id"
        numeric_agg_cols = ["co2_sum", "credit_sum", "heat_energy_total"]

        # 拠点ごとの不変情報列(グループ化後に保持したい列)
        preserve_cols = [
            col
            for col in df.columns
            if col not in exclude_cols + numeric_agg_cols + [group_key]
        ]

        if logger:
            logger.info(f"[DEBUG KPI] group_key: {group_key}")
            logger.info(f"[DEBUG KPI] numeric_agg_cols: {numeric_agg_cols}")
            logger.info(f"[DEBUG KPI] preserve_cols count: {len(preserve_cols)}")
            logger.info(f"[DEBUG KPI] df shape before groupby: {df.shape}")

        # グループ化して数値列を合計、その他の列は最初の値を取得
        agg_dict = {col: "sum" for col in numeric_agg_cols}
        agg_dict.update({col: "first" for col in preserve_cols})

        df_grouped = df.groupby(group_key, as_index=False).agg(agg_dict)

        if logger:
            logger.info(
                f"[DEBUG KPI] df_grouped shape after groupby: {df_grouped.shape}"
            )
        return df_grouped

    except Exception as e:
        if logger is not None:
            logger.warning(f"追加KPI計算でエラーが発生しました: {e}")
        raise
