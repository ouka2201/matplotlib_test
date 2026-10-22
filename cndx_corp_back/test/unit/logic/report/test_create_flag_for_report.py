import pandas as pd

from cndx_corp_back.dto.report.electricity_vis_create_in_dto import (
    ElectricityVisCreateInDto as ElcInDto,
)
from cndx_corp_back.logic.report.report_create_component import ReportCreateComponent


def make_base_df(rows):
    base_cols = {
        "agreement_category": "01",
        "org_id": "TEP",
        "updated_by": None,
        "updated_at": None,
        "building_id": "2025071400001001001",
        "corp_number": "2025071400001",
        "corp_name": "Corp",
        "building_name": "B1",
        "supply_point_number": "sp",
        "ep_customer_number": "ep",
        "missing_time_range_count": 0,
        "invalid_time_range_count": 0,
        "company_id": "C1",
        "delete_flg": False,
        "created_by": None,
        "created_at": None,
        "building_address_prefecture": "Pref",
        "building_address_city": "City",
        "jp_code_name": "JP",
        "building_address": "Addr",
    }
    df = pd.DataFrame(rows)
    for k, v in base_cols.items():
        if k not in df.columns:
            df[k] = v
    return df


def make_elc_dto(target_month="202401"):
    return ElcInDto(
        corporate_number="2025071400001",
        agreement_category="01",
        org_id="TEP",
        building_id="2025071400001001001",
        month_from=target_month,
        target_month=target_month,
        contracted_power=100,
    )


def call_create_flag(df, dto):
    # Avoid calling __init__ (requires Flask app context). The method doesn't use self.
    comp = object.__new__(ReportCreateComponent)
    return ReportCreateComponent.create_flag_for_report(comp, df.copy(), dto)


def test_create_flag_for_report_basic():
    # 2024-01-01 (Mon), 02 (Tue), 03 (Wed)
    rows = [
        {"acquisition_date": "20240101", "e1": 1, "e2": 2},
        {"acquisition_date": "20240102", "e1": 5, "e2": 1},
        {"acquisition_date": "20240103", "e1": 3, "e2": 2},
    ]
    df = make_base_df(rows)
    dto = make_elc_dto("202401")

    out = call_create_flag(df, dto)

    # acquisition_date back to str
    assert list(out["acquisition_date"]) == ["20240101", "20240102", "20240103"]

    # report_weeks = (weekday+1)%7: Mon=0 -> 1, Tue=2, Wed=3
    assert list(out["report_weeks"]) == [1, 2, 3]

    # report_max_day: row with global max (5 on 2024-01-02)
    assert list(out["report_max_day"]) == [0, 1, 0]

    # report_max_week: all rows in the week window containing 2024-01-02
    assert out["report_max_week"].sum() == 3

    # report_max_frequency: threshold is min of row maxima (=2)
    # counts per row of values >= 2: [1,1,2]
    assert list(out["report_max_frequency"]) == [1, 1, 2]

    # report_target_month: prefix match target_month
    assert list(out["report_target_month"]) == [1, 1, 1]


def test_create_flag_for_report_tie_max_selects_earliest_date():
    # Two rows share same row max (=9), earliest date should be flagged for report_max_day
    rows = [
        {"acquisition_date": "20240105", "e1": 9, "e2": 1},
        {"acquisition_date": "20240106", "e1": 9, "e2": 0},
        {"acquisition_date": "20240107", "e1": 1, "e2": 1},
    ]
    df = make_base_df(rows)
    dto = make_elc_dto("202401")
    out = call_create_flag(df, dto)

    assert list(out["report_max_day"]) == [1, 0, 0]


def test_report_weeks_mapping_includes_sunday_zero():
    # 2023-12-31 is Sunday -> (6+1)%7 == 0
    rows = [
        {"acquisition_date": "20231231", "e1": 1},
        {"acquisition_date": "20240101", "e1": 2},  # Monday -> 1
    ]
    df = make_base_df(rows)
    dto = make_elc_dto("202401")
    out = call_create_flag(df, dto)
    assert list(out["report_weeks"]) == [0, 1]


def test_report_max_week_window_crosses_sunday():
    # Max on 2024-01-06 (Sat). Week window Sun-Sat: 2023-12-31..2024-01-06
    rows = [
        {"acquisition_date": "20231230", "e1": 1},  # Sat prev week
        {"acquisition_date": "20231231", "e1": 2},  # Sun (in week)
        {"acquisition_date": "20240106", "e1": 9},  # Sat max (in week)
        {"acquisition_date": "20240107", "e1": 1},  # Sun next week (out)
    ]
    df = make_base_df(rows)
    dto = make_elc_dto("202401")
    out = call_create_flag(df, dto)
    # Only 12/31 and 01/06 within same week as max
    assert list(out["report_max_week"]) == [0, 1, 1, 0]


def test_report_target_month_prefix_match():
    rows = [
        {"acquisition_date": "20240131", "e1": 1},
        {"acquisition_date": "20240201", "e1": 1},
    ]
    df = make_base_df(rows)
    dto = make_elc_dto("202402")
    out = call_create_flag(df, dto)
    assert list(out["report_target_month"]) == [0, 1]
