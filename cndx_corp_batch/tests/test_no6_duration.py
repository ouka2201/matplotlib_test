"""仕様書No.6の順位表、TOP50集計、表示と年間コマ数を検証する。"""

from pathlib import Path
import sys
import unittest
import warnings

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rendering.sections.no6_duration import duration_axis
from services.data_service import bounds, build_context, most_common_labels
from rendering.pages.second_page import draw_second_page


class No6DurationTests(unittest.TestCase):
    """同値・0時台・日跨ぎ・うるう年を含めて帳票の値を照合する。"""

    def fixture(self, month="2026-06"):
        """1年分のデータに、同値の50枠と23:30の年間ピークを設定する。

        Args:
            month (str): レポートの対象年月（YYYY-MM）。

        Returns:
            tuple: 設定、表示用context、グラフ用series。
        """
        start, end, _ = bounds(month)
        frame = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 2.0,
            }
        )
        # 00:00と00:30の50枠を作る。kWhからの換算後の小数kWを渡す。
        for day in range(25):
            for minute in (0, 30):
                stamp = start + pd.Timedelta(days=day, minutes=minute)
                frame.loc[frame.timestamp == stamp, "kw"] = 201.4
        frame.loc[frame.timestamp == end - pd.Timedelta(minutes=30), "kw"] = 401.7
        config = {"target_month": month, "contract_kw": 500}
        context, series = build_context(
            frame.sample(frac=1, random_state=6)
            .sort_values("timestamp")
            .reset_index(drop=True),
            config,
        )
        return config, context, series

    def draw(self, config, context, series):
        """日本語フォントの警告を除き、2ページ目をメモリ上へ描く。

        Args:
            config (dict): レポートの設定。
            context (dict): 表示用の集計値。
            series (dict): 検証済みのグラフ用データ。

        Returns:
            matplotlib.figure.Figure: 描画結果。呼び出し側で閉じる。
        """
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Glyph .* missing from font")
            return draw_second_page(
                series, config, context, duration_axis(series["df"])
            )

    def test_rank50_matches_unrounded_top50_and_midnight_hour(self):
        """50位を同じTOP50から選び、同値の日時順・小数・0時台を確認する。"""
        _, context, series = self.fixture()
        self.assertEqual(len(series["top"]), 50)
        self.assertEqual(
            context["top_rows"][0],
            {"rank": 1, "date": "2026/06/30（火）", "time": "23:30", "kw": 401.7},
        )
        self.assertEqual(context["top_rows"][1]["date"], "2025/07/01（火）")
        self.assertEqual(context["top_rows"][1]["time"], "00:00")
        self.assertEqual(context["top_rows"][2]["time"], "00:30")
        self.assertEqual(
            context["rank50_row"],
            {"rank": 50, "date": "2025/07/25（金）", "time": "00:00", "kw": 201.4},
        )
        self.assertEqual(series["hour_count"].loc[0], 49)
        self.assertEqual(series["hour_count"].loc[23], 1)
        self.assertEqual(context["top_hours"], "00時")
        for key in ("month_count", "weekday_count", "hour_count"):
            self.assertEqual(series[key].sum(), 50)

    def test_same_count_features_use_display_order_and_three_labels(self):
        """4件同率でも先頭3件だけを半角スペースでつなぐ。"""
        counts = pd.Series([5, 5, 1, 5, 5], index=[23, 0, 1, 2, 3])
        self.assertEqual(
            most_common_labels(counts, {i: f"{i:02d}時" for i in counts.index}),
            "23時 00時 02時",
        )
        counts.loc[1] = 6
        self.assertEqual(
            most_common_labels(counts, {i: f"{i:02d}時" for i in counts.index}), "01時"
        )

    def test_tables_colors_axes_and_midnight_peak_message(self):
        """表の列・50位の独立行、グラフの色と46日時、日跨ぎ文を確認する。"""
        config, context, series = self.fixture()
        fig = self.draw(config, context, series)
        try:
            top_table = fig.axes[2].tables[0].get_celld()
            rank50_table = fig.axes[3].tables[0].get_celld()
            self.assertEqual(len(top_table), 44)  # 見出し＋10行、各4列。
            self.assertEqual(
                [top_table[0, i].get_text().get_text() for i in range(4)],
                ["順位", "年月日", "時分", "電力(kW)"],
            )
            self.assertEqual(top_table[1, 3].get_text().get_text(), "401.7")
            self.assertEqual(len(rank50_table), 4)  # 50位の行には見出しを付けない。
            self.assertEqual(
                [rank50_table[0, i].get_text().get_text() for i in range(4)],
                ["50", "2025/07/25（金）", "00:00", "201.4"],
            )
            self.assertEqual(len(fig.axes[1].get_xticklabels()), 46)
            for ax, key in zip(
                fig.axes[4:7], ("month_count", "weekday_count", "hour_count")
            ):
                counts = series[key]
                self.assertEqual(
                    [bar.get_height() for bar in ax.patches], counts.tolist()
                )
                self.assertEqual(
                    [bar.get_facecolor() for bar in ax.patches],
                    [
                        to_rgba("#e15759" if count == counts.max() else "#72a3c9")
                        for count in counts
                    ],
                )
                self.assertEqual(ax.get_ylabel(), "発生回数")
            self.assertEqual(fig.axes[4].get_xticklabels()[0].get_text(), "07月")
            self.assertEqual(fig.axes[6].get_xticklabels()[0].get_text(), "0")
            texts = [item.get_text() for item in fig.axes[0].texts]
            self.assertIn("ピークは、06月30日23:30〜00:00に発生しています", texts)
            self.assertTrue(any("48コマ/日×365日=17,520コマ" in item for item in texts))
            self.assertTrue(
                any("基本料金の低減につながります" in item for item in texts)
            )
        finally:
            plt.close(fig)

    def test_leap_year_description_uses_17568_frames(self):
        """366日の取得期間では17,568コマの説明文を表示する。"""
        config, context, series = self.fixture("2024-06")
        self.assertEqual(len(series["df"]), 17568)
        fig = self.draw(config, context, series)
        try:
            texts = [item.get_text() for item in fig.axes[0].texts]
            self.assertTrue(any("48コマ/日×366日=17,568コマ" in item for item in texts))
        finally:
            plt.close(fig)
