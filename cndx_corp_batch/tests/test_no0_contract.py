"""No.0がページへ直接描画され、契約値が領域に収まることを検証する。"""

from pathlib import Path
import sys
import unittest
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rendering.canvas import FirstPageCanvas
from rendering.sections.no0_contract import draw_no0


class No0ContractTests(unittest.TestCase):
    """同じFigureへの描画と、長い契約情報の扱いを確認する。"""

    def setUp(self):
        """既存ページと、契約情報4項目を準備する。"""
        self.page = FirstPageCanvas()
        self.config = {
            "customer_name": "テスト会社",
            "address": "東京都",
            "customer_number": "000-000",
            "contract_kw": 1600,
        }

    def tearDown(self):
        """検証用のページFigureを閉じる。"""
        plt.close(self.page.fig)

    def test_contract_texts_drawn_on_existing_page(self):
        """Figure・Axes・部品画像を増やさず、4項目を描画する。"""
        figures = set(plt.get_fignums())
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            draw_no0(self.page, self.config)
        self.assertEqual(set(plt.get_fignums()), figures)
        self.assertEqual(len(self.page.fig.axes), 1)
        self.assertEqual(len(self.page.canvas.images), 0)
        texts = [text.get_text() for text in self.page.canvas.texts]
        for value in [
            "電力使用状況見える化レポート",
            "テスト会社",
            "東京都",
            "000-000",
            "1,600kW",
        ]:
            self.assertIn(value, texts)
        self.assertEqual(tuple(self.page.canvas.get_xlim()), (0, 281))
        self.assertEqual(tuple(self.page.canvas.get_ylim()), (194, 0))

    def test_long_contract_value_does_not_close_shared_figure(self):
        """収まらない値はエラーにし、ページの終了処理は呼び出し側に任せる。"""
        self.config["address"] = "W" * 500
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            with self.assertRaisesRegex(ValueError, "契約情報が長すぎます"):
                draw_no0(self.page, self.config)
        self.assertTrue(plt.fignum_exists(self.page.fig.number))
