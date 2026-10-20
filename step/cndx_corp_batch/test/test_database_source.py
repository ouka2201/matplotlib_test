"""DBから取得した形式の48枠データを、外部に接続せずに検証する。"""

import pandas as pd
import pytest

from cndx_corp_batch.domains.generate_all_power_report.services.database_source import (
    DATE,
    POINT,
    SLOTS,
    NumericConversionError,
    expand_daily_rows,
)


@pytest.fixture
def daily_row():
    return {DATE: "20260731", POINT: "0001", **dict.fromkeys(SLOTS, "50")}


@pytest.mark.parametrize("unit, expected", [("kWh", 100), ("kW", 50), ("Wh", 0.1)])
def test_unit_conversion_and_slot_times(daily_row, unit, expected):
    daily_row[SLOTS[-1]] = "75"

    frame = expand_daily_rows([daily_row], "202607", "0001", value_unit=unit)

    assert len(frame) == 48
    assert frame.timestamp.iloc[0] == pd.Timestamp("2026-07-31 00:00")
    assert frame.timestamp.iloc[-1] == pd.Timestamp("2026-07-31 23:30")
    assert frame.timestamp.diff().iloc[1:].eq(pd.Timedelta(minutes=30)).all()
    assert frame.kw.iloc[:-1].to_numpy() == pytest.approx([expected] * 47)
    assert frame.kw.iloc[-1] == pytest.approx(expected * 1.5)


@pytest.mark.parametrize("slot", [SLOTS[0], SLOTS[23], SLOTS[-1]])
def test_conversion_error_identifies_date_and_column(daily_row, slot):
    daily_row[slot] = "数値以外"

    with pytest.raises(NumericConversionError) as error:
        expand_daily_rows([daily_row], "202607", "0001")

    assert error.value.primary_key == "20260731"
    assert error.value.column == slot
    assert str(error.value) == "数値変換エラー：20260731"


@pytest.mark.parametrize(
    "inside, outside",
    [("20250801", "20250731"), ("20260731", "20260801")],
)
def test_twelve_month_window_excludes_outside_rows(daily_row, inside, outside):
    rows = [
        {**daily_row, DATE: outside, SLOTS[0]: "期間外の不正値"},
        {**daily_row, DATE: inside},
    ]

    frame = expand_daily_rows(rows, "202607", "0001")

    assert len(frame) == 48
    assert frame.timestamp.dt.strftime("%Y%m%d").eq(inside).all()


def test_lowercase_database_column_names(daily_row):
    row = {key.lower(): value for key, value in daily_row.items()}

    frame = expand_daily_rows([row], "202607", "0001")

    assert len(frame) == 48
    assert frame.kw.eq(100).all()


def test_missing_slot_is_not_filled_with_zero(daily_row):
    del daily_row[SLOTS[-1]]

    with pytest.raises(KeyError):
        expand_daily_rows([daily_row], "202607", "0001")
