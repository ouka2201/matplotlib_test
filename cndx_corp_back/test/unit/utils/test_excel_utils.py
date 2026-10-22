import base64
import os
import re
import unittest
from io import BytesIO

import pandas as pd

from cndx_corp_back.utils.excel_utils import (
    base64_to_excel,
    exists_sheet,
    get_cell_value,
    get_range_values,
)


class TestExcelUtils(unittest.TestCase):

    def setUp(self):
        # テスト用のExcelファイル
        file_name = "./base64_data_1.txt"
        self.base64_data = ""
        os.chdir(os.path.dirname(__file__))
        if os.path.exists(file_name):
            try:
                with open(file_name, "r") as file:
                    self.base64_data = file.read()
            except Exception as e:
                print(f"テスト資源ファイル（{file_name}）エラー: {e}")
        else:
            print(f"テスト資源ファイル（{file_name}）が存在しません。")

        self.excel_file = base64_to_excel(self.base64_data)

    def test_base64_to_excel(self):
        # base64_to_excel関数のテスト
        self.assertIsInstance(
            self.excel_file, pd.ExcelFile, "Excelファイルの読み込みに失敗しました。"
        )

    def test_sheet_exists(self):
        # sheet_exists関数のテスト
        sheet_name = "test 1"  # 存在するシート名
        self.assertTrue(
            exists_sheet(self.excel_file, sheet_name),
            f"シート '{sheet_name}' が存在しません。",
        )

        sheet_name = "qwerty"  # 存在しないシート名
        self.assertFalse(
            exists_sheet(self.excel_file, sheet_name),
            f"シート '{sheet_name}' が存在するはずがありません。",
        )

    def test_get_cell_value_1(self):
        """get_cell_value関数のテスト　正常系"""
        sheet_name = "test 1"
        cell_row = 1
        cell_col = 2
        expected_value = "2048"
        self.assertEqual(
            get_cell_value(self.excel_file, sheet_name, cell_row, cell_col),
            int(expected_value),
            f"セル ('{cell_row}', '{cell_col}') の値が期待される値と一致しません。",
        )

    def test_get_cell_value_2(self):
        """get_cell_value関数のテスト　存在しないシート名参照"""
        sheet_name = "ああ"  # 存在しないシート名
        cell_row = 1
        cell_col = 2
        self.assertIsInstance(
            get_cell_value(self.excel_file, sheet_name, cell_row, cell_col),
            list,
            f"シート ('{sheet_name}'はありませんが、エラーメッセージが返されていません。",
        )

    def test_get_cell_value_2(self):
        """get_cell_value関数のテスト　存在しないセル参照"""
        sheet_name = "test 1"
        cell_row = 1  # 存在しないセル
        cell_col = 3  # 存在しないセル
        self.assertIsInstance(
            get_cell_value(self.excel_file, sheet_name, cell_row, cell_col),
            list,
            f"セル ('{cell_row}', '{cell_col}') に値が存在するはずがありません。",
        )

    def test_get_range_values_1(self):
        """get_range_values関数のテスト　正常系"""
        sheet_name = "テスト2"

        rows_list = range(2, 6)
        cols_list = range(1, 3)
        expected_values = [[21, 22], [31, 32], [41, 42], [51, 52]]

        self.assertEqual(
            get_range_values(self.excel_file, sheet_name, rows_list, cols_list),
            expected_values,
            f"結果が期待される値と一致しません。",
        )

    def test_get_range_values_2(self):
        """get_range_values関数のテスト　異常系"""
        sheet_name = "テスト222"  # 存在しないシート名

        rows_list = range(2, 6)
        cols_list = range(1, 3)

        self.assertIsInstance(
            get_range_values(self.excel_file, sheet_name, rows_list, cols_list)[0],
            str,
            f"シート ('{sheet_name}'はありませんが、エラーメッセージが返されていません。",
        )


if __name__ == "__main__":
    unittest.main()
