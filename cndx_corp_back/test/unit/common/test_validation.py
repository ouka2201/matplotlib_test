import unittest

from cndx_corp_back.common.validation import (
    allowed_characters_check,
    decimal_digits_check,
    length_check,
    numeric_range_check,
    required_check,
)


class TestValidation(unittest.TestCase):

    def setUp(self):
        """テスト用のエラーメッセージリストを初期化"""
        self.err_list = []

    def test_required_check(self):
        """必須チェックのテスト"""

        # 値がNoneの場合
        result = required_check(None, "テスト項目", self.err_list)
        self.assertFalse(result)
        self.assertIn("テスト項目が入力されていません。", self.err_list)
        self.err_list.clear()

        # 値が空文字の場合
        result = required_check("", "テスト項目", self.err_list)
        self.assertFalse(result)
        self.assertIn("テスト項目が入力されていません。", self.err_list)
        self.err_list.clear()

        # 値が存在する場合
        result = required_check("値あり", "テスト項目", self.err_list)
        self.assertTrue(result)
        self.assertNotIn("テスト項目が入力されていません。", self.err_list)

    def test_length_check(self):
        """文字列の長さチェックのテスト"""

        # 最小長さチェック
        result = length_check("短い", "テスト項目", self.err_list, min_length=5)
        self.assertFalse(result)
        self.assertIn("テスト項目は5文字以上で入力してください。", self.err_list)
        self.err_list.clear()

        # 最大長さチェック
        result = length_check(
            "長すぎる文字列", "テスト項目", self.err_list, max_length=5
        )
        self.assertFalse(result)
        self.assertIn("テスト項目は5文字以下で入力してください。", self.err_list)
        self.err_list.clear()

        # 長さが範囲内の場合
        result = length_check(
            "ちょうどいい", "テスト項目", self.err_list, min_length=5, max_length=10
        )
        self.assertTrue(result)
        self.assertNotIn("テスト項目は5文字以上で入力してください。", self.err_list)
        self.assertNotIn("テスト項目は10文字以下で入力してください。", self.err_list)

    def test_decimal_digits_check(self):
        """整数部と小数部の桁数チェックのテスト"""

        # 整数部が指定された桁数を超える場合
        result = decimal_digits_check(
            "12345.67", "テスト項目", self.err_list, integer_digits=4, decimal_digits=2
        )
        self.assertFalse(result)
        self.assertIn("テスト項目の整数部は4桁以下で入力してください。", self.err_list)
        self.err_list.clear()

        # 小数部が指定された桁数を超える場合
        result = decimal_digits_check(
            "1234.678", "テスト項目", self.err_list, integer_digits=4, decimal_digits=2
        )
        self.assertFalse(result)
        self.assertIn("テスト項目の小数部は2桁以下で入力してください。", self.err_list)
        self.err_list.clear()

        # 整数部と小数部が指定された桁数以内の場合
        result = decimal_digits_check(
            "1234.67", "テスト項目", self.err_list, integer_digits=4, decimal_digits=2
        )
        self.assertTrue(result)
        self.assertNotIn(
            "テスト項目の整数部は4桁以下で入力してください。", self.err_list
        )
        self.assertNotIn(
            "テスト項目の小数部は2桁以下で入力してください。", self.err_list
        )

        # 小数点がない場合
        result = decimal_digits_check(
            "1234", "テスト項目", self.err_list, integer_digits=4, decimal_digits=2
        )
        self.assertTrue(result)
        self.assertNotIn(
            "テスト項目の整数部は4桁以下で入力してください。", self.err_list
        )
        self.assertNotIn(
            "テスト項目の小数部は2桁以下で入力してください。", self.err_list
        )

        # 小数点以下が0の場合
        result = decimal_digits_check(
            "1234.0", "テスト項目", self.err_list, integer_digits=4, decimal_digits=2
        )
        self.assertTrue(result)
        self.assertNotIn(
            "テスト項目の整数部は4桁以下で入力してください。", self.err_list
        )
        self.assertNotIn(
            "テスト項目の小数部は2桁以下で入力してください。", self.err_list
        )

        # 数値でない場合
        result = decimal_digits_check(
            "abc", "テスト項目", self.err_list, integer_digits=4, decimal_digits=2
        )
        self.assertFalse(result)
        self.assertIn(
            "テスト項目は半角数字（小数点OK）の形式で入力されていません。",
            self.err_list,
        )
        self.err_list.clear()

    def test_numeric_range_check(self):
        """数値範囲チェックのテスト"""

        # 最小値を下回る場合
        result = numeric_range_check(4, "テスト項目", self.err_list, min_value=5)
        self.assertFalse(result)
        self.assertIn("テスト項目は5以上で入力してください。", self.err_list)
        self.err_list.clear()

        # 最大値を超える場合
        result = numeric_range_check(6, "テスト項目", self.err_list, max_value=5)
        self.assertFalse(result)
        self.assertIn("テスト項目は5以下で入力してください。", self.err_list)
        self.err_list.clear()

        # 範囲内の場合
        result = numeric_range_check(
            5, "テスト項目", self.err_list, min_value=5, max_value=10
        )
        self.assertTrue(result)
        self.assertNotIn("テスト項目は5以上で入力してください。", self.err_list)
        self.assertNotIn("テスト項目は10以下で入力してください。", self.err_list)

        # 数値でない場合
        result = numeric_range_check(
            "abc", "テスト項目", self.err_list, min_value=5, max_value=10
        )
        self.assertFalse(result)
        # self.assertIn("テスト項目は半角数字の形式で入力されていません。", self.err_list)
        self.err_list.clear()

    def test_allowed_characters_check(self):
        """許可された文字のチェックのテスト"""

        # 半角数字が含まれている場合
        result = allowed_characters_check(
            "123", "テスト項目", self.err_list, allow_numeric=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には半角英数字が含まれています。", self.err_list)
        self.err_list.clear()

        # 半角小文字が含まれている場合
        result = allowed_characters_check(
            "abc", "テスト項目", self.err_list, allow_lowercase=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には半角小文字が含まれています。", self.err_list)
        self.err_list.clear()

        # 半角大文字が含まれている場合
        result = allowed_characters_check(
            "ABC", "テスト項目", self.err_list, allow_uppercase=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には半角大文字が含まれています。", self.err_list)
        self.err_list.clear()

        # 半角仮名が含まれている場合
        result = allowed_characters_check(
            "ｶﾀｶﾅ", "テスト項目", self.err_list, allow_kana=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には半角仮名が含まれています。", self.err_list)
        self.err_list.clear()

        # 半角スペースが含まれている場合
        result = allowed_characters_check(
            " ", "テスト項目", self.err_list, allow_space=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には半角スペースが含まれています。", self.err_list)
        self.err_list.clear()

        # 半角記号が含まれている場合
        result = allowed_characters_check(
            "!@#", "テスト項目", self.err_list, allow_symbols=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には半角記号が含まれています。", self.err_list)
        self.err_list.clear()

        # 改行が含まれている場合
        result = allowed_characters_check(
            "\n", "テスト項目", self.err_list, allow_newline=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には改行コードが含まれています。", self.err_list)
        self.err_list.clear()

        # 全角数字が含まれている場合
        result = allowed_characters_check(
            "１２３", "テスト項目", self.err_list, allow_fullwidth_numeric=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には全角数字が含まれています。", self.err_list)
        self.err_list.clear()

        # 全角小文字が含まれている場合
        result = allowed_characters_check(
            "ａｂｃ", "テスト項目", self.err_list, allow_fullwidth_lowercase=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には全角小文字が含まれています。", self.err_list)
        self.err_list.clear()

        # 全角大文字が含まれている場合
        result = allowed_characters_check(
            "ＡＢＣ", "テスト項目", self.err_list, allow_fullwidth_uppercase=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には全角大文字が含まれています。", self.err_list)
        self.err_list.clear()

        # 全角仮名が含まれている場合
        result = allowed_characters_check(
            "カタカナ", "テスト項目", self.err_list, allow_fullwidth_kana=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には全角仮名が含まれています。", self.err_list)
        self.err_list.clear()

        # 全角スペースが含まれている場合
        result = allowed_characters_check(
            "　", "テスト項目", self.err_list, allow_fullwidth_space=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には全角スペースが含まれています。", self.err_list)
        self.err_list.clear()

        # 全角記号が含まれている場合
        result = allowed_characters_check(
            "！＠＃", "テスト項目", self.err_list, allow_fullwidth_symbols=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には全角記号が含まれています。", self.err_list)
        self.err_list.clear()

        # 外部文字が含まれている場合
        result = allowed_characters_check(
            "", "テスト項目", self.err_list, allow_external_chars=False
        )
        self.assertFalse(result)
        self.assertIn("テスト項目には外部文字が含まれています。", self.err_list)
        self.err_list.clear()

        # 許可された文字のみが含まれている場合
        result = allowed_characters_check(
            "abc123",
            "テスト項目",
            self.err_list,
            allow_numeric=True,
            allow_lowercase=True,
        )
        self.assertTrue(result)
        self.assertEqual(len(self.err_list), 0)


if __name__ == "__main__":
    unittest.main()
