"""PG2ケースの投入内容と、生成データを使った連携バッチを検証する。"""

from datetime import date
import json
import logging
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from cndx_corp_batch.common import db
from cndx_corp_batch.domains.link_customer_30min.jobs.link_customer_30min_job import LinkCustomer30MinJob
from cndx_corp_batch.test import prepare_link_customer_30min_cases as cases


@pytest.fixture
def settings(tmp_path):
    return {"url": f"sqlite:///{tmp_path / 'cases.db'}", "schema": None}


def read_rows(settings, table):
    engine = create_engine(settings["url"])
    try:
        with engine.connect() as connection:
            return connection.execute(text(f"SELECT * FROM {table}")).mappings().all()
    finally:
        engine.dispose()


def run_batch(settings, plan, monkeypatch, *, reject_zero=False):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def attach(connection, _):
        connection.execute("ATTACH DATABASE ? AS db_corp", (settings["url"].removeprefix("sqlite:///"),))

    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def sqlite_lock_compat(connection, cursor, statement, parameters, context, many):
        return statement.replace("FOR UPDATE OF m", ""), parameters

    # SQLiteのCASTはABを0にするため、トランザクション検証時だけDBエラーを代替する。
    if reject_zero:
        with engine.begin() as connection:
            connection.execute(text("""CREATE TRIGGER db_corp.reject_zero
                BEFORE INSERT ON t_electricity_data_30min
                WHEN NEW.v30min_used_energy_1 = 0
                BEGIN SELECT RAISE(ABORT, 'test numeric conversion error'); END"""))
    monkeypatch.setattr(db, "_Session", sessionmaker(bind=engine))
    context = SimpleNamespace(
        logger=logging.LoggerAdapter(logging.getLogger("test_cases"), {}),
        batch_id="test", batch_name="BLMMVMVBUILDING",
        config=SimpleNamespace(
            cut_off_day=int(plan["batch_environment"]["CUT_OFF_DAY"]),
            report_month_offset_before=int(plan["batch_environment"]["REPORT_MONTH_OFFSET_BEFORE"]),
            report_month_offset_after=int(plan["batch_environment"]["REPORT_MONTH_OFFSET_AFTER"]),
        ),
    )
    try:
        return LinkCustomer30MinJob(context, date.fromisoformat(plan["batch_date"]), 10).run()
    finally:
        engine.dispose()


def test_catalog_covers_every_populated_excel_row():
    catalog = cases.load_catalog()["cases"]
    assert len(catalog) == 72
    assert [c["source_row"] for c in catalog] == list(range(8, 80))
    assert [c["case_id"] for c in catalog] == [str(n) for n in range(1, 73)]
    assert [c["number"] for c in catalog] == list(range(1, 73))


@pytest.mark.parametrize("case_id", [c["case_id"] for c in cases.load_catalog()["cases"]])
def test_each_representable_case_can_be_inserted(settings, case_id):
    plan = cases.build_plan(case_id)
    result = cases.insert_plan(settings, plan, init_sqlite=True)
    assert result["daily"] == len(plan["points"])
    assert len(read_rows(settings, "t_30min_import_mng")) == len(plan["points"])


@pytest.mark.parametrize("case_id,batch_date,expected_month", [
    ("3", "2026-08-01", "2026-05"), ("4", "2026-08-15", "2026-05"),
    ("5", "2026-08-16", "2026-06"), ("6", "2026-08-31", "2026-06"),
    ("7", "2026-01-15", "2025-10"), ("8", "2026-01-16", "2025-11"),
    ("9", "2028-02-29", "2027-12"),
])
def test_date_cases_prepare_spec_month(settings, case_id, batch_date, expected_month):
    plan = cases.build_plan(case_id)
    assert plan["batch_date"] == batch_date
    assert plan["target_month"] == expected_month
    assert plan["batch_environment"] == {
        "CUT_OFF_DAY": "16", "REPORT_MONTH_OFFSET_BEFORE": "3", "REPORT_MONTH_OFFSET_AFTER": "2",
    }
    cases.insert_plan(settings, plan, init_sqlite=True)
    row = read_rows(settings, "t_30min_import_mng")[0]
    assert row["TARGET_YEAR_MONTH"] == expected_month.replace("-", "")


@pytest.mark.parametrize("case_id", ["3", "4", "5", "6", "7", "8", "9"])
def test_date_cases_link_with_current_batch(settings, monkeypatch, case_id):
    plan = cases.build_plan(case_id)
    cases.insert_plan(settings, plan, init_sqlite=True)
    assert run_batch(settings, plan, monkeypatch) == 1


@pytest.mark.parametrize("case_id,count", [
    ("2", 0), ("10", 1), ("11", 0), ("12", 0), ("13", 0), ("14", 1), ("15", 0), ("16", 0),
    ("17", 1), ("18", 0), ("19", 0), ("20", 1), ("21", 9), ("22", 10), ("23", 11), ("24", 21),
])
def test_selection_and_page_counts(settings, monkeypatch, case_id, count, caplog):
    plan = cases.build_plan(case_id)
    cases.insert_plan(settings, plan, init_sqlite=True)
    with caplog.at_level(logging.INFO, logger="test_cases"):
        assert run_batch(settings, plan, monkeypatch) == count
    assert len(read_rows(settings, "t_electricity_data_30min")) == count
    pages = [r for r in caplog.records if "30分値紐付け処理単位完了" in r.getMessage()]
    assert len(pages) == (count + 9) // 10


@pytest.mark.parametrize("case_id,office,customer", [
    ("34", "001", None), ("35", "012", ""), ("36", "012", "3"), ("38", "012", ""), ("39", "01", ""),
])
def test_customer_substrings(settings, monkeypatch, case_id, office, customer):
    plan = cases.build_plan(case_id)
    cases.insert_plan(settings, plan, init_sqlite=True)
    run_batch(settings, plan, monkeypatch)
    row = read_rows(settings, "t_electricity_data_30min")[0]
    assert row["ARVE_OFFICE_CODE"] == office
    assert row["ARVE_CUSTOMER_NUMBER"] == (customer if customer is not None else plan["rows"]["customer"][0]["CMN_OldCustomerNum__c"][3:])


def test_mapping_all_slots_and_rerun(settings, monkeypatch):
    plan = cases.build_plan("51")
    cases.insert_plan(settings, plan, init_sqlite=True)
    assert run_batch(settings, plan, monkeypatch) == 1
    row = read_rows(settings, "t_electricity_data_30min")[0]
    assert [row[f"V30MIN_USED_ENERGY_{i}"] for i in range(1, 49)] == list(range(1, 49))
    assert row["CORP_NAME"] == plan["rows"]["corporate"][0]["COMPANY_NAME"]
    assert row["BUILDING_NAME"] == plan["rows"]["building"][0]["LOCATION_IDENTIFIER_NAME"]
    assert row["ARVE_CORP_NAME"] == plan["rows"]["customer"][0]["CMN_DemandLocationFullName_Ref__c"]
    assert row["UPDATED_AT"] is None and row["FILE_UPDATE_DATE"] is None
    assert run_batch(settings, plan, monkeypatch) == 0


@pytest.mark.parametrize("case_id", ["61", "62", "63", "64", "67"])
def test_upsert_preserves_original_creation(settings, monkeypatch, case_id):
    plan = cases.build_plan(case_id)
    cases.insert_plan(settings, plan, init_sqlite=True)
    before = read_rows(settings, "t_electricity_data_30min")[0]
    run_batch(settings, plan, monkeypatch)
    rows = read_rows(settings, "t_electricity_data_30min")
    assert len(rows) == 1
    assert rows[0]["CREATED_BY"] == before["CREATED_BY"] == "pg2_original"
    assert rows[0]["CREATED_AT"] == before["CREATED_AT"]
    assert rows[0]["UPDATED_AT"] != before["UPDATED_AT"]
    assert rows[0]["V30MIN_USED_ENERGY_1"] == 1
    assert rows[0]["DELETE_FLG"] == 0 and rows[0]["FILE_UPDATE_DATE"] is None


def test_success_clears_only_link_error(settings, monkeypatch):
    plan = cases.build_plan("69")
    cases.insert_plan(settings, plan, init_sqlite=True)
    run_batch(settings, plan, monkeypatch)
    row = read_rows(settings, "t_30min_import_mng")[0]
    assert row["LINKED_ERROR_MESSAGE"] == "" and row["LINKED_DATE"]
    assert row["ERROR_MESSAGE"] == plan["rows"]["management"][0]["ERROR_MESSAGE"]


@pytest.mark.parametrize("case_id,column,value", [
    ("41", "T01_KSKJ_KSU", "12"), ("42", "T01_KSKJ_KSU", "0"),
    ("43", "T01_KSKJ_KSU", ""), ("44", "T01_KSKJ_KSU", "AB"), ("45", "T01_KSKJ_KSU", "-1"),
    ("46", "T01_FSIJ_KSU", "12"), ("47", "T01_FSIJ_KSU", "0"),
    ("48", "T01_FSIJ_KSU", ""), ("49", "T01_FSIJ_KSU", "AB"), ("50", "T01_FSIJ_KSU", "-1"),
    ("52", "T01_30T_SYR01", "0.12"), ("53", "T01_30T_SYR01", "0"),
    ("54", "T01_30T_SYR01", ""), ("55", "T01_30T_SYR01", "AB"), ("71", "T01_30T_SYR01", "AB"),
])
def test_exact_test_values_survive_insert(settings, case_id, column, value):
    cases.insert_plan(settings, cases.build_plan(case_id), init_sqlite=True)
    assert read_rows(settings, "t_ep_electricity_data_30min")[0][column] == value


def test_case72_commits_first_page_and_rolls_back_second(settings, monkeypatch):
    plan = cases.build_plan("72")
    cases.insert_plan(settings, plan, init_sqlite=True)
    with pytest.raises(IntegrityError, match="test numeric conversion error"):
        run_batch(settings, plan, monkeypatch, reject_zero=True)
    linked = read_rows(settings, "t_electricity_data_30min")
    assert sorted(row["SUPPLY_POINT_NUMBER"] for row in linked) == plan["points"][:10]
    management = sorted(read_rows(settings, "t_30min_import_mng"), key=lambda r: r["SUPPLY_POINT_NUMBER"])
    assert all(row["LINKED_DATE"] for row in management[:10])
    assert all(row["LINKED_DATE"] is None and row["LINKED_ERROR_MESSAGE"] for row in management[10:])


@pytest.mark.parametrize("column,value,message", [
    ("CREATE_STATUS", None, "NOT NULL"), ("LINKED_DATE", "", "日時型"),
])
def test_invalid_input_is_rejected_without_partial_insert(settings, column, value, message):
    plan = cases.build_plan("10")
    plan["rows"]["management"][0][column] = value
    with pytest.raises(ValueError, match=message):
        cases.insert_plan(settings, plan, init_sqlite=True)
    assert read_rows(settings, "m_corporate_basic") == []


def test_duplicate_seed_never_overwrites(settings):
    plan = cases.build_plan("67")
    cases.insert_plan(settings, plan, init_sqlite=True)
    before = read_rows(settings, "t_electricity_data_30min")
    with pytest.raises(ValueError, match="既存キー"):
        cases.insert_plan(settings, plan)
    assert read_rows(settings, "t_electricity_data_30min") == before


def test_insert_failure_rolls_back_all_tables(settings):
    engine = create_engine(settings["url"])
    try:
        cases.seed.init_sqlite_tables(engine, settings)
        with engine.begin() as connection:
            connection.execute(text("""CREATE TRIGGER reject_customer BEFORE INSERT ON t_arve_customer_info
                BEGIN SELECT RAISE(ABORT, 'seed failure'); END"""))
        with pytest.raises(IntegrityError, match="seed failure"):
            cases.insert_plan(settings, cases.build_plan("10"))
        assert read_rows(settings, "m_corporate_basic") == []
        assert read_rows(settings, "m_building") == []
    finally:
        engine.dispose()


def test_cli_dry_run_is_offline_and_exports_plan(tmp_path, monkeypatch):
    def no_connection(*args, **kwargs):
        pytest.fail("dry-run must not connect")
    monkeypatch.setattr(cases, "create_engine", no_connection)
    output = tmp_path / "plan.json"
    assert cases.main(["--case", "72", "--dry-run", "--output", str(output)]) == 0
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert len(plan["rows"]["daily"]) == 15
    assert [row["T01_30T_SYR01"] for row in plan["rows"]["daily"]] == ["1"] * 10 + ["AB"] * 5


@pytest.mark.parametrize("case_id", ["59-1", "59-3", "60-1", "60-4", "0", "73", "unknown"])
def test_old_branch_ids_or_undefined_cases_are_rejected(case_id):
    with pytest.raises(ValueError, match="ケースID"):
        cases.build_plan(case_id)
