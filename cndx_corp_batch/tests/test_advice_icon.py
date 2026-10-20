"""ICON.pngのサイズ・透過・再利用と、両ページへの配置を検証する。"""

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
from rendering import icons
from rendering.canvas import FirstPageCanvas, SecondPageCanvas


class AdviceIconTests(unittest.TestCase):
    """実際のPNGを使い、図形から画像への変更による不具合を確認する。"""

    def setUp(self):
        """運用画像と独立した90×89の透過PNGを一時フォルダーに作る。"""
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
        """透過を保持し、2回目以降はファイルを読み直さない。"""
        first = icons.load_advice_icon()
        self.assertEqual(first.shape, (89, 90, 4))
        self.assertEqual(first[0, 0, 3], 0)
        self.assertEqual(first[20, 20, 3], 1)
        self.path.unlink()
        self.assertIs(icons.load_advice_icon(), first)

    def test_missing_png_has_actionable_error(self):
        """画像がない場合は必要なファイル名・サイズ・配置先を示す。"""
        self.path.unlink()
        with self.assertRaises(FileNotFoundError) as caught:
            icons.load_advice_icon()
        self.assertIn("90×89", str(caught.exception))
        self.assertIn(str(self.path), str(caught.exception))

    def test_wrong_size_is_rejected(self):
        """幅と高さが逆の場合も、不正サイズとして明確に拒否する。"""
        Image.new("RGBA", (89, 90)).save(self.path)
        with self.assertRaisesRegex(ValueError, "現在のサイズ: 幅89×高さ90"):
            icons.load_advice_icon()

    def test_both_pages_use_png_without_changing_canvas(self):
        """両ページの青い枠に画像を配置し、mm座標と元の縦横比を保つ。"""
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
        """黄色い結果欄は画像を読み込まず、PNGがなくても描画できる。"""
        self.path.unlink()
        for canvas_class in (FirstPageCanvas, SecondPageCanvas):
            page = canvas_class()
            page.note(20, 30, 50, 20, ["Result"])
            self.assertEqual(len(page.canvas.images), 0)
            plt.close(page.fig)
