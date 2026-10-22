import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
from fpdf import FPDF as BaseFPDF
from sqlalchemy import String, cast, func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)


class KessonReportCreateLogic:

    # @log_time
    def generate_pdf_report(
        self, df_building, request_dict: dict, logger, prefetched_data: dict = None
    ) -> str:
        # create_filesで一括取得済みのデータを変数に展開
        company_name = prefetched_data.get("company_name", "")
        energy_df_by_building = prefetched_data.get("energy_df_by_building", {})
        df_energy_all = prefetched_data.get("df_energy_all", pd.DataFrame())
        target_building_ids = set(df_building["building_id"])

        ordered_building_ids = (
            df_energy_all["building_id"].tolist()
            if "building_id" in df_energy_all.columns
            else []
        )

        dfs = [
            energy_df_by_building[bid]
            for bid in ordered_building_ids
            if bid in target_building_ids and bid in energy_df_by_building
        ]

        df_energy = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

        # 既存ロジックとの互換性のため定義
        consent_route = request_dict["consent_route"]
        df_merged = pd.DataFrame()

        consent_route = request_dict["consent_route"]

        if df_energy.empty:
            logger.info("データ欠損数データが存在しません。CSV出力をスキップします。")
            # return ""
        else:
            df_energy["cert_flg"] = df_energy["証書クレジット"].notna().astype(int)

            # マージ実行
            df_merged = df_energy.merge(
                df_building,
                on="building_id",
                how="inner",
                suffixes=("", "_right"),  # df_energy 側はそのまま
            )

            # df_merged = (
            #             df_merged.sort_values(["building_id", "件数"], ascending=[True, False], kind="mergesort")
            #             .drop_duplicates(subset=["building_id"], keep="first")
            #             .reset_index(drop=True)
            #     )
        if df_merged.empty:
            logger.info("データ欠損数データが存在しません。CSV出力をスキップします。")
            # return ""

        # --- 出力行作成 ---

        # 住所の結合
        # 0 や False を維持し、None/NaN のみ空文字にする処理
        def to_blank(series):
            # .replace(0, "") により、数値の 0 も空文字に変換される
            return (
                series.fillna("").replace([0, 0.0, False, "0", "0.0"], "").astype(str)
            )

        df_merged["住所_combined"] = (
            to_blank(df_merged["住所都道府県"])
            + to_blank(df_merged["住所"])
            + to_blank(df_merged["事業所コード"])
        )

        # フラグ計算

        # 証書・クレジット未設定判定
        # cert_flg = b["group_cert_flg"] (集計用一時DF作成時に適用)
        df_merged = df_merged.sort_values(
            ["拠点識別番号", "energy_code"], ascending=[True, True]
        )

        df_merged["group_cert_flg"] = df_merged.groupby(["拠点識別番号", "拠点識別名"])[
            "cert_flg"
        ].transform(lambda s: 1 if s.all() else 0)

        # 細分類判定
        # building_use_flg = 1 if b["業種コード"] is None or val == "" else 0
        df_merged["building_use_flg"] = (
            df_merged["業種コード"].isna() | (df_merged["業種コード"].astype(str) == "")
        ).astype(int)

        # 省エネ法ベンチマーク業種判定
        # benchmark_industry_flg = 1 if b["省エネ法ベンチマーク業種"] is None or val == "" else 0
        df_merged["benchmark_industry_flg"] = (
            df_merged["省エネ法ベンチマーク業種"].isna()
            | (df_merged["省エネ法ベンチマーク業種"].astype(str) == "")
        ).astype(int)

        # 延床面積
        # gross_floor_area_flg = 1 if b["延床面積"] is None else 0
        df_merged["gross_floor_area_flg"] = df_merged["延床面積"].isna().astype(int)

        # 省エネ法ベンチマーク指標判定
        # benchmark_indicator_flg = 1 if b["省エネ法ベンチマーク指標"] is None else 0
        # (初期値として int の 0 or 1 で保持し、集計後にハイフンへ置換)
        df_merged["benchmark_indicator_flg_val"] = (
            df_merged["省エネ法ベンチマーク指標"].isna().astype(int)
        )

        # 件数の計算 (12 - int(b["件数"]) の挙動を維持。非数値があれば例外を出す)
        df_merged["energy_diff"] = 12 - df_merged["件数"].astype(int)

        # 集計用の一時DataFrame作成
        column = [
            "同意書取得経路",
            "企業名",
            "拠点識別番号",
            "拠点識別名",
            "住所",
            "お客さま番号",
            "供給地点特定番号",
            "エネルギー使用量データ",
            "証書・クレジット",
            "延床面積",
            "建物用途（細分類番号）",
            "省エネ法ベンチマーク対象業種",
            "省エネ法ベンチマーク指標",
        ]

        temp_df = pd.DataFrame(
            {
                "同意書取得経路": consent_route,
                "企業名": company_name,
                "拠点識別番号": df_merged["拠点識別番号"],
                "拠点識別名": df_merged["拠点識別名"],
                "住所": df_merged["住所_combined"],
                "お客さま番号": df_merged["お客さま番号"],
                "供給地点特定番号": df_merged["供給地点特定番号"],
                "エネルギー使用量データ": df_merged["energy_diff"],
                "証書・クレジット": df_merged["group_cert_flg"],
                "延床面積": df_merged["gross_floor_area_flg"],
                "建物用途（細分類番号）": df_merged["building_use_flg"],
                "省エネ法ベンチマーク対象業種": df_merged["benchmark_industry_flg"],
                "省エネ法ベンチマーク指標": df_merged["benchmark_indicator_flg_val"],
            }
        )

        # エネルギーごと欠損コマ数合併 (Groupby)
        # --- DataFrame化およびエネルギーごと欠損コマ数合併 ---
        group_cols = [c for c in column if c != "エネルギー使用量データ"]
        df = temp_df.groupby(group_cols, as_index=False)["エネルギー使用量データ"].sum()

        # 省エネ法ベンチマーク指標のハイフン判定
        # 元ロジック: if benchmark_industry_flg == 1: benchmark_indicator_flg = "-"
        df.loc[df["省エネ法ベンチマーク対象業種"] == 1, "省エネ法ベンチマーク指標"] = (
            "-"
        )

        # 「集計対象以外の列による昇順ソート」を明示的に実行し、行順を完全一致させる
        sort_columns = [c for c in column if c != "エネルギー使用量データ"]
        df = df.sort_values(sort_columns, ascending=True).reset_index(drop=True)
        df["エネルギー使用量データ"] = df["エネルギー使用量データ"].astype(int)

        # 最後に列順序を確定
        df = df[column]

        # --- フォント設定 ---
        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        font_path = os.path.join(BASE_DIR, "static", "fonts", "NotoSansJP-Regular.ttf")
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"フォントファイルが見つかりません: {font_path}")

        class FPDF(BaseFPDF):
            def header(self):
                self.set_font("NotoSans", "", 14)
                self.cell(0, 10, "データ欠損一覧レポート", ln=True, align="C")

        pdf = FPDF(orientation="L", unit="mm", format="A3")
        pdf.add_font("NotoSans", "", font_path, uni=True)
        pdf.set_font("NotoSans", size=8)
        pdf.add_page()
        th = pdf.font_size + 1

        col_widths = [40, 40, 25, 35, 35, 30, 25, 25, 25, 25, 32, 32, 32]

        headers = [
            "同意書取得経路",
            "企業名",
            "拠点識別番号",
            "拠点識別名",
            "住所",
            "お客さま番号",
            "供給地点\n特定番号",
            "エネルギー\n使用量データ",
            "証書・\nクレジット",
            "延床\n面積",
            "建物用途\n（細分類番号）",
            "省エネ法\nベンチマーク\n対象業種",
            "省エネ法\nベンチマーク\n指標",
        ]

        def draw_multiline_cell(pdf, x, y, w, h, text, align="C"):
            lines = text.split("\n")
            line_height = h / len(lines)
            pdf.rect(x, y, w, h)
            for i, line in enumerate(lines):
                pdf.set_xy(x, y + i * line_height)
                pdf.multi_cell(w, line_height, line, border=0, align=align)

        # --- 表ヘッダー描画 ---
        row_height = 15
        y_start = pdf.get_y()
        x_start = pdf.get_x()
        for i, header in enumerate(headers):
            draw_multiline_cell(
                pdf, x_start, y_start, col_widths[i], row_height, header, align="C"
            )
            x_start += col_widths[i]

        # --- 表データ描画 ---
        pdf.set_y(y_start + row_height)
        for _, row in df.iterrows():
            x_origin = pdf.get_x()
            y_origin = pdf.get_y()
            split_texts = []
            max_line_count = 1
            for i, item in enumerate(row):
                cell_text = str(item) if item is not None else ""
                lines = pdf.multi_cell(
                    col_widths[i], th, cell_text, border=0, align="L", split_only=True
                )
                split_texts.append(lines)
                max_line_count = max(max_line_count, len(lines))

            row_height = th * max_line_count
            x_now = x_origin
            for i, lines in enumerate(split_texts):
                pdf.rect(x_now, y_origin, col_widths[i], row_height)
                for j, line in enumerate(lines):
                    pdf.set_xy(x_now, y_origin + j * th)
                    pdf.cell(col_widths[i], th, line, ln=0, align="L")
                x_now += col_widths[i]
            pdf.set_y(y_origin + row_height)

        # 時間のローカライズ
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        file_name = f"kesson_report_basic_{now_local.strftime('%Y%m%d%H%M%S')}.pdf"

        data = pdf.output(dest="S")
        if isinstance(data, str):
            data = data.encode("latin-1")  # bytesへ変換

        return file_name, data
