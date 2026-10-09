"""日別48列の変換とDBの供給地点・期間条件を検証する。"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from sqlalchemy import Column, MetaData, Table, String, Integer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.database_source import (
    DatabaseSource,
    expand_daily_rows,
    POINT,
    DATE,
    SLOTS,
    CONTRACT_POINT,
    CONTRACT_POWER,
)
from services.data_service import bounds, build_context


def daily_rows(month="2026-06", point="0000000000000000000001"):
    """全日付に1〜48kWを持つ日別テスト行を作る。

    Args:
        month (str): 最終対象月。
        point (str): 供給地点特定番号。

    Returns:
        list[dict]: 日別の物理列を持つレコード。
    """
    start, end, _ = bounds(month)
    return [
        {
            POINT: point,
            DATE: date.strftime("%Y%m%d"),
            **{c: str(i + 1) for i, c in enumerate(SLOTS)},
        }
        for date in pd.date_range(start, end, freq="D", inclusive="left")
    ]


class DatabaseSourceTests(unittest.TestCase):
    """CSVを介さないテーブル取得と日時変換を確認する。"""

    def test_postgresql_uses_psycopg2_and_preserves_connection_settings(self):
        """旧URLもPsycopg2を選び、認証情報等を保持して接続をまだ開かない。"""
        import psycopg2

        for driver in ("postgresql", "postgresql+psycopg", "postgresql+psycopg2"):
            # 全て検証用の値。実DBへ接続するテストではない。
            url = f"{driver}://seed_test:p%40ss%2Fword@127.0.0.1:5432/test_database?sslmode=require"
            with self.subTest(driver=driver), patch.dict(
                os.environ, {"REPORT_DRIVER_TEST_URL": url}
            ), patch.object(
                psycopg2, "connect", side_effect=AssertionError("Must not connect")
            ) as connect:
                source = DatabaseSource({"url_env": "REPORT_DRIVER_TEST_URL"})
                try:
                    self.assertEqual(source.engine.dialect.driver, "psycopg2")
                    self.assertEqual(source.engine.dialect.dbapi.__name__, "psycopg2")
                    self.assertEqual(source.engine.url.username, "seed_test")
                    self.assertEqual(source.engine.url.password, "p@ss/word")
                    self.assertEqual(source.engine.url.host, "127.0.0.1")
                    self.assertEqual(source.engine.url.port, 5432)
                    self.assertEqual(source.engine.url.database, "test_database")
                    self.assertEqual(source.engine.url.query["sslmode"], "require")
                    connect.assert_not_called()
                finally:
                    source.close()

    def test_slots_kw_and_year_range(self):
        """1・2・48の開始時刻、kWの保持、月別kWhの集計を確認する。"""
        frame = expand_daily_rows(
            daily_rows(), "2026-06", "0000000000000000000001", value_unit="kW"
        )
        self.assertEqual(len(frame), 17520)
        self.assertEqual(frame.timestamp.iloc[0], pd.Timestamp("2025-07-01 00:00"))
        self.assertEqual(frame.timestamp.iloc[1], pd.Timestamp("2025-07-01 00:30"))
        self.assertEqual(frame.timestamp.iloc[47], pd.Timestamp("2025-07-01 23:30"))
        self.assertEqual(frame.timestamp.iloc[-1], pd.Timestamp("2026-06-30 23:30"))
        self.assertEqual(frame.kw.iloc[0], 1)
        self.assertEqual(frame.kw.iloc[47], 48)
        _, series = build_context(frame, {"target_month": "2026-06", "contract_kw": 50})
        self.assertEqual(
            series["monthly"].loc[pd.Period("2026-06"), "kwh"],
            sum(range(1, 49)) * 0.5 * 30,
        )

    def test_leap_year_and_kwh_option(self):
        """うるう年の枠数と、既定のkWh→kW変換を確認する。"""
        frame = expand_daily_rows(
            daily_rows("2024-06"), "2024-06", "0000000000000000000001"
        )
        self.assertEqual(len(frame), 17568)
        self.assertEqual(frame.kw.iloc[47], 96)
        _, series = build_context(
            frame, {"target_month": "2024-06", "contract_kw": 100}
        )
        self.assertEqual(
            series["monthly"].loc[pd.Period("2024-06"), "kwh"], sum(range(1, 49)) * 30
        )

    def test_duplicate_missing_and_invalid_values(self):
        """日付重複・日欠損・枠欠損を拒否する。"""
        rows = daily_rows()
        for invalid in [
            rows + [rows[0]],
            rows[:1] + rows[2:],
            [{**row, SLOTS[47]: ""} if i == 0 else row for i, row in enumerate(rows)],
        ]:
            with self.assertRaises(ValueError):
                expand_daily_rows(invalid, "2026-06", "0000000000000000000001")

    def test_quality_counts_rejected(self):
        """欠測件数が0でない日を正常な48枠として扱わない。"""
        rows = [{**r, "MISSING": "0"} for r in daily_rows()]
        rows[0]["MISSING"] = "1"
        with self.assertRaisesRegex(ValueError, "欠測"):
            expand_daily_rows(
                rows, "2026-06", "0000000000000000000001", quality_columns=["MISSING"]
            )

    def test_database_accepts_three_day_history(self):
        """SQL取得でも、3日間だけの実績と契約電力を正しく返す。"""
        settings = {"schema": None, "url_env": "REPORT_TEST_URL"}
        with patch.dict(os.environ, {"REPORT_TEST_URL": "sqlite://"}):
            source = DatabaseSource(settings)
        try:
            metadata = MetaData()
            daily = Table(
                "t_ep_electricity_data_30min",
                metadata,
                Column(POINT, String(22)),
                Column(DATE, String(8)),
                *[Column(name, String(9)) for name in SLOTS],
            )
            contract = Table(
                "t_ep_contracted_power",
                metadata,
                Column(CONTRACT_POINT, String(22)),
                Column(CONTRACT_POWER, Integer),
            )
            metadata.create_all(source.engine)
            rows = daily_rows()[-3:]
            with source.engine.begin() as connection:
                connection.execute(daily.insert(), rows)
                connection.execute(
                    contract.insert(),
                    [{CONTRACT_POINT: "0000000000000000000001", CONTRACT_POWER: 50}],
                )
            frame, power = source.load("0000000000000000000001", "2026-06")
            self.assertEqual(len(frame), 144)
            self.assertEqual(power, 50)
            self.assertEqual(frame.timestamp.iloc[0], pd.Timestamp("2026-06-28"))
            self.assertEqual(frame.kw.iloc[-1], 96)
        finally:
            source.close()

    def test_database_filters_and_contract(self):
        """SQLiteで顧客別・期間別の取得と、契約電力の参照を確認する。"""
        settings = {"schema": None, "url_env": "REPORT_TEST_URL", "value_unit": "kW"}
        with patch.dict(os.environ, {"REPORT_TEST_URL": "sqlite://"}):
            source = DatabaseSource(settings)
        try:
            metadata = MetaData()
            daily = Table(
                "t_ep_electricity_data_30min",
                metadata,
                Column(POINT, String(22)),
                Column(DATE, String(8)),
                *[Column(name, String(9)) for name in SLOTS],
            )
            contract = Table(
                "t_ep_contracted_power",
                metadata,
                Column(CONTRACT_POINT, String(22)),
                Column(CONTRACT_POWER, Integer),
            )
            metadata.create_all(source.engine)
            rows = daily_rows()
            extra = [
                {**rows[0], POINT: "0000000000000000000002"},
                {**rows[0], DATE: "20250700"},
                {**rows[-1], DATE: "20260701"},
            ]
            # 20250700は取得開始以前なのでSQL条件で除外される。
            with source.engine.begin() as connection:
                connection.execute(daily.insert(), rows + extra)
                connection.execute(
                    contract.insert(),
                    [{CONTRACT_POINT: "0000000000000000000001", CONTRACT_POWER: 50}],
                )
            frame, power = source.load("0000000000000000000001", "2026-06")
            self.assertEqual(len(frame), 17520)
            self.assertEqual(power, 50)
            with self.assertRaisesRegex(ValueError, "未登録"):
                source.load("0' OR '1'='1", "2026-06")
        finally:
            source.close()
