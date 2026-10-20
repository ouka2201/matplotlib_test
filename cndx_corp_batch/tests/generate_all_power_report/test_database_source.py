"""EP30分値の列変換を現行サービスで検証する。"""

import pandas as pd
import pytest

from cndx_corp_batch.domains.generate_all_power_report.services.data_service import bounds
from cndx_corp_batch.domains.generate_all_power_report.services.database_source import (
    DATE,
    POINT,
    SLOTS,
    NumericConversionError,
    expand_daily_rows,
)


def rows(start="2026-06-01", end="2026-07-01", value="1.5"):
    return [
        {
            POINT: "0000000000000000000001",
            DATE: day.strftime("%Y%m%d"),
            **{slot: value for slot in SLOTS},
        }
        for day in pd.date_range(start, end, freq="D", inclusive="left")
    ]


def test_expands_48_slots_to_half_hour_times_and_kw():
    frame = expand_daily_rows(rows(value="1.5"), "202606", "0000000000000000000001")
    assert len(frame) == 30 * 48
    assert frame.timestamp.iloc[0] == pd.Timestamp("2026-06-01 00:00")
    assert frame.timestamp.iloc[1] == pd.Timestamp("2026-06-01 00:30")
    assert frame.timestamp.iloc[-1] == pd.Timestamp("2026-06-30 23:30")
    assert (frame.kw == 3).all()


def test_filters_to_the_twelve_month_period_and_supports_leap_year():
    start, end, _ = bounds("202406")
    frame = expand_daily_rows(
        rows("2024-02-28", "2024-07-01", value="1"), "202406", "0001"
    )
    assert start == pd.Timestamp("2023-07-01")
    assert end == pd.Timestamp("2024-07-01")
    assert len(frame) == 124 * 48


def test_bad_slot_reports_the_source_date_and_column():
    invalid = rows()[:1]
    invalid[0][SLOTS[16]] = "不正値"
    with pytest.raises(NumericConversionError) as caught:
        expand_daily_rows(invalid, "202606", "0001")
    assert caught.value.primary_key == "20260601"
    assert caught.value.column == SLOTS[16]


def test_quality_count_and_unit_are_validated():
    invalid = [{**rows()[:1][0], "MISSING": "1"}]
    with pytest.raises(ValueError, match="MISSING"):
        expand_daily_rows(invalid, "202606", "0001", quality_columns=["MISSING"])
    with pytest.raises(ValueError, match="value_unit"):
        expand_daily_rows(rows()[:1], "202606", "0001", value_unit="MW")
