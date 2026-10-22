import os
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pandas as pd
from dateutil.relativedelta import relativedelta
from fpdf import FPDF as BaseFPDF
from sqlalchemy import and_, func, or_

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)


class EnergyKessonReportCreateLogic:

    # @log_time
    def generate_energy_kesson_pdf_report(
        self, df_building, request_dict: Dict[str, Any], logger
    ) -> str:

        corporate_number = request_dict["corporate_number"]
        agreement_category = request_dict["agreement_category"]
        org_id = request_dict["org_id"]

        start_ym = f"{int(request_dict['start_year']):04d}{int(request_dict['start_month']):02d}"
        end_ym = (
            f"{int(request_dict['end_year']):04d}{int(request_dict['end_month']):02d}"
        )

        start_date = datetime(
            int(request_dict["start_year"]), int(request_dict["start_month"]), 1
        )
        months = [
            (start_date + relativedelta(months=i)).strftime("%Y%m") for i in range(12)
        ]

        with get_scoped_session() as session:
            kessnon_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_category_name.label(
                        "エネルギー種別"
                    ),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        start_ym, end_ym
                    ),
                    # 論理削除されたデータを追加する
                    or_(
                        and_(
                            TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                            TMonthlyBuildingEnergyAggregation.energy_quantity == 0,
                        ),
                        TMonthlyBuildingEnergyAggregation.delete_flg.is_(True),
                    ),
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

            new_kessnon = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.building_id,
                    TMonthlyBuildingEnergyAggregation.energy_category_name.label(
                        "エネルギー種別"
                    ),
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        start_ym, end_ym
                    ),
                )
                .all()
            )

            # --- グループ ---
            groups = defaultdict(list)
            for r in new_kessnon:
                groups[(r.building_id, r.エネルギー種別)].append(r)

            # --- フィルタ条件：グループの件数が 0より大きく、12未満 ---
            filtered_groups = {
                key: group for key, group in groups.items() if 0 < len(group) < 12
            }

            filtered_rows = [r for group in filtered_groups.values() for r in group]

            # マージ
            kessnon_stmt = list(kessnon_stmt) + list(filtered_rows)

            # building_id と エネルギー種別 で重複を除外する
            unique_stmt = []
            seen = set()

            for row in kessnon_stmt:
                key = (row.building_id, getattr(row, "エネルギー種別", None))
                if key not in seen:
                    seen.add(key)
                    unique_stmt.append(row)

            energy_stmt = (
                session.query(
                    TMonthlyBuildingEnergyAggregation.energy_category_name.label(
                        "エネルギー種別"
                    ),
                    func.round(
                        TMonthlyBuildingEnergyAggregation.energy_quantity_for_law, 2
                    ).label("エネルギー使用量"),
                    TMonthlyBuildingEnergyAggregation.energy_unit_for_law.label("単位"),
                    TMonthlyBuildingEnergyAggregation.target_year_month.label("年月"),
                    TMonthlyBuildingEnergyAggregation.building_id,
                )
                .where(
                    TMonthlyBuildingEnergyAggregation.corporate_number
                    == corporate_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                    TMonthlyBuildingEnergyAggregation.target_year_month.between(
                        start_ym, end_ym
                    ),
                    TMonthlyBuildingEnergyAggregation.delete_flg.is_not(True),
                )
                .all()
            )

            cn_info = (
                session.query(TCnApplicationInfo)
                .filter_by(
                    corporate_number=corporate_number,
                    agreement_category=agreement_category,
                    org_id=org_id,
                )
                .first()
            )
            company_name = cn_info.company_name if cn_info else ""

        consent_route = request_dict["consent_route"]

        # 欠損拠点対象絞り
        df_kesson = pd.DataFrame(
            [
                {field: getattr(row, field) for field in row._fields}
                for row in unique_stmt
            ],
            dtype=str,
        )
        # 全エネルギー情報取得

        def fill_energy_stmt(energy_stmt, start_ym, end_ym):
            df = pd.DataFrame(
                [
                    {
                        "エネルギー種別": row.エネルギー種別,
                        "エネルギー使用量": row.エネルギー使用量,
                        "単位": row.単位,
                        "年月": row.年月,
                        "building_id": row.building_id,
                    }
                    for row in energy_stmt
                ]
            )

            # 完全な年月リストを生成する
            ym_list = []
            start = datetime.strptime(start_ym, "%Y%m")
            end = datetime.strptime(end_ym, "%Y%m")
            while start <= end:
                ym_list.append(start.strftime("%Y%m"))
                # 1か月を加算する
                if start.month == 12:
                    start = datetime(start.year + 1, 1, 1)
                else:
                    start = datetime(start.year, start.month + 1, 1)

            # building_id と エネルギー種別 ごとにグループ化して補完する
            filled_all = []
            for (b_id, cat), group in df.groupby(["building_id", "エネルギー種別"]):
                existing_months = set(group["年月"])
                unit = group.iloc[0]["単位"]  # 同じグループ内の単位は同一である
                for ym in ym_list:
                    if ym not in existing_months:
                        filled_all.append(
                            {
                                "エネルギー種別": cat,
                                "エネルギー使用量": Decimal("0.00"),
                                "単位": unit,
                                "年月": ym,
                                "building_id": b_id,
                            }
                        )
                # 元のデータを追加する
                filled_all.extend(group.to_dict("records"))

            return filled_all

        energy_stmt_filled = fill_energy_stmt(energy_stmt, start_ym, end_ym)

        # df_energy = pd.DataFrame([{field: getattr(row, field) for field in row._fields} for row in energy_stmt_filled])
        columns = ["エネルギー種別", "エネルギー使用量", "単位", "年月", "building_id"]
        df_energy = pd.DataFrame(energy_stmt_filled, columns=columns)

        if df_kesson.empty:
            logger.warning(
                "エネルギーデータ欠損レポートデータが存在しません。CSV出力をスキップします。"
            )
            df_merged = pd.DataFrame(
                columns=[
                    "同意書取得経路",
                    "企業名",
                    "拠点識別番号",
                    "拠点識別名",
                    "エネルギー種別",
                    "単位",
                    "エネルギー使用量",
                    "年月",
                ]
            )
            # return ""
        else:
            # 検索条件エネルギー情報絞り
            df_merged = df_energy.merge(
                df_building,
                on="building_id",
                how="inner",
                suffixes=("", "_right"),  # df_energy 側はそのまま
            )

            # 欠損エネルギー情報絞り
            df_merged = df_merged.merge(
                df_kesson,
                on=["building_id", "エネルギー種別"],
                how="inner",
                suffixes=("", "_right"),  # df_energy 側はそのまま
            )

        if df_merged.empty:
            logger.warning(
                "エネルギーデータ欠損レポートデータが存在しません。CSV出力をスキップします。"
            )
            # return ""

        df_merged["同意書取得経路"] = consent_route
        # df_merged["企業名"] = request_dict.get("company_name", "")
        df_merged["企業名"] = company_name

        # 値が空のエネルギー使用量を0に変更する
        df_pivot = (
            df_merged.pivot_table(
                index=[
                    "同意書取得経路",
                    "企業名",
                    "拠点識別番号",
                    "拠点識別名",
                    "エネルギー種別",
                    "単位",
                ],
                columns="年月",
                values="エネルギー使用量",
                aggfunc="sum",
            )
            .fillna(0)
            .reset_index()
        )

        # エネルギー使用量の部分の数値を「0.00」形式の文字列に変換する
        value_cols = df_pivot.columns.difference(
            [
                "同意書取得経路",
                "企業名",
                "拠点識別番号",
                "拠点識別名",
                "エネルギー種別",
                "単位",
            ]
        )
        df_pivot[value_cols] = df_pivot[value_cols].applymap(lambda x: f"{x:.2f}")

        for month in months:
            if month not in df_pivot.columns:
                df_pivot[month] = None

        month_columns = sorted([col for col in df_pivot.columns if col.isdigit()])
        renamed_months = {m: f"{m[:4]}年{int(m[4:]):d}月" for m in month_columns}
        df_pivot = df_pivot.rename(columns=renamed_months)

        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        font_path = os.path.join(BASE_DIR, "static", "fonts", "NotoSansJP-Regular.ttf")

        class FPDF(BaseFPDF):
            def header(self):
                self.set_font("NotoSansJP", "", 14)
                self.cell(0, 10, "欠損有エネルギーデータ一覧", ln=True, align="C")

        pdf = FPDF(orientation="L", unit="mm", format="A3")
        pdf.add_font("NotoSansJP", "", font_path, uni=True)
        pdf.set_font("NotoSansJP", size=8)
        pdf.add_page()

        col_names = list(df_pivot.columns)
        col_width = 400 / len(col_names)

        for col in col_names:
            pdf.cell(col_width, 10, txt=str(col), border=1)
        pdf.ln()

        # for _, row in df_pivot.iterrows():
        #     for col in col_names:
        #         val = row[col]
        #         pdf.cell(col_width, 10, txt=str("" if pd.isna(val) else val), border=1)
        #     pdf.ln()
        th = pdf.font_size + 1
        for _, row in df_pivot.iterrows():
            # 行の開始位置を記録
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            row_height = 10  # 行の高さの基準値

            # 各列のテキストを分割した結果を保持
            col_texts = []
            max_lines = 1

            # 各列の文字列をあらかじめ分割（描画はしない）
            for col in col_names:
                val = "" if pd.isna(row[col]) else str(row[col])
                lines = pdf.multi_cell(col_width, th, val, border=0, split_only=True)
                col_texts.append(lines)
                max_lines = max(max_lines, len(lines))

            # 最も行数の多いセルに合わせて行の高さを決定
            row_height = th * max_lines

            # 列ごとに描画処理
            x = x_start
            for lines in col_texts:
                pdf.rect(x, y_start, col_width, row_height)  # セルの枠を描画
                for j, line in enumerate(lines):
                    pdf.set_xy(x, y_start + j * th)
                    pdf.cell(col_width, th, line, border=0)
                x += col_width

            # 次の行に移動
            pdf.set_y(y_start + row_height)

        # 時間のローカライズ
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        file_name = f"energy_kesson_report_{now_local.strftime('%Y%m%d%H%M%S')}.pdf"

        data = pdf.output(dest="S")
        if isinstance(data, str):
            data = data.encode("latin-1")  # bytesへ変換

        return file_name, data
