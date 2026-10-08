"""No.1の四捨五入、順位、カレンダーの仕様を検証する。"""

import calendar
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
from services.data_service import bounds, build_context, calendar_power
from rendering.canvas import FirstPageCanvas
from rendering.sections.no1_daily_maximum import draw_no1


class No1SpecTests(unittest.TestCase):
    """日別最大値の集計と、表示時の丸め・配置を確認する。"""

    def test_round_kwh_before_doubling(self):
        """100.5kWh→202kWを含め、四捨五入の順序と境界を確認する。"""
        for kwh, expected in [
            (0, 0),
            (0.49, 0),
            (0.5, 2),
            (100.49, 200),
            (100.5, 202),
            (101.5, 204),
        ]:
            with self.subTest(kwh=kwh):
                self.assertEqual(calendar_power(kwh * 2), expected)

    def test_rank_before_rounding_and_no2_keeps_raw_power(self):
        """同じ表示値でも元の最大値で順位を決め、No.2と月合計は丸めない。"""
        start, end, _ = bounds("2026-06")
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 10.0,
            }
        )
        df.loc[0, "kw"] = 400.0  # 指定月の外なのでNo.1の順位には含めない。
        for stamp, kw in [
            ("2026-06-01 09:00", 201.0),
            ("2026-06-02 10:00", 201.4),
            ("2026-06-02 10:30", 201.4),
            ("2026-06-03 08:00", 201.4),
        ]:
            df.loc[df.timestamp == pd.Timestamp(stamp), "kw"] = kw
        context, series = build_context(
            df, {"target_month": "2026-06", "contract_kw": 500}
        )
        self.assertEqual(
            [row["date"] for row in context["daily_top"]],
            ["2026/06/02（火）", "2026/06/03（水）", "2026/06/01（月）"],
        )
        self.assertEqual([row["kw"] for row in context["daily_top"]], [202, 202, 202])
        self.assertEqual(context["daily_top"][0]["time"], "10:00〜10:30")
        self.assertEqual(context["day_peak_time"], context["daily_top"][0]["time"])
        self.assertEqual(series["day"].kw.max(), 201.4)
        self.assertEqual(
            series["monthly"].loc[pd.Period("2026-06"), "kwh"],
            df.loc[df.timestamp >= pd.Timestamp("2026-06-01"), "kw"].sum() * 0.5,
        )
        cells = [cell for week in context["weeks"] for cell in week if cell]
        self.assertEqual(cells[0]["kw"], 202)

    def test_dynamic_rows_backgrounds_dates_and_rank_text(self):
        """4・5・6週の月で、曜日別の仕様色、MM/DD、TOP3の書式を確認する。"""
        for target_month, expected_rows in [
            ("2015-02", 4),
            ("2026-06", 5),
            ("2026-08", 6),
        ]:
            with self.subTest(target_month=target_month):
                month = pd.Timestamp(target_month + "-01")
                days = pd.date_range(
                    month, month + pd.DateOffset(months=1), freq="D", inclusive="left"
                )
                daily = pd.DataFrame(
                    {"timestamp": days + pd.Timedelta(hours=19), "kw": 201.0}
                )
                config = {
                    "target_month": target_month,
                    "holidays": [str(days[0].date())],
                }
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore", message="Glyph .* missing from font"
                    )
                    page = FirstPageCanvas()
                    draw_no1(page, daily, config)
                    fig = page.fig
                try:
                    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(
                        month.year, month.month
                    )
                    self.assertEqual(len(weeks), expected_rows)
                    # 先頭は丸印、次が7曜日。以降が日付セル、最後がTOP3背景。
                    cells = fig.axes[0].patches[8:-1]
                    self.assertEqual(len(cells), 7 * expected_rows)
                    for index, patch in enumerate(cells):
                        column = index % 7
                        color = (
                            "#ffd7de"
                            if column == 0
                            else "#e7f0fb" if column == 6 else "#f2f2f2"
                        )
                        self.assertEqual(patch.get_facecolor(), to_rgba(color))
                    texts = [item.get_text() for item in fig.axes[0].texts]
                    self.assertIn(f"{month.month:02d}/01", texts)
                    self.assertIn("202kW", texts)
                    weekday = "月火水木金土日"[month.weekday()]
                    self.assertIn(f"1位 1日（{weekday}） 19:00〜19:30 202kW", texts)
                    self.assertIn("TOP3は以下のとおりでした", texts)
                finally:
                    plt.close(fig)
