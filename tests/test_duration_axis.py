import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rendering.sections.no6_duration import duration_axis


class DurationAxisTests(unittest.TestCase):
    """デュレーションカーブの並び順と中央日時選定を確認するテスト。"""

    def test_46_labels_keep_power_timestamp_pairing(self):
        """46区間の中央日時と電力の対応、および分割件数の均等性を確認する。"""
        dates = pd.date_range("2025-07-01", periods=17520, freq="30min")
        # 入力順とは異なる電力順で日時との対応を確認する。
        df = pd.DataFrame({"timestamp": dates, "kw": np.arange(len(dates))[::-1]})
        ordered, ticks, labels = duration_axis(df)
        self.assertEqual(len(ticks), 46)
        self.assertEqual(len(labels), 46)
        groups = np.array_split(np.arange(len(df)), 46)
        self.assertLessEqual(max(map(len, groups)) - min(map(len, groups)), 1)
        for group, tick, label in zip(groups, ticks, labels):
            center = group[(len(group) - 1) // 2]
            self.assertEqual(tick, center + 1)
            self.assertEqual(label, dates[center].strftime("%Y/%m/%d %H:%M"))
        self.assertTrue(ordered.kw.is_monotonic_decreasing)

    def test_ties_use_earlier_timestamp(self):
        """同じ電力値では日時の早い枠を優先することを確認する。"""
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2026-01-03", "2026-01-01", "2026-01-02"]),
                "kw": [100, 100, 100],
            }
        )
        ordered, ticks, labels = duration_axis(df, segments=1)
        self.assertTrue(ordered.timestamp.is_monotonic_increasing)
        self.assertEqual(labels, ["2026/01/02 00:00"])
        self.assertEqual(ticks.tolist(), [2])

    def test_even_segment_uses_left_middle(self):
        """偶数件の区間では中央2枠の左側を選ぶことを確認する。"""
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-01-01", periods=4, freq="30min"),
                "kw": [400, 300, 200, 100],
            }
        )
        _, ticks, labels = duration_axis(df, segments=1)
        self.assertEqual(ticks.tolist(), [2])
        self.assertEqual(labels, ["2026/01/01 00:30"])


if __name__ == "__main__":
    unittest.main()
