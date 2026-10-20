import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cndx_corp_batch.domains.generate_all_power_report.services.data_service import (
    bounds,
    build_context,
    validate_data,
)


def load_data(path, target_month):
    """旧CSV入力用ヘルパーから、現行のDataFrame検証処理を呼び出す。"""
    return validate_data(pd.read_csv(path), target_month)


class DataTests(unittest.TestCase):
    """電力データの入力検証と帳票用集計を確認する。"""

    def setUp(self):
        """検証に使う12か月分の一定電力データと設定を用意する。"""
        start, end, _ = bounds("2026-06")
        self.df = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, end, freq="30min", inclusive="left"),
                "kw": 100.0,
            }
        )
        self.config = {"target_month": "2026-06", "contract_kw": 1600, "holidays": []}

    def read(self, df):
        """DataFrameを一時CSVに書き出して読み戻し、入力検証を実行する。

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
        self.df.loc[0, "kw"] = 1000  # 年間ピークは対象月の外に設定する。
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

    def test_missing_frame_is_kept_as_partial_history(self):
        """現行仕様どおり、欠けた30分枠を補完せず取得済みのデータだけを扱う。"""
        actual = self.read(self.df.drop(index=20))
        self.assertEqual(len(actual), len(self.df) - 1)

    def test_duplicate_frame_is_kept_without_silent_deduplication(self):
        """重複行を自動削除せず、入力件数をそのまま保持することを確認する。"""
        actual = self.read(pd.concat([self.df, self.df.iloc[[0]]]))
        self.assertEqual(len(actual), len(self.df) + 1)

    def test_negative_value_is_preserved_for_upstream_validation(self):
        """負の値の業務判定を上流に任せ、変換処理では値を保持する。"""
        self.df.loc[0, "kw"] = -1
        self.assertEqual(self.read(self.df).kw.iloc[0], -1)

    def test_peak_at_end_keeps_week_in_range(self):
        """期間末尾にピークがあっても対象週が期間内に収まることを確認する。"""
        self.df.loc[self.df.index[-1], "kw"] = 200
        context, series = build_context(self.df, self.config)
        self.assertEqual(len(series["week"]), 336)
        self.assertEqual(series["week"].timestamp.iloc[-1], self.df.timestamp.iloc[-1])
        self.assertEqual(context["peak_time"], "23:30〜00:00")


if __name__ == "__main__":
    unittest.main()
