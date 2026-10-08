import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.data_service import bounds, build_context, load_data


class DataTests(unittest.TestCase):
    """電力データの入力検証と帳票用集計を確認するテスト。"""

    def setUp(self):
        """検証用の12か月分の一定電力データと設定を用意する。"""
        start, end, _ = bounds("2026-06")
        self.df = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 100.0,
            }
        )
        self.config = {"target_month": "2026-06", "contract_kw": 1600, "holidays": []}

    def read(self, df):
        """DataFrameを一時CSV経由で読み込み、入力検証を実行する。

        Args:
            df (pandas.DataFrame): timestamp（30分枠の開始日時）とkw（平均電力）を持つデータ。

        Returns:
            pandas.DataFrame: load_dataによる検証済みデータ。

        Raises:
            ValueError: 入力検証に失敗した場合。
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.csv"
            df.to_csv(path, index=False)
            return load_data(path, "2026-06")

    def test_energy_units_and_ties(self):
        """kWhへの換算、日・週・TOP50の件数、同値時の順位を確認する。"""
        context, series = build_context(self.read(self.df), self.config)
        self.assertEqual(
            series["monthly"].loc[pd.Period("2026-06"), "kwh"], 100 * 24 * 30
        )
        self.assertEqual(len(series["day"]), 48)
        self.assertEqual(len(series["week"]), 336)
        self.assertEqual(len(series["top"]), 50)
        self.assertEqual(series["top"].timestamp.iloc[0], self.df.timestamp.iloc[0])
        for key in ["month_count", "weekday_count", "hour_count"]:
            self.assertEqual(series[key].sum(), 50)
        self.assertEqual(context["count"], 17520)

    def test_leap_year(self):
        """うるう日を含む12か月の30分枠数を確認する。"""
        start, end, _ = bounds("2024-06")
        self.assertEqual(
            len(pd.date_range(start, end, freq="30min", inclusive="left")), 17568
        )

    def test_no2_uses_no1_first_rank_in_target_month(self):
        """No.2が年間ピークではなく、No.1の1位の日と時間を使うことを確認する。"""
        self.df.loc[0, "kw"] = 1000  # 年間ピークは指定月の外。
        stamp = pd.Timestamp("2026-06-19 19:00")
        self.df.loc[self.df.timestamp == stamp, "kw"] = 200
        context, series = build_context(self.df, self.config)
        self.assertEqual(series["day"].timestamp.iloc[0], stamp.normalize())
        self.assertEqual(len(series["day"]), 48)
        self.assertEqual(context["day_date"], context["daily_top"][0]["date"])
        self.assertEqual(context["day_peak_time"], context["daily_top"][0]["time"])
        self.assertEqual(context["day_peak_kw"], context["daily_top"][0]["kw"])

    def test_no2_ties_use_earliest_day_and_frame(self):
        """同値時にNo.1とNo.2が最も早い日・30分枠を採用することを確認する。"""
        peaks = pd.to_datetime(
            ["2026-06-01 10:00", "2026-06-01 10:30", "2026-06-02 09:00"]
        )
        self.df.loc[self.df.timestamp.isin(peaks), "kw"] = 200
        context, series = build_context(self.df, self.config)
        self.assertEqual(series["day"].timestamp.iloc[0], pd.Timestamp("2026-06-01"))
        self.assertEqual(context["day_peak_time"], "10:00〜10:30")
        self.assertEqual(context["day_peak_time"], context["daily_top"][0]["time"])

    def test_missing_is_rejected(self):
        """30分枠が欠けたCSVを拒否することを確認する。"""
        with self.assertRaisesRegex(ValueError, "欠損=1"):
            self.read(self.df.drop(index=20))

    def test_duplicate_is_rejected(self):
        """同じ開始日時が重複するCSVを拒否することを確認する。"""
        with self.assertRaisesRegex(ValueError, "重複"):
            self.read(pd.concat([self.df, self.df.iloc[[0]]]))

    def test_negative_is_rejected(self):
        """負の電力値があるCSVを拒否することを確認する。"""
        self.df.loc[0, "kw"] = -1
        with self.assertRaises(ValueError):
            self.read(self.df)

    def test_peak_at_end_keeps_week_in_range(self):
        """期間末尾にピークがあっても対象週が期間内に収まることを確認する。"""
        self.df.loc[self.df.index[-1], "kw"] = 200
        context, series = build_context(self.df, self.config)
        self.assertEqual(len(series["week"]), 336)
        self.assertEqual(series["week"].timestamp.iloc[-1], self.df.timestamp.iloc[-1])
        self.assertEqual(context["peak_time"], "23:30〜00:00")


if __name__ == "__main__":
    unittest.main()
