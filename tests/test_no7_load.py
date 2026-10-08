"""仕様書No.7の週選定、時間帯色、日別kWhと最大kWを検証する。"""

from pathlib import Path
import sys
import unittest
import warnings

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rendering.sections.no6_duration import duration_axis
from services.data_service import bounds, build_context, peak_week_bounds
from rendering.styles import DEFAULT_NOTES
from rendering.pages.second_page import draw_second_page


class No7LoadTests(unittest.TestCase):
    """通常週・期間端・7日未満と、昼休みを含む棒の値を確認する。"""

    def fixture(self):
        """1.25kWhの年間データに、同率の23:30ピークを2日分設定する。

        Returns:
            tuple: 設定、表示用context、描画用series。
        """
        start, end, _ = bounds("2026-06")
        # 入力はDB取得後のkW。1.25kWh×2=2.5kW。
        frame = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 2.5,
            }
        )
        frame.loc[
            frame.timestamp.isin(
                pd.to_datetime(["2026-06-19 23:30", "2026-06-20 23:30"])
            ),
            "kw",
        ] = (
            100.7 * 2
        )
        config = {"target_month": "2026-06", "contract_kw": 500, "issuer": "別の設定値"}
        context, series = build_context(frame, config)
        return config, context, series

    def test_week_bounds_normal_edges_exactly_seven_and_short_period(self):
        """日曜始まりを基本に、開始端・終了端・7日未満の範囲を確認する。"""
        cases = [
            ("2025-07-01", "2026-06-30", "2025-07-16", "2025-07-13", "2025-07-20"),
            ("2025-07-01", "2026-06-30", "2025-07-02", "2025-07-01", "2025-07-08"),
            ("2025-07-01", "2026-06-30", "2026-06-30", "2026-06-24", "2026-07-01"),
            ("2025-07-01", "2025-07-07", "2025-07-04", "2025-07-01", "2025-07-08"),
            ("2025-07-01", "2025-07-03", "2025-07-02", "2025-07-01", "2025-07-04"),
        ]
        for first, last, peak, expected_start, expected_end in cases:
            with self.subTest(first=first, last=last, peak=peak):
                frame = pd.DataFrame(
                    {
                        "timestamp": pd.date_range(
                            first,
                            pd.Timestamp(last) + pd.Timedelta(days=1),
                            freq="30min",
                            inclusive="left",
                        )
                    }
                )
                self.assertEqual(
                    peak_week_bounds(frame, pd.Timestamp(peak)),
                    (pd.Timestamp(expected_start), pd.Timestamp(expected_end)),
                )

    def test_week_rows_preserve_energy_and_converted_power(self):
        """元kWhの48枠合計と換算後の最大kWを、端数を保持して照合する。"""
        _, context, series = self.fixture()
        self.assertEqual(context["week_period"], "2026年06月14日〜2026年06月20日")
        self.assertEqual(len(series["week"]), 336)
        self.assertEqual(series["week"].timestamp.iloc[0], pd.Timestamp("2026-06-14"))
        self.assertTrue(series["week"].timestamp.is_monotonic_increasing)
        self.assertEqual(len(context["week_rows"]), 7)
        self.assertEqual(
            context["week_rows"][0],
            {"date": "2026/06/14（日）", "kwh": 60.0, "kw": 2.5},
        )
        peak_row = context["week_rows"][5]
        self.assertAlmostEqual(peak_row["kwh"], 47 * 1.25 + 100.7)
        self.assertEqual(peak_row["kw"], 201.4)

    def test_load_colors_dates_table_and_specification_notes(self):
        """全336枠の色、唯一の1位、上側日時、表の端数と注記全文を確認する。"""
        config, context, series = self.fixture()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            fig = draw_second_page(series, config, context, duration_axis(series["df"]))
        try:
            ax = fig.axes[7]
            self.assertEqual(len(ax.patches), 336)
            self.assertEqual(
                [bar.get_height() for bar in ax.patches], series["week"].kw.tolist()
            )
            peak = pd.Timestamp("2026-06-19 23:30")
            for bar, timestamp in zip(ax.patches, series["week"].timestamp):
                # 全枠を確認することで07:30/08:00、11:30/12:00、12:30/13:00、17:30/18:00を含む。
                expected = (
                    "#e15759"
                    if timestamp == peak
                    else (
                        "#f28e2b"
                        if 8 <= timestamp.hour < 12 or 13 <= timestamp.hour < 18
                        else "#72a3c9"
                    )
                )
                self.assertEqual(bar.get_facecolor(), to_rgba(expected))
            self.assertEqual(
                sum(bar.get_facecolor() == to_rgba("#e15759") for bar in ax.patches), 1
            )
            self.assertEqual(ax.xaxis.get_ticks_position(), "top")
            self.assertEqual(
                [item.get_text() for item in ax.get_xticklabels()],
                ["0", "6", "12", "18"] * 7,
            )
            self.assertEqual(ax.texts[0].get_text(), "2026/06/14（日）")
            self.assertEqual(ax.texts[-1].get_text(), "2026/06/20（土）")
            cells = fig.axes[8].tables[0].get_celld()
            self.assertEqual(len(cells), 24)
            self.assertEqual(
                [cells[0, col].get_text().get_text() for col in range(3)],
                ["年月日", "電力量(kWh)", "最大電力(kW)"],
            )
            self.assertEqual(
                [cells[6, col].get_text().get_text() for col in range(3)],
                ["2026/06/19（金）", "159.45", "201.4"],
            )
            texts = [item.get_text() for item in fig.axes[0].texts]
            self.assertIn(
                "ピークは、06月19日23:30〜00:00に発生しています\n当該日を含む一週間の電力の使い方に注目してください",
                texts,
            )
            self.assertTrue(any("48コマ/日×7日=336コマ" in item for item in texts))
            self.assertTrue(
                any(
                    "特に太陽光発電システムの導入が効果的です" in item for item in texts
                )
            )
            self.assertIn(DEFAULT_NOTES, [item.replace("\n", "") for item in texts])
            self.assertIn("発行元：東京電力エナジーパートナー株式会社", texts)
        finally:
            plt.close(fig)
