import re
from decimal import Decimal

import openpyxl
from logic.building_vis.building_vis_utils import is_numeric
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common.decorators import component
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.entity.m_benchmark_info_entity import MBenchmarkInfo
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.m_jp_st_industry_classification_entity import (
    MJpStIndustryClassification,
)
from cndx_corp_back.logic.building_vis import building_vis_constants as vis_constants
from cndx_corp_back.logic.building_vis.vis_file_check import VisFileCheck


@component
class VisHearingDataCheck(VisFileCheck):
    def __init__(
        self,
        input_file: FileStorage,
        logger: CorpLogger,
        session: scoped_session,
        org_id: str,
        user_id: str,
        request_dict: dict[str, any],
    ) -> None:
        super().__init__(input_file, logger, session, org_id, user_id, request_dict)

    def execute(self):
        wb = openpyxl.load_workbook(self.input_file.stream, data_only=True)

        # 必須シート
        self.check_required_sheet(wb, vis_constants.hearing_required_sheet_names)
        if len(self.format_errors) > 1:
            # フォーマットチェックエラー
            return self.format_errors

        # B列 2行目～11行目をループ
        ws_corp = wb["企業情報"]
        # 期待項目リスト
        expected_values = [
            "企業名",
            "法人番号",
            "GHG排出量算定システム会社名",
            "日本産業分類（大分類）",
            "日本産業分類（中分類）",
            "日本産業分類（小分類）",
            "日本産業分類（細分類）",
            "日本産業分類（細分類番号）",
            "【対象の場合のみ】省エネ法ベンチマーク対象業種",
            "【対象の場合のみ】省エネ法ベンチマーク指標",
        ]

        # B列項目チェック
        self.check_required_headers(
            ws_corp, expected_values, start_col="B", start_row=3, single_col_flg=True
        )

        self.validate_corp_sheet_required(wb)

        ws_building = wb["拠点情報"]
        # 必須列チェック
        building_headers = [
            "会社名",
            "法人番号",
            "拠点識別番号",
            "拠点識別名",
            "住所",
            "供給地点特定番号",
            "店所番号",
            "お客さま番号",
            "延床面積",
        ]
        self.check_required_headers(
            ws_building, building_headers, start_col="A", start_row=4
        )

        # 必須列チェック
        building_industry_headers = ["大分類", "中分類", "小分類", "細分類"]
        self.check_required_headers(
            ws_building, building_industry_headers, start_col="J", start_row=5
        )

        self.validate_base_sheet_required(ws_building)

        self.check_cell_with_pattern(ws_building, "N2", r"^原単位分母")
        self.check_cell_with_pattern(ws_building, "O2", r"^原単位分母")
        self.check_cell_with_pattern(
            ws_building, "S3", r"^省エネ法ベンチマーク制度対象業種"
        )
        self.check_cell_with_pattern(ws_building, "T4", r"^省エネ法")

        ws_unit = wb["（任意）原単位分母"]
        # 必須列チェック
        unit_headers = ["会社名", "法人番号", "拠点識別番号", "拠点名", "原単位分母"]
        self.check_required_headers(ws_unit, unit_headers, start_col="A", start_row=4)

        ws_credit = wb["証書・クレジット"]
        # 必須列チェック
        credit_headers = [
            "会社名",
            "法人番号",
            "拠点識別番号",
            "拠点名",
            "証書・クレジット名",
        ]
        self.check_required_headers(
            ws_credit, credit_headers, start_col="A", start_row=3
        )

        # 日付カラムチェック
        self.check_header_month_format(ws_credit, start_col_letter="G", header_row=3)

        # 証書・クレジット名の検証
        self.validate_credit_sheet(ws_credit)

        # 企業情報シートの産業分類と省エネ法ベンチマーク対象業種のチェック
        self.validate_corp_sheet_industry(wb, self.session)

        # 拠点情報シートの産業分類と省エネ法ベンチマーク対象業種のチェック
        self.validate_base_sheet_industry(ws_building, self.session)

        if len(self.format_errors) > 1:
            # フォーマットチェックエラー
            return self.format_errors

        # 企業情報シート 省エネ法ベンチマーク指標年度チェック（型チェック・桁数チェックに含める）
        sheet_name = ws_corp.title
        value_C12 = (
            str(ws_corp["C12"].value) if ws_corp["C12"].value is not None else ""
        )
        self.benchmark_year_check(value_C12, sheet_name, ws_corp, "C12")

        # 拠点情報シート 省エネ法ベンチマーク指標年度チェック（型チェック・桁数チェックに含める）
        value_T5 = (
            str(ws_building["T5"].value) if ws_building["T5"].value is not None else ""
        )
        self.benchmark_year_check(value_T5, ws_building.title, ws_building, "T5")

        # 企業情報シートD12(省エネ法ベンチマーク指標)の型・桁数チェック
        value_D12 = ws_corp["D12"].value
        if value_D12 is not None:
            if isinstance(value_D12, (int, float)):
                # 科学記数法を通常表記に変換
                dec = Decimal(str(value_D12))
                sign, digits, exponent = dec.as_tuple()
                if exponent > 0:
                    # 正の指数（整数部のみ）の場合、通常表記の文字列に変換
                    dec_str = format(dec, "f")
                    dec = Decimal(dec_str)
                else:
                    # 負の指数（小数部あり）の場合、normalize()で末尾のゼロを削除
                    dec = dec.normalize()
                # 通常表記の文字列に変換（小数点以下は削除せず、そのまま）
                value_str = str(dec)
                # 小数点とマイナス記号を除いた桁数をカウント
                digit_count = len(value_str.replace(".", "").replace("-", ""))
                if digit_count > 100:
                    self.data_errors.append(
                        f"{sheet_name}!{ws_corp['D12'].coordinate} セルの値が正しくありません: "
                        f"桁数が正しくありません{digit_count}桁 - (最大：100桁)"
                    )
            else:
                self.data_errors.append(
                    f"{sheet_name}!{ws_corp['D12'].coordinate} セルの値が正しくありません: 数値以外の値が入力されています。"
                )

        # 企業情報シートD3(GHG排出量算定システム会社名)の型・桁数チェック
        value_D5 = ws_corp["D5"].value if ws_corp["D5"].value is not None else ""
        if len(value_D5) > 50:
            self.data_errors.append(
                f"{sheet_name}!{ws_corp['D5'].coordinate} の文字数が不正: {len(value_D5)}文字 - (最大：50文字)"
            )

        self.check_column_length(
            ws_building, col="C", length=100, start_row=6, not_fixed_check_flg=True
        )

        self.check_decimal_precision(
            ws_building,
            start_col_letter="O",
            max_precision=10,
            max_scale=3,
            min_row=6,
            max_col_letter="P",
        )

        self.check_decimal_precision(
            ws_building,
            start_col_letter="T",
            max_precision=100,
            max_scale=5,
            min_row=6,
            max_col_letter="U",
        )

        # 証書桁数チェック
        self.check_decimal_precision(
            ws_credit,
            start_col_letter="G",
            max_precision=12,
            max_scale=3,
            min_row=4,
            max_col_letter="AD",
        )

        # 省エネ法ベンチマーク制度分母数値
        self.check_decimal_precision(
            ws_building,
            start_col_letter="U",
            max_precision=10,
            max_scale=3,
            min_row=6,
            max_col_letter="AO",
        )

        # 型チェック・桁数チェックのエラーを全て収集した後、返却
        if len(self.data_errors) > 1:
            # 型チェック・桁数チェックエラー
            return self.data_errors

        # 拠点存在チェック
        location_cd_list = self.get_location_cd_list(
            ws_building, start_row=6, start_col_letter="C"
        )
        self.check_building(ws_building.title, location_cd_list)
        if len(self.building_error_list) > 1:
            # フォーマットチェックエラー
            return self.building_error_list

        # 企業名チェック
        file_company_name = ws_corp["D3"].value
        self.check_company_name(file_company_name=file_company_name)

        if len(self.check_file_company_name) > 1:
            # フォーマットチェックエラー
            return self.check_file_company_name

        return file_company_name

    def benchmark_year_check(self, value, sheet_name, ws_name, cell_name):
        if not re.match(r"^\d{4}(年度)?$", value):
            if re.match(r"^\d{4}$", value):
                self.data_errors.append(
                    f"{sheet_name}!{ws_name[cell_name].coordinate} セルの値が正しくありません: {value}。年度を記載してください。"
                )
            elif "年度" in value:
                if re.match(r"^\d+", value) and not re.match(r"^\d{4}", value):
                    self.data_errors.append(
                        f"{sheet_name}!{ws_name[cell_name].coordinate} セルの値が正しくありません: {value}。年度は4桁である必要があります。"
                    )
                else:
                    self.data_errors.append(
                        f"{sheet_name}!{ws_name[cell_name].coordinate} セルの値が正しくありません: {value}。先頭が4桁の数値である必要があります。"
                    )
            else:
                self.data_errors.append(
                    f"{sheet_name}!{ws_name[cell_name].coordinate} セルの値がパターン ^\\d{{4}}(年度)?$ に一致しません: {value}"
                )
        return self.data_errors

    def find_row_by_item(self, ws, item_name, item_col=2, max_rows=200):
        """
        フォーム型Excel用：
        B列（item_col=2）から項目名を探して行番号を返す
        """
        for row in range(1, max_rows + 1):
            val = ws.cell(row=row, column=item_col).value
            if val is None:
                continue
            if str(val).strip() == item_name:
                return row
        return None

    def validate_corp_sheet_required(self, wb):
        ws = wb["企業情報"]

        # 必须入力項目（企业信息）
        required_items = [
            "日本産業分類（細分類番号）",
            "【対象の場合のみ】省エネ法ベンチマーク対象業種",
        ]

        for item in required_items:
            row = self.find_row_by_item(ws, item)

            value = ws.cell(row=row, column=4).value  # D列：入力欄
            if value in (None, ""):
                self.data_errors.append(f"【企業情報】「{item}」は必須入力です。")

    def is_empty_cell(self, value) -> bool:
        """
        セルが未入力かどうかを判定する
        ・None
        ・空文字
        ・空白（全角／半角）のみ
        を未入力とみなす
        """
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False

    def validate_base_sheet_required(self, ws_base):
        """
        拠点情報シートの必須チェック

        【仕様】
        ・C列に値が入力されている行は「有効な拠点行」とみなす
        ・有効な拠点行の場合、以下の項目は必須
            - M列：細分類
            - S列：省エネ法ベンチマーク制度対象業種
        """

        # 6行目以降をデータ行としてチェック
        for row in range(6, ws_base.max_row + 1):

            # C列（拠点を判定する基準列）
            c_value = ws_base.cell(row=row, column=3).value

            # C列が未入力の場合、この行はチェック対象外
            if self.is_empty_cell(c_value):
                continue

            # --- ここから「有効な拠点行」 ---

            # M列：細分類
            m_value = ws_base.cell(row=row, column=13).value

            # S列：省エネ法ベンチマーク制度対象業種
            s_value = ws_base.cell(row=row, column=19).value

            # デバッグ用（必要に応じて削除）
            print(
                f"[DEBUG] row={row}, "
                f"C列={repr(c_value)}, "
                f"M列={repr(m_value)}, "
                f"S列={repr(s_value)}"
            )

            # 細分類（M列）必須チェック
            if self.is_empty_cell(m_value):
                self.data_errors.append(
                    f"【拠点情報】{row}行目：" "「細分類」は必須入力です。"
                )

            # 省エネ法ベンチマーク制度対象業種（S列）必須チェック
            if self.is_empty_cell(s_value):
                self.data_errors.append(
                    f"【拠点情報】{row}行目："
                    "「省エネ法ベンチマーク制度対象業種」は必須入力です。"
                )

    def validate_credit_sheet(self, ws_credit):
        """
        証書・クレジットシートのE列（証書・クレジット名）検証

        【仕様】
        - E4から下に向かってE列を検査
        - 同一行のC列（拠点識別番号）に値がある場合のみ検査対象
        - C列が空になったら検査終了
        - E列の値（trim後）がm_corp_code_infoテーブルの
          code LIKE '9900%'の条件で取得したjp_code_nameリストに含まれているか検証
        - E列が空の場合もエラー
        - 全ての行を検査してからまとめてエラーを返す

        Args:
            ws_credit: 証書・クレジットシートのワークシート
        """
        sheet_name = ws_credit.title

        try:
            # データベースからcode LIKE '9900%'のjp_code_nameリストを取得
            valid_credit_names = (
                self.session.query(MCorpCodeInfo.jp_code_name)
                .filter(MCorpCodeInfo.code.like("9900%"))
                .all()
            )

            # jp_code_nameのリストを作成（trim処理）
            valid_names_set = {
                name[0].strip() for name in valid_credit_names if name[0]
            }

        except Exception as e:
            self.logger.error(
                f"[validate_credit_sheet] データベース取得エラー: {str(e)}"
            )
            self.data_errors.append(
                "証書・クレジット名の検証中にエラーが発生しました。"
            )
            return

        # E4から検査開始
        row = 4
        max_row = self._get_effective_max_row(ws_credit)

        while row <= max_row:
            # C列（拠点識別番号）の値を取得
            c_value = ws_credit.cell(row=row, column=3).value

            # C列が空の場合、検査終了
            if self.is_empty_cell(c_value):
                break

            # E列（証書・クレジット名）の値を取得
            e_value = ws_credit.cell(row=row, column=5).value
            e_cell_coord = ws_credit.cell(row=row, column=5).coordinate

            # E列が空の場合、エラー
            if not self.is_empty_cell(e_value):
                # E列の値をtrim
                e_value_trimmed = str(e_value).strip()

                # データベースのjp_code_nameリストに含まれているか検証,E列にある値は存在すると、チェックします。存在しないと、チェックしません。
                if e_value_trimmed and e_value_trimmed not in valid_names_set:
                    error_msg = f"シートの「{sheet_name}」の{e_cell_coord}証書・クレジット名「{e_value_trimmed}」は存在しません。"
                    self.data_errors.append(error_msg)
                    self.logger.warning(
                        f"[validate_credit_sheet] E列の値が不正: {e_cell_coord}={repr(e_value_trimmed)}"
                    )

            row += 1

    def validate_corp_sheet_industry(self, wb, session):
        """
        日本産業分類の階層整合性チェック
        （大分類 → 中分類 → 小分類 → 細分類）
        """

        ws = wb["企業情報"]

        # ----------------------------------------
        # ① 各分類の値を取得
        # ----------------------------------------
        division_row = self.find_row_by_item(ws, "日本産業分類（大分類）")
        major_group_row = self.find_row_by_item(ws, "日本産業分類（中分類）")
        group_row = self.find_row_by_item(ws, "日本産業分類（小分類）")
        industry_row = self.find_row_by_item(ws, "日本産業分類（細分類）")

        # ベンチマーク対象業種行
        benchmark_row = self.find_row_by_item(
            ws, "【対象の場合のみ】省エネ法ベンチマーク対象業種"
        )

        division_value = (ws.cell(row=division_row, column=4).value or "").strip()
        major_group_value = (ws.cell(row=major_group_row, column=4).value or "").strip()
        group_value = (ws.cell(row=group_row, column=4).value or "").strip()
        industry_value = (ws.cell(row=industry_row, column=4).value or "").strip()
        benchmark_value = (ws.cell(row=benchmark_row, column=4).value or "").strip()

        # 空欄はここではチェックしない（必須チェックは別処理）
        if not (
            division_value and major_group_value and group_value and industry_value
        ):
            return

        # ----------------------------------------
        # ② code:name 形式から code 部分を抽出
        # ----------------------------------------
        try:
            division_code = division_value.split(":")[0]
            major_group_code = major_group_value.split(":")[0]
            group_code = group_value.split(":")[0]
            industry_code = industry_value.split(":")[0]
        except Exception:
            self.data_errors.append(
                "【企業情報】日本産業分類の形式が不正です。（code:name 形式で入力してください）"
            )
            return

        # ----------------------------------------
        # ③ 階層を絞り込んで1件存在するか確認
        # ----------------------------------------
        exists = (
            session.query(MJpStIndustryClassification)
            .filter(
                MJpStIndustryClassification.division_code == division_code,
                MJpStIndustryClassification.major_group_code == major_group_code,
                MJpStIndustryClassification.group_code == group_code,
                MJpStIndustryClassification.industry_code == industry_code,
            )
            .first()
        )

        if not exists:
            self.data_errors.append(
                "【企業情報】日本産業分類（大・中・小・細分類）の組み合わせが正しくありません。"
            )

        # ----------------------------------------
        # ④ 【対象の場合のみ】ベンチマーク制度対象業種チェック
        # ----------------------------------------

        # 空欄はここではチェックしない（必須チェックは別処理）
        if not benchmark_value:
            return

        try:
            benchmark_code = benchmark_value.split(":")[0]
        except Exception:
            self.data_errors.append(
                "【企業情報】省エネ法ベンチマーク対象業種の形式が不正です。（code:name形式）"
            )
            return

        # 細分類コードでマスタ検索
        benchmark_list = (
            session.query(MBenchmarkInfo)
            .filter(MBenchmarkInfo.industry_class_detail_code == industry_code)
            .all()
        )

        if not benchmark_list:
            self.data_errors.append(
                "【企業情報】細分類に対応する省エネ法ベンチマーク対象業種がマスタに存在しません。"
            )
            return

        # ----------------------------------------
        # DB側の code:name 一覧を生成
        # ----------------------------------------
        db_benchmark_values = [b.pulldown_code for b in benchmark_list]

        # ----------------------------------------
        # Excel値がDB一覧に存在するかチェック
        # ----------------------------------------
        if benchmark_code not in db_benchmark_values:
            self.data_errors.append(
                "【企業情報】省エネ法ベンチマーク対象業種がマスタと一致していません。"
            )

    def validate_base_sheet_industry(self, ws_base, session):
        """
        拠点情報シート：
        日本産業分類（大・中・小・細）の
        階層整合性チェック

        【仕様】
        ・6行目以降を対象
        ・C列に値がある行のみチェック対象
        ・J～M列は code:name 形式
        ・4分類が同一マスタレコードに存在するか確認する
        """

        # 6行目以降をチェック
        for row in range(6, ws_base.max_row + 1):

            # C列（拠点判定列）
            c_value = ws_base.cell(row=row, column=3).value

            # C列が未入力または「*」の場合は対象外
            if c_value == "" or c_value == "*":
                continue

            # -----------------------------
            # J～M列の値を取得
            # -----------------------------
            division_value = (
                ws_base.cell(row=row, column=10).value or ""
            ).strip()  # J列
            major_group_value = (
                ws_base.cell(row=row, column=11).value or ""
            ).strip()  # K列
            group_value = (ws_base.cell(row=row, column=12).value or "").strip()  # L列
            industry_value = (
                ws_base.cell(row=row, column=13).value or ""
            ).strip()  # M列

            # いずれか空欄の場合はここではチェックしない（必須チェックは別処理）
            if not (
                division_value and major_group_value and group_value and industry_value
            ):
                continue

            # -----------------------------
            # code:name 形式から code 抽出
            # -----------------------------
            try:
                division_code = division_value.split(":")[0]
                major_group_code = major_group_value.split(":")[0]
                group_code = group_value.split(":")[0]
                industry_code = industry_value.split(":")[0]
            except Exception:
                self.data_errors.append(
                    f"【拠点情報】{row}行目：日本産業分類の形式が不正です。（code:name 形式で入力してください）"
                )
                continue

            # -----------------------------
            # マスタに同一レコードが存在するか確認
            # -----------------------------
            exists = (
                session.query(MJpStIndustryClassification)
                .filter(
                    MJpStIndustryClassification.division_code == division_code,
                    MJpStIndustryClassification.major_group_code == major_group_code,
                    MJpStIndustryClassification.group_code == group_code,
                    MJpStIndustryClassification.industry_code == industry_code,
                )
                .first()
            )

            if not exists:
                self.data_errors.append(
                    f"【拠点情報】{row}行目："
                    "日本産業分類（大・中・小・細分類）の組み合わせが正しくありません。"
                )

            # =============================
            # ② 省エネ法ベンチマーク制度対象業種チェック（S列）
            # =============================
            benchmark_value = (
                ws_base.cell(row=row, column=19).value or ""
            ).strip()  # S列

            try:
                benchmark_code = benchmark_value.split(":")[0]
            except Exception:
                self.data_errors.append(
                    f"【拠点情報】{row}行目："
                    "省エネ法ベンチマーク制度対象業種の形式が不正です。（code:name形式）"
                )
                return

            # 細分類コードからMBenchmarkInfoを取得
            benchmark_list = (
                session.query(MBenchmarkInfo)
                .filter(MBenchmarkInfo.industry_class_detail_code == industry_code)
                .all()
            )

            if not benchmark_list:
                self.data_errors.append(
                    f"【拠点情報】{row}行目："
                    "細分類に対応する省エネ法ベンチマーク制度対象業種がマスタに存在しません。"
                )
                continue

            # ----------------------------------------
            # DB側の code:name 一覧を生成
            # ----------------------------------------
            db_benchmark_values = [b.pulldown_code for b in benchmark_list]

            # ----------------------------------------
            # 完全一致チェック（Excel値がDB一覧に存在するか）
            # ----------------------------------------
            if benchmark_code not in db_benchmark_values:
                self.data_errors.append(
                    f"【拠点情報】{row}行目："
                    "省エネ法ベンチマーク制度対象業種がマスタと一致していません。"
                )
