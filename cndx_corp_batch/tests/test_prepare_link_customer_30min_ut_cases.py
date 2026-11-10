"""現行112ケース表のTD条件と再設定を確認する。"""

import pytest
from sqlalchemy import create_engine, text

from cndx_corp_batch.test import prepare_link_customer_30min_cases as storage
from cndx_corp_batch.test import prepare_link_customer_30min_ut_cases as cases


def test_catalog_and_case_isolation():
    catalog = cases.load_catalog()
    assert len(catalog["cases"]) == 112
    assert len(catalog["test_data"]) == 72
    assert [item["case_id"] for item in catalog["cases"]] == [f"UT-{i:03d}" for i in range(1, 113)]
    first = cases.build_plan("UT-001")
    second = cases.build_plan("UT-010")
    assert first["test_data_id"] == second["test_data_id"] == "TD-01"
    assert first["points"] != second["points"]
    assert first["target_month"] == "2026-07"
    assert first["batch_environment"]["CUT_OFF_DAY"] == "19"


@pytest.mark.parametrize("case_id,count", [
    ("UT-024", 999), ("UT-025", 1000), ("UT-026", 1001),
    ("UT-027", 2001), ("UT-098", 1001),
])
def test_page_boundary_counts(case_id, count):
    plan = cases.build_plan(case_id)
    assert len(plan["rows"]["management"]) == count
    assert len(plan["rows"]["daily"]) == count


@pytest.mark.parametrize("case_id,expected", [
    ("UT-071", (1, 1)), ("UT-076", (2, 1)),
    ("UT-077", (2, 6)), ("UT-104", (1, 31)),
])
def test_update_and_multiple_days(case_id, expected):
    rows = cases.build_plan(case_id)["rows"]
    assert (len(rows["management"]), len(rows["daily"])) == expected


def test_reset_and_cleanup_new_catalog(tmp_path):
    settings = {"url": f"sqlite:///{tmp_path / 'ut.db'}", "schema": None}
    plan = cases.build_plan("UT-071")
    storage.insert_plan(settings, plan, init_sqlite=True)
    engine = create_engine(settings["url"])
    try:
        with engine.begin() as connection:
            connection.execute(text("UPDATE t_electricity_data_30min SET V30MIN_USED_ENERGY_1=1"))
        storage.insert_plan(settings, plan, reset=True)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT V30MIN_USED_ENERGY_1 FROM t_electricity_data_30min")).scalar_one() == 999
        storage.insert_plan(settings, plan, cleanup=True)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM t_30min_import_mng")).scalar_one() == 0
            assert connection.execute(text("SELECT COUNT(*) FROM t_electricity_data_30min")).scalar_one() == 0
    finally:
        engine.dispose()
