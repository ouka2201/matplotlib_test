"""仕様書No.4の月間電力量、最小値の点線、順位とコメントを検証する。"""

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


class No4EnergyTests(unittest.TestCase):
    """③の月別kWhグラフを、原値の合計と仕様の表示条件で照合する。"""

    def setUp(self):
        """30分枠ごとの1.25kWhに相当する12か月の平均電力を用意する。"""
        start, end, _ = bounds("2026-06")
        self.frame = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 2.5,
            }
        )
        self.config = {
            "target_month": "2026-06",
            "contract_kw": 39,
            "customer_name": "テスト会社",
            "address": "東京都",
            "customer_number": "000-000",
        }

    def test_month_totals_keep_fractional_kwh(self):
        """48枠×日数の月合計に端数を保持し、年月順と最少月を確認する。"""
        self.frame.loc[
            self.frame.timestamp == pd.Timestamp("2026-06-01 00:00"), "kw"
        ] += 4.5
        context, series = build_context(self.frame, self.config)
        monthly = series["monthly"]
        self.assertEqual(monthly.loc[pd.Period("2025-07"), "kwh"], 31 * 48 * 1.25)
        self.assertEqual(
            monthly.loc[pd.Period("2026-06"), "kwh"], 30 * 48 * 1.25 + 2.25
        )
        self.assertEqual(monthly.kwh.sum(), self.frame.kw.sum() * 0.5)
        self.assertEqual(context["period"], "2025年07月〜2026年06月")
        self.assertEqual(context["energy_peak_month"], "2025年07月")
        self.assertEqual(context["energy_min_month"], "2026年02月")

    def draw(self, values):
        """月間値を指定し、グラフを含むページを実際の描画関数で作る。

        Args:
            values (list[float]): 年月順の12か月の使用電力量。

        Returns:
            matplotlib.figure.Figure: 検証用の1ページ目。呼び出し側で閉じる。
        """
        _, series = build_context(self.frame, self.config)
        series["monthly"]["kwh"] = values
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            return draw_first_page(series, self.config)

    def test_bar_colors_minimum_line_top3_and_comments(self):
        """平均と異なる最小値で点線を引き、仕様色・上位順位・月の文言を確認する。"""
        values = [300, 500, 400, 240, 220, 150, 270, 180, 100, 260, 250, 230]
        fig = self.draw(values)
        try:
            ax = fig.axes[1]
            self.assertEqual([bar.get_height() for bar in ax.patches], values)
            self.assertEqual(
                [bar.get_facecolor() for bar in ax.patches],
                [to_rgba("#e15759" if i == 1 else "#72a3c9") for i in range(12)],
            )
            self.assertEqual(len(ax.lines), 1)
            self.assertEqual(list(ax.lines[0].get_ydata()), [100, 100])
            self.assertEqual(ax.lines[0].get_linestyle(), ":")
            self.assertEqual(ax.lines[0].get_color(), "#72a3c9")
            self.assertEqual(
                [(t.get_text(), t.get_position()[0]) for t in ax.texts],
                [("第1位", 1), ("第2位", 2), ("第3位", 0)],
            )
            self.assertEqual(ax.get_ylabel(), "電力量(kWh)")
            self.assertEqual(
                [t.get_text() for t in ax.get_xticklabels()],
                [
                    str(p).replace("-", "/")
                    for p in pd.period_range("2025-07", "2026-06", freq="M")
                ],
            )
            texts = [t.get_text() for t in fig.axes[0].texts]
            self.assertIn("使用電力量が最も多かったのは\n08月でした。", texts)
            self.assertIn(
                "03月（青点線）を上回る使用電力量は\n空調による影響が大きいと思われます\n空調洗浄や高効率空調への更新が\n使用電力量削減につながります",
                texts,
            )
        finally:
            plt.close(fig)

    def test_equal_months_rank_by_earlier_month(self):
        """最多・最少が同値の月では早い年月を選び、順位は3か月だけ表示する。"""
        fig = self.draw([100] * 12)
        try:
            ax = fig.axes[1]
            self.assertEqual(
                [(t.get_text(), t.get_position()[0]) for t in ax.texts],
                [("第1位", 0), ("第2位", 1), ("第3位", 2)],
            )
            self.assertEqual(ax.patches[0].get_facecolor(), to_rgba("#e15759"))
            texts = [t.get_text() for t in fig.axes[0].texts]
            self.assertIn("使用電力量が最も多かったのは\n07月でした。", texts)
            self.assertTrue(any(t.startswith("07月（青点線）") for t in texts))
        finally:
            plt.close(fig)
