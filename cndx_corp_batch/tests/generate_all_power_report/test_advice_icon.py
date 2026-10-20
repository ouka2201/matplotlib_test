"""ICON.pngのサイズ・透過状態・再利用と、両ページへの配置を検証する。"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cndx_corp_batch.domains.generate_all_power_report.rendering import icons
from cndx_corp_batch.domains.generate_all_power_report.rendering.canvas import (
    FirstPageCanvas,
    SecondPageCanvas,
)


class AdviceIconTests(unittest.TestCase):
    """実際のPNGを使い、図形から画像へ変更した影響を確認する。"""

    def setUp(self):
        """実際の運用画像とは別に、90×89ピクセルの透過PNGを一時フォルダーへ作成する。"""
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "ICON.png"
        pixels = np.zeros((89, 90, 4), dtype=np.uint8)
        pixels[10:80, 10:80] = (75, 158, 192, 255)
        Image.fromarray(pixels).save(self.path)
        self.patcher = patch.object(icons, "ICON_PATH", self.path)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        icons.load_advice_icon.cache_clear()
        self.addCleanup(icons.load_advice_icon.cache_clear)
        self.addCleanup(plt.close, "all")

    def test_png_alpha_and_cache(self):
        """透過状態を保持し、2回目以降はファイルを読み直さないことを確認する。"""
        first = icons.load_advice_icon()
        self.assertEqual(first.shape, (89, 90, 4))
        self.assertEqual(first[0, 0, 3], 0)
        self.assertEqual(first[20, 20, 3], 1)
        self.path.unlink()
        self.assertIs(icons.load_advice_icon(), first)

    def test_missing_png_has_actionable_error(self):
        """画像がない場合に、必要なファイル名・サイズ・配置先を示すことを確認する。"""
        self.path.unlink()
        with self.assertRaises(FileNotFoundError) as caught:
            icons.load_advice_icon()
        self.assertIn("90×89", str(caught.exception))
        self.assertIn(str(self.path), str(caught.exception))

    def test_wrong_size_is_rejected(self):
        """幅と高さが入れ替わっている場合も、不正なサイズとして拒否することを確認する。"""
        Image.new("RGBA", (89, 90)).save(self.path)
        with self.assertRaisesRegex(ValueError, "現在のサイズ: 幅89×高さ90"):
            icons.load_advice_icon()

    def test_both_pages_use_png_without_changing_canvas(self):
        """両ページの青い枠に画像を配置し、mm座標と元画像の縦横比を維持することを確認する。"""
        for canvas_class in (FirstPageCanvas, SecondPageCanvas):
            with self.subTest(page=canvas_class.__name__):
                page = canvas_class()
                before = (page.canvas.get_xlim(), page.canvas.get_ylim())
                page.note(20, 30, 50, 20, ["Advice"], advice=True)
                self.assertEqual(len(page.canvas.images), 1)
                image = page.canvas.images[0]
                self.assertEqual(image.get_array().shape, (89, 90, 4))
                left, right, bottom, top = image.get_extent()
                self.assertAlmostEqual((right - left) / (bottom - top), 90 / 89)
                self.assertLess(left, 20)
                self.assertLess(top, 30)
                self.assertGreater(bottom, 30)
                self.assertEqual(image.origin, "upper")
                self.assertEqual((page.canvas.get_xlim(), page.canvas.get_ylim()), before)
                plt.close(page.fig)

    def test_yellow_note_does_not_require_icon(self):
        """黄色い結果欄では画像を読み込まず、PNGがなくても描画できることを確認する。"""
        self.path.unlink()
        for canvas_class in (FirstPageCanvas, SecondPageCanvas):
            page = canvas_class()
            page.note(20, 30, 50, 20, ["Result"])
            self.assertEqual(len(page.canvas.images), 0)
            plt.close(page.fig)
