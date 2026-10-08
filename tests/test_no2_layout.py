"""No.2の48本の棒・配色・日時表記を仕様書と照合する。"""

from pathlib import Path
import sys
import unittest
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.data_service import bounds, build_context
from rendering.pages.first_page import draw_first_page


class No2LayoutTests(unittest.TestCase):
    """No.2の描画結果を、文字と棒のデータで検証する。"""

    def test_48_bars_colors_labels_and_midnight(self):
        """仕様色、0〜23の目盛り、曜日付き日付、日跨ぎのピーク表示を確認する。"""
        start, end, _ = bounds("2026-06")
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 10.0,
            }
        )
        df.loc[df.timestamp == pd.Timestamp("2026-06-30 23:30"), "kw"] = 30.0
        config = {
            "target_month": "2026-06",
            "contract_kw": 39,
            "customer_name": "テスト会社",
            "address": "東京都",
            "customer_number": "000-000",
        }
        _, series = build_context(df, config)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            fig = draw_first_page(series, config)
        try:
            ax = fig.axes[-1]
            self.assertEqual(len(ax.patches), 48)
            self.assertEqual(
                [bar.get_height() for bar in ax.patches], series["day"].kw.tolist()
            )
            self.assertEqual(
                [bar.get_facecolor() for bar in ax.patches[:-1]],
                [to_rgba("#72a3c9")] * 47,
            )
            self.assertEqual(ax.patches[-1].get_facecolor(), to_rgba("#e15759"))
            self.assertEqual(ax.get_ylabel(), "電力(kW)")
            self.assertEqual(
                [label.get_text() for label in ax.get_xticklabels()],
                [str(i) for i in range(24)],
            )
            text = [item.get_text() for item in fig.axes[0].texts]
            self.assertIn("30分ごとの需要電力の推移：2026年06月30日（火）", text)
            self.assertIn("最大電力は、23:30〜00:00に\n発生しています", text)
        finally:
            plt.close(fig)
