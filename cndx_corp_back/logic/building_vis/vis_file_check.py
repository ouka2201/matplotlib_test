import re
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Counter

import openpyxl
from entity.m_building_entity import MBuilding
from flask import abort
from openpyxl.utils import column_index_from_string
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common.decorators import component
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.logic.building_vis import building_vis_constants as vis_constants


class VisFileCheck:
    def __init__(
        self,
        input_file: FileStorage,
        logger: CorpLogger,
        session: scoped_session,
        org_id: str,
        user_id: str,
        request_dict: dict[str, any],
    ) -> None:

        self.input_file: FileStorage = input_file
        self.check_file_company_name = ["c"]
        self.logger = logger
        self.session = session
        self.org_id = org_id
        self.user_id = user_id
        self.request_dict = request_dict

        self.format_errors: list[str] = ["f"]
        self.data_errors: list[str] = ["d"]
        self.building_error_list: list[str] = ["b"]

    def check_required_headers(
        self,
        ws,
        headers: list[str],
        start_col: str,
        start_row: str,
        single_col_flg: bool = None,
    ):
        """必須カラムチェック

        Args:
            ws (_type_): _description_
            headers (list[str]): _description_
            start_col (str): _description_
            start_row (str): _description_
        """
        sheet_name = ws.title
        start_col_idx = column_index_from_string(start_col)

        for i, expected in enumerate(headers):
            # 列固定・縦方向の場合
            col_idx = start_col_idx
            row_idx = start_row + i if single_col_flg else start_row

            # 横方向の場合
            if not single_col_flg:
                col_idx = start_col_idx + i

            cell = ws.cell(row=row_idx, column=col_idx)
            value = str(cell.value) if cell.value is not None else ""
            if not value.startswith(expected):
                self.format_errors.append(
                    f"以下の列名が{cell.coordinate}にありません：\n{sheet_name}： {expected}"
                )

    # def check_required_headers(self, ws, headers: list[str], start_col: str, start_row: int):
    #     """
    #     必須カラムチェック

    #     Args:
    #         ws: openpyxl worksheet
    #         headers: 期待されるヘッダのリスト
    #         start_col: 開始列 (例: "A")
    #         start_row: 開始行 (例: 5)
    #     """
    #     sheet_name = ws.title
    #     start_col_idx = column_index_from_string(start_col)

    #     for i, expected in enumerate(headers):
    #         col_idx = start_col_idx + i
    #         cell = ws.cell(row=start_row, column=col_idx)
    #         value = str(cell.value) if cell.value is not None else ""

    #         if not value.startswith(expected):
    #             self.format_errors.append(
    #                 f"{sheet_name}!{cell.coordinate} セルは「{expected}」であるべきです (実際: {value})"
    #             )

    def check_cell(self, ws, cell: str, target_val):

        # ----------------------------------------------------
        # ③ 指定セルが指定内容 (例: B2セルが "Report" 固定)
        # ----------------------------------------------------
        sheet_name = ws.title
        if ws[cell].value != target_val:
            self.format_errors.append(
                (f"{sheet_name}!{ws[cell].coordinate}セルは{target_val}であるべきです")
            )

    def check_cell_with_pattern(self, ws, cell: str, pattern: str):
        """
        指定セルが正規表現にマッチするかチェック
        """
        sheet_name = ws.title
        value = str(ws[cell].value) if ws[cell].value is not None else ""

        if not re.match(pattern, value):
            self.format_errors.append(
                f"{sheet_name}!{ws[cell].coordinate} セルの値がパターン {pattern} に一致しません: {value}"
            )

    def round_decimal(self, value, max_scale=2):
        """
        value: float or Decimal
        max_scale: 小数点以下の桁数
        """
        # float -> Decimal に変換
        d = Decimal(str(value))

        # 量子化用のフォーマットを作る
        quantize_str = "1." + "0" * max_scale  # 例: max_scale=2 -> "1.00"

        # ROUND_HALF_UP で丸め
        return d.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    def check_required_buildingNo(self, ws, min_row: int):
        """
        指定列(英字)から最終列までの Decimal 精度チェック

        ws: openpyxl worksheet
        min_row: 開始行番号（例: 6）
        """
        max_row = self._get_effective_max_row(ws)

        sheet_name = ws.title

        # B列とC列のインデックスを取得
        b_col_idx = column_index_from_string("B")
        c_col_idx = column_index_from_string("C")

        for row in range(min_row, max_row + 1):
            b_value = ws.cell(row=row, column=b_col_idx).value
            c_value = ws.cell(row=row, column=c_col_idx).value

            if c_value not in (None, "") and b_value in (None, ""):
                c_cell = ws.cell(row=row, column=c_col_idx)
                b_cell = ws.cell(row=row, column=b_col_idx)
                self.data_errors.append(
                    f"{sheet_name}!{b_cell.coordinate}：物件番号が未入力です。"
                )

    def check_decimal_precision(
        self,
        ws,
        start_col_letter: str,
        max_precision: int,
        max_scale: int,
        min_row: int,
        max_col_letter: str = None,
    ):
        """
        指定列(英字)から最終列までの Decimal 精度チェック

        ws: openpyxl worksheet
        start_col_letter: 開始列（例: "C"）
        max_precision: 全体桁数（例: 25 → 整数部 + 小数部）
        max_scale: 小数点以下桁数（例: 10）
        min_row: 開始行番号（例: 6）
        """
        start_col_idx = column_index_from_string(start_col_letter)
        max_column = self._get_effective_max_col(ws)
        max_row = self._get_effective_max_row(ws)
        if max_col_letter:
            max_col_idx = column_index_from_string(max_col_letter)
        else:
            max_col_idx = max_column

        sheet_name = ws.title

        def clean_float(v, rel_tol=1e-12, abs_tol=1e-15):
            """
            Excel由来の浮動小数誤差を除去する実用関数。
            - まず repr(v) の文字列で「長いゼロ列＋小さな余剰」を検出して切り捨てる（e.g. 1048.5800000000002 -> 1048.58）
            - 次に相対/絶対誤差基準で丸め（e.g. 0.15000000000000002 -> 0.15）
            - 本当に小さい有効値（例 2e-10）は壊さない
            戻り値は Decimal 型（normalize() 済み）。
            """
            _RE_ZERO_TAIL = re.compile(
                r"^(-?\d+\.\d*?)(0{6,}\d+)$"
            )  # 長いゼロ列のあとに小さな余剰（例: 1048.5800000000002）

            if not isinstance(v, float):
                return v

            s = repr(v)

            # 1) 文字列パターンで「...<ゼロ多数><小余剰>」を検出 → 切り捨てして Decimal に
            m = _RE_ZERO_TAIL.match(s)
            if m:
                base_str = m.group(1)  # 例: "1048.58"
                return Decimal(base_str).normalize()

            # 2) Decimal にして相対/絶対誤差で判定・丸め
            # 科学記数法表記（例: 1E+17）を通常表記（例: 100000000000000000）に変換
            dec = Decimal(str(v))
            # 科学記数法表記を通常表記に変換（format()で通常表記の文字列に変換してから再度Decimalに）
            # as_tuple()で指数を取得し、小数点以下の桁数を計算
            sign, digits, exponent = dec.as_tuple()
            if exponent > 0:
                # 正の指数（整数部のみ）の場合、通常表記の文字列に変換
                dec_str = format(dec, "f")
                dec = Decimal(dec_str)
            else:
                # 負の指数（小数部あり）の場合、normalize()で末尾のゼロを削除
                dec = dec.normalize()
            # Excel相当（有効約15桁）で一旦丸め
            try:
                rounded = dec.quantize(Decimal("1e-15"), rounding=ROUND_HALF_UP)
            except InvalidOperation:
                return dec
            except TypeError:
                rounded = Decimal(str(round(v, 15)))
            except Exception:
                # scaleb fallback: (安全に)
                rounded = Decimal(str(round(v, 15)))
            diff = abs(dec - rounded)
            tol = max(Decimal(str(abs_tol)), abs(dec) * Decimal(str(rel_tol)))

            if diff <= tol:
                return rounded.normalize()

            # どれにも該当しなければ元のDecimalを正規化して返す（壊さない）
            return dec.normalize()

        def is_blank_cell(v):
            if v is None:
                return True
            if isinstance(v, str) and v.strip() == "":
                return True
            return False

        for col_idx in range(start_col_idx, max_col_idx):
            col_letter = ws.cell(row=min_row, column=col_idx).column_letter
            for row in ws.iter_rows(
                min_row=min_row, max_row=max_row, min_col=col_idx, max_col=col_idx
            ):
                cell = row[0]
                v = clean_float(cell.value)
                if v is None or is_blank_cell(cell.value):
                    continue
                try:
                    val = Decimal(str(v))
                    sign, digits, exponent = val.as_tuple()

                    precision = len(digits)
                    scale = -exponent if exponent < 0 else 0
                    integer_digits = precision - scale
                    max_integer_digits = max_precision - max_scale

                    # チェック処理
                    if integer_digits > max_integer_digits:
                        self.data_errors.append(
                            (
                                f"以下のセルの整数部桁数が正しくありません：\n"
                                f"{sheet_name}!{cell.coordinate}：{integer_digits}桁 - (最大：{max_integer_digits}桁)"
                            )
                        )

                    elif scale > max_scale:
                        self.data_errors.append(
                            (
                                f"以下のセルの小数桁数が正しくありません：\n"
                                f"{sheet_name}!{cell.coordinate}：{scale}桁 - (最大：{max_scale}桁)"
                            )
                        )

                    elif precision > max_precision:
                        self.data_errors.append(
                            (
                                f"以下のセルの桁数が正しくありません：\n"
                                f"{sheet_name}!{cell.coordinate}：{precision}桁 - (最大：{max_precision}桁)"
                            )
                        )
                except (InvalidOperation, TypeError):
                    self.data_errors.append(
                        (
                            f"以下のセルに数値以外の値が入力されています。\n"
                            f"{sheet_name}!{cell.coordinate}：{clean_float(cell.value)}"
                        )
                    )

    def check_header_month_format(
        self, ws, start_col_letter: str, header_row: int, max_col: int = None
    ):
        """
        5行目のN列以降のヘッダが「YYYY年mm月」または datetime 形式であることをチェック

        ws: openpyxl worksheet
        start_col: チェック開始列 (デフォルトはN列=14)
        header_row: ヘッダ行 (デフォルトは5)
        sheet_name: シート名
        errors: エラーを追加するリスト
        """
        pattern = re.compile(r"^(?:\d{4}年\d{1,2}月|\d{4}/\d{1,2}/\d{1,2})$")
        start_col = column_index_from_string(start_col_letter)
        sheet_name = ws.title

        if max_col:
            max_col = max_col
        else:
            max_col = self._get_effective_max_col(ws)

        # start_colから最終列までループ
        for col_idx in range(start_col, max_col + 1):
            cell = ws.cell(row=header_row, column=col_idx)
            value = self.normalize_header(cell.value)

            # None の場合は終了（右端に到達したとみなす）
            if value is None:
                break

            valid = False

            # ① datetime型ならOK
            if isinstance(value, datetime):
                valid = True

            # ② "YYYY年mm月" フォーマットならOK
            elif isinstance(value, str) and pattern.match(value):
                try:
                    datetime.strptime(value, "%Y年%m月")
                    valid = True
                except ValueError:
                    pass

            if not valid:
                self.data_errors.append(
                    (
                        f"以下のセルに ‘YYYY年mm月’ または日付形式以外の値が入力されています\n{sheet_name}!{cell.coordinate}: {value}"
                    )
                )

    def check_required_sheet(self, wb, required_sheets: list[str]):
        missing = [s for s in required_sheets if s not in wb.sheetnames]

        if len(missing) > 0:
            self.format_errors.append(
                f"以下のシートがファイルに存在しません: {missing}。"
            )

    def check_column_length(
        self,
        ws,
        col: str,
        length: int,
        start_row: int,
        not_fixed_check_flg: bool = None,
        only_num: bool = None,
    ):
        """
        Excelの指定列の文字列桁数チェック（end_rowは自動で検知）

        Parameters
        ----------
        ws : Worksheet
            openpyxl の worksheet オブジェクト
        col : str
            チェック対象の列（例: "B"）
        length : int
            許容する文字数（ちょうど length 桁かを判定）
        start_row : int
            チェックを開始する行番号

        Returns
        -------
        list[str]
            エラーメッセージ一覧（空リストならエラーなし）
        """
        sheet_name = ws.title

        # 列の最終データ行を検知（空セルを無視して最後の行を探す）
        end_row = start_row
        max_row = self._get_effective_max_row(ws)
        for row in range(max_row, start_row - 1, -1):
            if ws[f"{col}{row}"].value not in (None, ""):
                end_row = row
                break

        # チェック処理
        for row in range(start_row, end_row + 1):
            cell = ws[f"{col}{row}"]
            value = str(cell.value).strip() if cell.value is not None else ""
            if not value:
                continue
            if not_fixed_check_flg:
                if len(value) > length:
                    self.data_errors.append(
                        (
                            f"以下のセルの桁数が正しくありません：\n{sheet_name}!{cell.coordinate}：{len(value)}桁 - (最大：{length}桁)"
                        )
                    )
            else:
                if only_num:
                    value_str = str(value).strip()
                    if not value_str.isdigit():
                        # self.data_errors.append(
                        #     f"{sheet_name}!{cell.coordinate} の値が不正: 数字のみ入力可能（値='{value_str}'）"
                        # )
                        self.data_errors.append(
                            (
                                f"以下のセルに数値以外の値が入力されています。\n"
                                f"{sheet_name}!{cell.coordinate}：{value_str}"
                            )
                        )
                if len(value) != length:
                    self.data_errors.append(
                        f"{sheet_name}!{cell.coordinate} の文字数が不正: {len(value)}桁（期待値: {length}桁, 値='{value}'）"
                    )

    def check_num_column(self, ws, col: str, start_row: int):
        sheet_name = ws.title

        # 列の最終データ行を検知
        end_row = start_row
        max_row = self._get_effective_max_row(ws)
        for row in range(max_row, start_row - 1, -1):
            if ws[f"{col}{row}"].value not in (None, ""):
                end_row = row
                break

        # 数値チェックだけ
        for row in range(start_row, end_row + 1):
            cell = ws[f"{col}{row}"]
            value = cell.value

            # 空白はスキップ
            if value is None or str(value).strip() == "":
                continue

            value_str = str(value).strip()

            def is_number(val: str) -> bool:
                try:
                    float(val)
                    return True
                except ValueError:
                    return False

            # 数字チェック
            if not is_number(value_str):
                self.data_errors.append(
                    (
                        f"以下のセルに数値以外の値が入力されています。\n"
                        f"{sheet_name}!{cell.coordinate}：{value_str}"
                    )
                )

    def _get_effective_max_row(self, ws):
        """実質的な最終行を返す（末尾の * や空行を無視）"""
        max_row = ws.max_row
        max_col = ws.max_column

        while max_row > 0:
            row_values = [
                (
                    str(ws.cell(row=max_row, column=col).value).strip()
                    if ws.cell(row=max_row, column=col).value is not None
                    else ""
                )
                for col in range(1, max_col + 1)
            ]

            if all(v == "*" for v in row_values if v != "") or all(
                v == "" for v in row_values
            ):
                max_row -= 1
            else:
                break
        return max_row

    def _get_effective_max_col(self, ws):
        """実質的な最終列を返す（末尾の * や空列を無視）"""
        max_row = ws.max_row
        max_col = ws.max_column

        while max_col > 0:
            col_values = [
                (
                    str(ws.cell(row=row, column=max_col).value).strip()
                    if ws.cell(row=row, column=max_col).value is not None
                    else ""
                )
                for row in range(1, max_row + 1)
            ]

            if all(v == "*" for v in col_values if v != "") or all(
                v == "" for v in col_values
            ):
                max_col -= 1
            else:
                break
        return max_col

    def check_building(self, sheet_name: str, location_cd_list: list[str]):
        """拠点存在チェック

        Args:
            location_cd (str): _description_
        """
        agreement_category = self.request_dict.get("agreement_category", None)
        corporate_number = self.request_dict.get("corporate_number", None)
        if not corporate_number:
            abort(412, description="企業情報が存在しません。")
        for location_cd in location_cd_list:
            building_id = corporate_number + location_cd
            # 建物存在チェック
            exit_mbuilding_entity = (
                self.session.query(MBuilding)
                .filter_by(
                    corporate_number=corporate_number,
                    agreement_category=agreement_category,
                    # agreement_org=self.org_id,
                    building_id=building_id,
                )
                .first()
            )
            if not exit_mbuilding_entity:
                self.building_error_list.append(
                    f"以下の拠点の拠点IDが拠点マスタに登録されていません：{location_cd}"
                )

    def get_location_cd_list(
        self, ws, start_row: int, start_col_letter: str, dup_check_flg=None
    ):

        col_idx = column_index_from_string(start_col_letter)
        max_row = self._get_effective_max_row(ws) + 1
        location_cd_dict = defaultdict(list)  # defaultdictを使用して初期化
        for row in range(start_row, max_row):
            cell_value = ws.cell(row=row, column=col_idx).value
            if cell_value is None:  # データが無いセルは無視
                continue
            location_cd_dict[row].append(cell_value)  # 行番号とlocation_cdのペアを追加

        if dup_check_flg:
            # 値の出現回数をカウント
            all_values = [v[0] for v in location_cd_dict.values()]
            counts = Counter(all_values)

            # 重複（出現回数 > 1）の行だけ残す
            dup_location_cd_dict = {
                row: vals
                for row, vals in location_cd_dict.items()
                if counts[vals[0]] > 1
            }
            return dup_location_cd_dict
        else:
            return [v[0] for v in location_cd_dict.values()]

    def check_company_name(self, file_company_name: str):
        """企業名チェック

        Args:
            file_company_name (str): _description_
        """
        request_company_name = self.request_dict.get("company_name", None)

        # 企業名チェック
        file_company_name = file_company_name if file_company_name else ""
        if file_company_name != request_company_name:
            self.check_file_company_name.append(file_company_name)
            # validator.error_list.append(f"入力ファイルの企業名と不一致です。\
            #     シート上企業名：{sheet_company_name}, 画面上企業名：{company_name}")
            # return

    def normalize_header(self, cell_value):
        if isinstance(cell_value, datetime):
            # datetime 型なら "YYYY年mm月"
            return cell_value.strftime("%Y年%m月")
        elif isinstance(cell_value, (int, float)):
            # シリアル値（Excel 日付）を変換
            date_value = datetime(1899, 12, 30) + timedelta(days=int(cell_value))
            return date_value.strftime("%Y年%m月")
        elif isinstance(cell_value, str):
            # "2022年1月" や "2022/01/01" 文字列を datetime にパース
            try:
                if re.match(r"^\d{4}年\d{1,2}月$", cell_value):
                    return cell_value  # すでにOK
                elif re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", cell_value):
                    dt = datetime.strptime(cell_value, "%Y/%m/%d")
                    return dt.strftime("%Y年%m月")
                else:
                    # フォーマット不正ならそのまま返す（要件に応じてエラーにしても良い）
                    return cell_value
            except Exception:
                return cell_value
        else:
            return str(cell_value) if cell_value is not None else None
