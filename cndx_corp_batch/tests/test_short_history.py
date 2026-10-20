"""1年未満の実績をCSV・DB・集計・ページ描画まで検証する。"""

import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.data_service import validate_data, load_data, build_context
from services.database_source import expand_daily_rows, POINT, DATE, SLOTS
from rendering.pages.first_page import draw_first_page
from rendering.pages.second_page import draw_second_page
from rendering.sections.no6_duration import duration_axis


class ShortHistoryTests(unittest.TestCase):
    """実績期間の短縮と、欠測・実績なしを区別する。"""

    def setUp(self):
        """対象月と、ページ描画に必要な顧客情報を準備する。"""
        self.config = {
            "target_month": "2026-06",
            "contract_kw": 1600,
            "customer_name": "テスト会社",
            "address": "東京都",
            "customer_number": "000-000",
        }

    def frame(self, start, end):
        """指定期間の日別48枠を作る。終了日時は含めない。

        Args:
            start (str): 開始日。
            end (str): 終了日の翌日。

        Returns:
            pandas.DataFrame: 日時と100kWの時系列データ。
        """
        return pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 100.0,
            }
        )

    def test_quarter_csv_and_dynamic_months(self):
        """3か月だけのCSVを受け付け、月別棒・合計・期間を実績から求める。"""
        frame = self.frame("2026-04-01", "2026-07-01")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "short.csv"
            frame.to_csv(path, index=False)
            actual = load_data(path, "2026-06")
        context, series = build_context(actual, self.config)
        self.assertEqual(len(actual), 91 * 48)
        self.assertEqual(
            series["monthly"].index.astype(str).tolist(),
            ["2026-04", "2026-05", "2026-06"],
        )
        self.assertEqual(series["monthly"].kwh.sum(), frame.kw.sum() * 0.5)
        self.assertEqual(context["period"], "2026年04月〜2026年06月")
        self.assertEqual(context["actual_period"], "2026/04/01〜2026/06/30")
        self.assertFalse(context["has_full_year"])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            fig = draw_first_page(series, self.config)
        try:
            for ax in fig.axes[1:3]:
                self.assertEqual(len(ax.patches), 3)
                self.assertEqual(
                    [t.get_text() for t in ax.get_xticklabels()],
                    ["2026/04", "2026/05", "2026/06"],
                )
        finally:
            plt.close(fig)

    def test_one_day_and_less_than_fifty_records(self):
        """1日48枠でTOP48・50位なし・1日ロードカーブを描画する。"""
        frame = validate_data(self.frame("2026-06-30", "2026-07-01"), "2026-06")
        context, series = build_context(frame, self.config)
        self.assertEqual(context["top_count"], 48)
        self.assertEqual(context["top_label"], "TOP48")
        self.assertIsNone(context["rank50_row"])
        self.assertEqual(len(series["week"]), 48)
        for name in ("month_count", "weekday_count", "hour_count"):
            self.assertEqual(series[name].sum(), 48)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            fig = draw_second_page(series, self.config, context)
        try:
            texts = [t.get_text() for t in fig.axes[0].texts]
            self.assertIn("TOP48", texts)
            self.assertIn("における特徴", texts)
            self.assertIn("50位の実績なし（全48コマ）", texts)
            self.assertTrue(any("48コマ/日×1日=48コマ" in text for text in texts))
            self.assertTrue(any("当該日を含む1日間" in text for text in texts))
            # 最後のグラフはロードカーブ。実績の48枠だけを描く。
            self.assertEqual(len(fig.axes[-2].patches), 48)
        finally:
            plt.close(fig)

    def test_no_target_month_history(self):
        """対象月に実績がなくても、日別欄を実績なしとして両ページを描く。"""
        frame = validate_data(self.frame("2026-05-01", "2026-06-01"), "2026-06")
        context, series = build_context(frame, self.config)
        self.assertTrue(series["daily"].empty)
        self.assertTrue(series["day"].empty)
        self.assertEqual(context["daily_top"], [])
        self.assertIsNone(context["day_date"])
        self.assertEqual(context["period"], "2026年05月〜2026年05月")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            first = draw_first_page(series, self.config)
            second = draw_second_page(series, self.config, context)
        try:
            texts = [t.get_text() for t in first.axes[0].texts]
            self.assertIn("対象月の実績はありません", texts)
            self.assertEqual(texts.count("実績なし"), 30)
            self.assertTrue(any("日別グラフは表示しません" in t for t in texts))
            self.assertEqual(len(first.axes), 3)
        finally:
            plt.close(first)
            plt.close(second)

    def test_period_ends_during_target_month(self):
        """月の途中で実績が終わる場合も、実績のある日だけでTOP3を選ぶ。"""
        frame = validate_data(self.frame("2026-06-10", "2026-06-13"), "2026-06")
        context, series = build_context(frame, self.config)
        self.assertEqual(len(series["daily"]), 3)
        self.assertEqual(len(series["week"]), 144)
        self.assertEqual(context["actual_period"], "2026/06/10〜2026/06/12")
        self.assertEqual(
            [r["date"] for r in context["daily_top"]],
            ["2026/06/10（水）", "2026/06/11（木）", "2026/06/12（金）"],
        )
        cells = [cell for week in context["weeks"] for cell in week if cell]
        self.assertEqual(sum(cell["kw"] is None for cell in cells), 27)

    def test_week_energy_has_no_float_tail(self):
        """日別表の電力量に計算誤差の余分な桁が表示されないことを確認する。"""
        path = Path(__file__).resolve().parents[1] / "examples/sample_short.csv"
        frame = pd.read_csv(path, parse_dates=["timestamp"])
        frame = frame.loc[
            (frame.timestamp >= "2026-06-10") & (frame.timestamp < "2026-06-13")
        ]
        context, _ = build_context(validate_data(frame, "2026-06"), self.config)
        self.assertEqual(context["week_rows"][1]["kwh"], 15501.023)
        self.assertEqual(str(context["week_rows"][1]["kwh"]), "15501.023")

    def test_zero_power_is_history(self):
        """0kWの実績を、未取得日や空データと混同しない。"""
        frame = self.frame("2026-06-30", "2026-07-01")
        frame["kw"] = 0.0
        context, series = build_context(validate_data(frame, "2026-06"), self.config)
        self.assertEqual(context["day_peak_kw"], 0)
        self.assertEqual(context["daily_top"][0]["kw"], 0)
        self.assertEqual(series["monthly"].kwh.iloc[0], 0)

    def test_interior_missing_and_partial_days_rejected(self):
        """実績途中の欠落日・枠、開始日・終了日の不足枠は拒否する。"""
        frame = self.frame("2026-06-10", "2026-06-13")
        cases = [
            frame.drop(index=50),
            frame.drop(index=range(48, 96)),
            frame.iloc[1:],
            frame.iloc[:-1],
        ]
        for case in cases:
            with self.subTest(rows=len(case)), self.assertRaisesRegex(
                ValueError, "不完全"
            ):
                validate_data(case, "2026-06")

    def test_empty_or_outside_window_rejected(self):
        """取得対象内に実績が1件もない場合は明確なエラーを返す。"""
        for frame in (
            self.frame("2026-07-01", "2026-07-02"),
            self.frame("2026-06-01", "2026-06-02").iloc[:0],
        ):
            with self.assertRaisesRegex(ValueError, "実績データがありません"):
                validate_data(frame, "2026-06")
        with self.assertRaisesRegex(ValueError, "実績データがありません"):
            expand_daily_rows([], "2026-06", "0001")

    def test_short_daily_database_rows_and_internal_gap(self):
        """日別48列を短期間で展開し、kWh換算と期間途中の欠落日を確認する。"""
        rows = [
            {
                POINT: "0001",
                DATE: date.strftime("%Y%m%d"),
                **{slot: 1.5 for slot in SLOTS},
            }
            for date in pd.date_range("2026-06-10", periods=3, freq="D")
        ]
        frame = expand_daily_rows(rows, "2026-06", "0001")
        self.assertEqual(len(frame), 144)
        self.assertTrue((frame.kw == 3.0).all())
        context, series = build_context(frame, self.config)
        self.assertEqual(series["monthly"].kwh.iloc[0], 1.5 * 144)
        with self.assertRaisesRegex(ValueError, "欠損=48"):
            expand_daily_rows([rows[0], rows[2]], "2026-06", "0001")

    def test_duration_axis_small_and_empty_inputs(self):
        """46件未満は各実データを目盛りとし、空入力・不正な分割数を拒否する。"""
        frame = self.frame("2026-06-30", "2026-07-01").iloc[:10]
        ordered, ticks, labels = duration_axis(frame)
        self.assertEqual(len(ticks), 10)
        self.assertEqual(ticks.tolist(), list(range(1, 11)))
        self.assertEqual(
            labels, ordered.timestamp.dt.strftime("%Y/%m/%d %H:%M").tolist()
        )
        with self.assertRaises(ValueError):
            duration_axis(frame.iloc[:0])
        for segments in (0, -1, 1.5):
            with self.assertRaises(ValueError):
                duration_axis(frame, segments)
