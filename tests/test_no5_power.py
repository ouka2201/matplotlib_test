"""仕様書No.5の月別最大電力、契約電力、数値ラベルとコメントを検証する。"""

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
from rendering.styles import format_number


class No5PowerTests(unittest.TestCase):
    """小数のkWhから換算したkWと、契約値の表示を照合する。"""

    def setUp(self):
        """各月の1枠だけを最大値にする、12か月の30分データを用意する。"""
        start, end, _ = bounds("2026-06")
        self.frame = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 2.0,
            }
        )
        self.months = pd.period_range("2025-07", "2026-06", freq="M")
        self.kwh = [
            100.5,
            200.7,
            150.25,
            90.1,
            100.2,
            50.0,
            70.3,
            60.1,
            80.3,
            100.0,
            55.5,
            100.8,
        ]
        self.config = {
            "target_month": "2026-06",
            "contract_kw": 39,
            "customer_name": "テスト会社",
            "address": "東京都",
            "customer_number": "000-000",
        }

    def context(self, kwh):
        """DB取得後と同じ換算値を各月に入れ、月別集計を作る。

        Args:
            kwh (list[float]): 12か月の月別最大の30分使用電力量。

        Returns:
            tuple[dict, dict]: 表示用contextとグラフ用series。
        """
        frame = self.frame.copy()
        for month, value in zip(self.months, kwh):
            stamp = month.start_time + pd.Timedelta(hours=19)
            # DBの既存処理と同じ、kWh×2の平均電力を渡す。
            frame.loc[frame.timestamp == stamp, "kw"] = value * 2
        return build_context(frame, self.config)

    def draw(self, series):
        """全No.を直接描画して、検証用のページFigureを作成する。

        Args:
            series (dict): 共通集計が返すグラフ用データ。

        Returns:
            matplotlib.figure.Figure: 描画結果。呼び出し側で閉じる。
        """
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            return draw_first_page(series, self.config)

    def test_monthly_maximum_preserves_unrounded_kw(self):
        """未丸めのkWh×2を月別最大値とし、期間とピーク月を確認する。"""
        context, series = self.context(self.kwh)
        self.assertEqual(
            series["monthly"]["max"].tolist(), [value * 2 for value in self.kwh]
        )
        self.assertEqual(series["monthly"].loc[pd.Period("2025-07"), "max"], 201)
        self.assertEqual(series["monthly"].loc[pd.Period("2025-08"), "max"], 401.4)
        self.assertEqual(context["power_peak_month"], "2025年08月")
        self.assertEqual(context["period"], "2025年07月〜2026年06月")

    def test_colors_labels_contract_line_legend_and_comments(self):
        """全月の値・色・数値ラベルと、kWの契約値の赤点線・凡例を確認する。"""
        _, series = self.context(self.kwh)
        fig = self.draw(series)
        try:
            ax = fig.axes[2]
            self.assertEqual(
                [bar.get_height() for bar in ax.patches],
                [value * 2 for value in self.kwh],
            )
            self.assertEqual(
                [bar.get_facecolor() for bar in ax.patches],
                [to_rgba("#e15759" if i == 1 else "#72a3c9") for i in range(12)],
            )
            self.assertEqual(
                [text.get_text() for text in ax.texts],
                [
                    "201",
                    "401.4",
                    "300.5",
                    "180.2",
                    "200.4",
                    "100",
                    "140.6",
                    "120.2",
                    "160.6",
                    "200",
                    "111",
                    "201.6",
                ],
            )
            line = ax.lines[0]
            self.assertEqual(list(line.get_ydata()), [39, 39])  # 契約値を2倍しない。
            self.assertEqual(line.get_color(), "#e15759")
            self.assertEqual(line.get_linestyle(), ":")
            self.assertEqual(line.get_label(), "契約電力")
            legend = ax.get_legend()
            self.assertEqual(
                [text.get_text() for text in legend.get_texts()], ["契約電力"]
            )
            self.assertEqual(legend.get_lines()[0].get_linestyle(), ":")
            self.assertEqual(legend.get_lines()[0].get_color(), "#e15759")
            self.assertEqual(ax.get_ylabel(), "電力(kW)")
            self.assertEqual(
                [text.get_text() for text in ax.get_xticklabels()],
                [str(month).replace("-", "/") for month in self.months],
            )
            texts = [text.get_text() for text in fig.axes[0].texts]
            self.assertIn("ピークは08月でした", texts)
            self.assertIn("次の08月に契約電力を\n超過しないよう気を付けましょう", texts)
        finally:
            plt.close(fig)

    def test_ties_choose_earlier_month_and_label_format(self):
        """最大値が同じ場合は早い月を選び、数値ラベルの端数と桁区切りを確認する。"""
        context, series = self.context([100.5] * 12)
        self.assertEqual(context["power_peak_month"], "2025年07月")
        fig = self.draw(series)
        try:
            self.assertEqual(fig.axes[2].patches[0].get_facecolor(), to_rgba("#e15759"))
            texts = [text.get_text() for text in fig.axes[0].texts]
            self.assertIn("次の07月に契約電力を\n超過しないよう気を付けましょう", texts)
        finally:
            plt.close(fig)
        for value, label in [
            (0.0, "0"),
            (1000.0, "1,000"),
            (1000.5, "1,000.5"),
            (1.25, "1.25"),
        ]:
            with self.subTest(value=value):
                self.assertEqual(format_number(value), label)
