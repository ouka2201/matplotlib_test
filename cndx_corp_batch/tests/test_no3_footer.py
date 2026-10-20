"""No.3の画像貼り付けと、注記・部分太字・文字領域を検証する。"""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rendering.canvas import FirstPageCanvas
from rendering.sections.no3_footer import draw_no3, load_footer_logo


class No3FooterTests(unittest.TestCase):
    """仕様書の注記を全文表示し、太字と画像が領域に収まることを確認する。"""

    def test_logo_note_emphasis_and_bounds(self):
        """ロゴの縦横比、注記全文、強調箇所と実描画のはみ出しを確認する。"""
        page = FirstPageCanvas()
        fig, ax = page.fig, page.canvas
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="Glyph .* missing from font")
                draw_no3(page, {})
                fig.canvas.draw()
            self.assertEqual(len(ax.images), 1)
            extent = ax.images[0].get_extent()
            logo = ax.images[0].get_array()
            self.assertAlmostEqual(
                (extent[2] - extent[3]) / (extent[1] - extent[0]),
                logo.shape[0] / logo.shape[1],
            )
            self.assertLessEqual(extent[2], 194)
            self.assertEqual(
                "".join(t.get_text() for t in ax.texts),
                "最大電力とは30分ごとの需要電力の最大値のことです。また、使用電力量とは"
                "30分ごとの使用電力量を対象期間（月初〜月末）において合計した値のことです。"
                "この対象期間は、料金の算定期間とは異なる場合がありますのでご留意ください。",
            )
            self.assertEqual(
                "".join(t.get_text() for t in ax.texts if t.get_fontweight() == "bold"),
                "料金の算定期間とは異なる場合があります",
            )
            renderer = fig.canvas.get_renderer()
            left, bottom = ax.transData.transform((56.3, 192.8))
            right, top = ax.transData.transform((139.4, 183.8))
            for artist in ax.texts:
                box = artist.get_window_extent(renderer)
                self.assertGreaterEqual(box.x0, left - 1)
                self.assertLessEqual(box.x1, right + 1)
                self.assertGreaterEqual(box.y0, bottom - 1)
                self.assertLessEqual(box.y1, top + 1)
        finally:
            plt.close(fig)

    def test_logo_is_loaded_once_and_cached(self):
        """プロセス内でロゴを一度だけ読み込み、画像ファイルの生成をしない。"""
        load_footer_logo.cache_clear()
        original = Path.read_bytes
        calls = []

        def read(path):
            """ロゴ読み込みの回数を記録して、元のPNGバイト列を返す。

            Args:
                path (pathlib.Path): 読み込む画像ファイル。

            Returns:
                bytes: ファイルの内容。
            """
            calls.append(path)
            return original(path)

        with patch.object(Path, "read_bytes", read), patch.object(
            Path, "write_bytes", side_effect=AssertionError("disk write")
        ):
            first = load_footer_logo()
            second = load_footer_logo()
        self.assertIs(first, second)
        self.assertEqual(len(calls), 1)
