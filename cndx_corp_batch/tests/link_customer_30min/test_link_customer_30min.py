"""実SQLの登録・更新と、バッチのトランザクション境界を検証する。"""

from datetime import date
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from cndx_corp_batch.common import db
from cndx_corp_batch.domains.link_customer_30min.jobs import link_customer_30min_job as module
from cndx_corp_batch.entrypoints import link_customer_30min as entrypoint


@pytest.fixture
def context():
    return SimpleNamespace(
        logger=logging.LoggerAdapter(logging.getLogger("test"), {}),
        batch_id="test", batch_name="BLMMVMVBUILDING",
    )


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def attach(connection, _):
        connection.execute("ATTACH DATABASE ':memory:' AS db_corp")

    @event.listens_for(engine, "before_cursor_execute", retval=True)
    def sqlite_lock_compat(connection, cursor, statement, parameters, context, many):
        # SQLiteでは行ロック構文だけを除外する。結合・UPSERT・更新は実SQLを実行する。
        return statement.replace("FOR UPDATE OF m", ""), parameters

    slot_sources = ", ".join(f"t01_30t_syr{i:02} TEXT" for i in range(1, 49))
    slot_targets = ", ".join(f"v30min_used_energy_{i} NUMERIC" for i in range(1, 49))
    definitions = [
        """t_30min_import_mng (
            supply_point_number TEXT, target_year_month TEXT, create_status TEXT,
            linked_date TIMESTAMP, linked_error_message VARCHAR(100),
            error_message TEXT, updated_by TEXT, updated_at TIMESTAMP,
            PRIMARY KEY (supply_point_number, target_year_month))""",
        """m_building (corporate_number TEXT, agreement_category TEXT, org_id TEXT,
            building_id TEXT, location_identifier_name TEXT, ep_customer_number TEXT,
            supply_point_number TEXT, delete_flg BOOLEAN)""",
        "m_corporate_basic (corporate_number TEXT PRIMARY KEY, company_name TEXT)",
        """t_arve_customer_info (cmn_supplypointspecificnum__c TEXT PRIMARY KEY,
            cmn_kigyoid_fk__c TEXT, cmn_demandlocationfullname_ref__c TEXT,
            cmn_oldcustomernum__c TEXT)""",
        f"""t_ep_electricity_data_30min (t01_kyo_ctn_tok_no TEXT,
            t01_get_ymd TEXT, t01_kskj_ksu TEXT, t01_fsij_ksu TEXT, {slot_sources},
            PRIMARY KEY (t01_kyo_ctn_tok_no, t01_get_ymd))""",
        f"""t_electricity_data_30min (
            corp_number TEXT, agreement_category TEXT, org_id TEXT, building_id TEXT,
            corp_name TEXT, building_name TEXT, ep_customer_number TEXT,
            supply_point_number TEXT, company_id TEXT, missing_time_range_count INTEGER,
            invalid_time_range_count INTEGER, acquisition_date TEXT, {slot_targets},
            delete_flg BOOLEAN, created_by TEXT, created_at TIMESTAMP,
            updated_by TEXT, updated_at TIMESTAMP, file_update_date TIMESTAMP,
            arve_corp_name TEXT, arve_customer_number TEXT, arve_office_code TEXT,
            PRIMARY KEY (corp_number, agreement_category, org_id, building_id,
                         acquisition_date, supply_point_number))""",
    ]
    with engine.begin() as connection:
        for definition in definitions:
            connection.execute(text("CREATE TABLE db_corp." + definition))
    monkeypatch.setattr(db, "_Session", sessionmaker(bind=engine))
    yield engine
    engine.dispose()


def run_sql(engine, sql, **params):
    with engine.begin() as connection:
        result = connection.execute(text(sql), params)
        return result.mappings().all() if result.returns_rows else []


def seed(engine, point="0001", month="202603", status="3", deleted=False):
    run_sql(engine, """INSERT INTO db_corp.t_30min_import_mng
        (supply_point_number, target_year_month, create_status, error_message)
        VALUES (:point, :month, :status, '元の取込メッセージ')""",
        point=point, month=month, status=status)
    run_sql(engine, """INSERT INTO db_corp.m_building VALUES
        (:point, '01', 'org', :point, '拠点名', '0000000000123', :point, :deleted)""",
        point=point, deleted=deleted)
    run_sql(engine, "INSERT INTO db_corp.m_corporate_basic VALUES (:point, '企業名')",
        point=point)
    run_sql(engine, """INSERT INTO db_corp.t_arve_customer_info VALUES
        (:point, '00123', 'ARVE名', '0120000000000456')""", point=point)
    slots = ", ".join(f"t01_30t_syr{i:02}" for i in range(1, 49))
    values = ", ".join(f"'{i}.25'" for i in range(1, 49))
    for day in ["20260228", "20260301", "20260331", "20260401"]:
        run_sql(engine, f"""INSERT INTO db_corp.t_ep_electricity_data_30min
            (t01_kyo_ctn_tok_no, t01_get_ymd, t01_kskj_ksu, t01_fsij_ksu, {slots})
            VALUES (:point, :day, '02', '03', {values})""", point=point, day=day)


def make_job(context, size=1000):
    return module.LinkCustomer30MinJob(context, date(2026, 5, 19), size)


@pytest.mark.parametrize("day, month, end", [
    ("2026-05-01", "202602", "20260228"),
    ("2026-05-18", "202602", "20260228"),
    ("2026-05-19", "202603", "20260331"),
    ("2026-05-31", "202603", "20260331"),
    ("2026-01-18", "202510", "20251031"),
    ("2026-01-19", "202511", "20251130"),
    ("2024-05-18", "202402", "20240229"),
])
def test_target_month(context, day, month, end):
    job = module.LinkCustomer30MinJob(context, date.fromisoformat(day))
    assert job.params["target_year_month"] == month
    assert job.params["end_date"] == end


def test_insert_mapping_and_rerun(database, context):
    seed(database)
    job = make_job(context)
    assert job.run() == 1
    rows = run_sql(database, "SELECT * FROM db_corp.t_electricity_data_30min ORDER BY acquisition_date")
    assert [r["acquisition_date"] for r in rows] == ["20260301", "20260331"]
    row = rows[0]
    assert (row["corp_name"], row["building_name"]) == ("企業名", "拠点名")
    assert (row["company_id"], row["ep_customer_number"]) == ("00123", "0000000000123")
    assert (row["arve_office_code"], row["arve_customer_number"]) == ("012", "0000000000456")
    assert row["arve_corp_name"] == "ARVE名"
    assert (row["missing_time_range_count"], row["invalid_time_range_count"]) == (2, 3)
    for i in range(1, 49):
        assert row[f"v30min_used_energy_{i}"] == i + .25
    assert row["delete_flg"] == 0
    assert row["updated_at"] is None and row["file_update_date"] is None
    assert row["created_at"] is not None and row["created_by"]
    assert job.run() == 0


def test_upsert_preserves_creation_and_scopes_month(database, context):
    seed(database)
    job = make_job(context)
    job.run()
    run_sql(database, """INSERT INTO db_corp.t_30min_import_mng
        (supply_point_number, target_year_month, create_status) VALUES ('0001', '202602', '3')""")
    run_sql(database, """UPDATE db_corp.t_electricity_data_30min
        SET created_by='original', created_at='2000-01-01', delete_flg=TRUE,
            file_update_date='2000-01-01', v30min_used_energy_1=999""")
    run_sql(database, """UPDATE db_corp.t_30min_import_mng
        SET linked_date=NULL, linked_error_message='前回エラー' WHERE target_year_month='202603'""")
    assert job.run() == 1
    rows = run_sql(database, "SELECT * FROM db_corp.t_electricity_data_30min")
    assert len(rows) == 2
    for row in rows:
        assert row["created_by"] == "original" and row["created_at"] == "2000-01-01"
        assert row["v30min_used_energy_1"] == 1.25
        assert row["updated_at"] and row["delete_flg"] == 0
        assert row["file_update_date"] is None
    management = run_sql(database, "SELECT * FROM db_corp.t_30min_import_mng ORDER BY target_year_month")
    assert management[0]["linked_date"] is None
    assert management[1]["linked_date"] and management[1]["linked_error_message"] == ""
    assert management[1]["error_message"] == "元の取込メッセージ"


def test_selection_and_pagination_with_missing_join(database, context):
    seed(database, "0001")
    seed(database, "0002", status="4")
    seed(database, "0003", deleted=True)
    seed(database, "0004")
    seed(database, "0005")
    run_sql(database, "DELETE FROM db_corp.t_arve_customer_info WHERE cmn_supplypointspecificnum__c='0001'")
    # 同じ供給地点に複数の建物があっても、取得件数は管理行単位とする。
    run_sql(database, """INSERT INTO db_corp.m_building SELECT corporate_number,
        agreement_category, org_id, 'other', location_identifier_name,
        ep_customer_number, supply_point_number, delete_flg
        FROM db_corp.m_building WHERE supply_point_number='0004'""")
    assert make_job(context, size=1).run() == 2
    rows = run_sql(database, "SELECT * FROM db_corp.t_30min_import_mng ORDER BY supply_point_number")
    assert [r["linked_date"] is not None for r in rows] == [False, False, False, True, True]
    assert len(run_sql(database, "SELECT * FROM db_corp.t_electricity_data_30min")) == 6


def test_logs_each_batch_page(database, context, caplog):
    for point in ("0001", "0002", "0003", "0004", "0005"):
        seed(database, point)

    with caplog.at_level(logging.INFO, logger="test"):
        assert make_job(context, size=2).run() == 5

    page_logs = [
        record.getMessage()
        for record in caplog.records
        if "30分値紐付け処理単位完了" in record.getMessage()
    ]
    fetch_logs = [
        record.getMessage()
        for record in caplog.records
        if "30分値紐付けページ取得" in record.getMessage()
    ]
    assert len(page_logs) == 3
    assert len(fetch_logs) == 3
    assert all("バッチサイズ=2" in message for message in fetch_logs)
    assert "単位番号=1" in page_logs[0] and "取得件数=2" in page_logs[0]
    assert "単位番号=2" in page_logs[1] and "取得件数=2" in page_logs[1]
    assert "単位番号=3" in page_logs[2] and "取得件数=1" in page_logs[2]


def test_rollback_records_error_and_stops(database, context):
    seed(database, "0001")
    seed(database, "0002")
    seed(database, "0003")
    # 2回目の管理更新を失敗させ、同じトランザクションの生データも戻ることを確認する。
    run_sql(database, """CREATE TRIGGER db_corp.fail_link BEFORE UPDATE OF linked_date
        ON t_30min_import_mng WHEN NEW.supply_point_number='0002'
        BEGIN SELECT RAISE(ABORT, 'link failure'); END""")
    with pytest.raises(Exception, match="link failure"):
        make_job(context, size=1).run()
    rows = run_sql(database, "SELECT * FROM db_corp.t_30min_import_mng ORDER BY supply_point_number")
    assert rows[0]["linked_date"]
    assert rows[1]["linked_date"] is None and rows[1]["linked_error_message"]
    assert len(rows[1]["linked_error_message"]) <= 100
    assert rows[2]["linked_date"] is None and rows[2]["linked_error_message"] is None
    data = run_sql(database, "SELECT DISTINCT supply_point_number FROM db_corp.t_electricity_data_30min")
    assert [r["supply_point_number"] for r in data] == ["0001"]


def test_empty_and_invalid_size(database, context):
    assert make_job(context).run() == 0
    with pytest.raises(ValueError):
        make_job(context, size=0)


def test_failed_page_is_atomic_and_can_retry(database, context):
    seed(database, "0001")
    seed(database, "0002")
    run_sql(database, """CREATE TRIGGER db_corp.fail_link BEFORE UPDATE OF linked_date
        ON t_30min_import_mng WHEN NEW.supply_point_number='0002'
        BEGIN SELECT RAISE(ABORT, 'page failure'); END""")
    job = make_job(context)
    with pytest.raises(Exception, match="page failure"):
        job.run()
    assert run_sql(database, "SELECT * FROM db_corp.t_electricity_data_30min") == []
    rows = run_sql(database, "SELECT * FROM db_corp.t_30min_import_mng")
    assert all(r["linked_date"] is None and r["linked_error_message"] for r in rows)
    run_sql(database, "DROP TRIGGER db_corp.fail_link")
    assert job.run() == 2
    rows = run_sql(database, "SELECT * FROM db_corp.t_30min_import_mng")
    assert all(r["linked_date"] and r["linked_error_message"] == "" for r in rows)


def test_error_recording_failure_preserves_original(database, context, caplog):
    seed(database)
    run_sql(database, """CREATE TRIGGER db_corp.fail_link BEFORE UPDATE OF linked_date
        ON t_30min_import_mng BEGIN SELECT RAISE(ABORT, 'original failure'); END""")
    run_sql(database, """CREATE TRIGGER db_corp.fail_error BEFORE UPDATE OF linked_error_message
        ON t_30min_import_mng WHEN NEW.linked_date IS NULL
        BEGIN SELECT RAISE(ABORT, 'secondary failure'); END""")
    with pytest.raises(Exception, match="original failure"):
        make_job(context).run()
    assert "紐付けエラーの記録に失敗" in caplog.text
    assert run_sql(database, "SELECT * FROM db_corp.t_electricity_data_30min") == []


@pytest.mark.parametrize("fails, expected", [(False, 0), (True, 1)])
def test_entrypoint_passes_arguments_and_closes(monkeypatch, fails, expected):
    from dataclasses import make_dataclass
    config = make_dataclass("Config", ["batch_name"])(None)
    monkeypatch.setattr(entrypoint, "load_config", lambda: config)
    context = Mock()
    context.__enter__ = Mock(return_value=context)
    context.__exit__ = Mock(return_value=False)
    factory = Mock(return_value=context)
    monkeypatch.setattr(entrypoint, "BatchContext", factory)
    monkeypatch.setattr(entrypoint, "setup_logging", Mock())
    job = Mock()
    if fails:
        job.run.side_effect = RuntimeError("failure")
    job_factory = Mock(return_value=job)
    monkeypatch.setattr(entrypoint, "LinkCustomer30MinJob", job_factory)
    assert entrypoint.main(["--batch-date", "2026-05-19", "--batch-size", "2"]) == expected
    job_factory.assert_called_once_with(context, date(2026, 5, 19), 2)
    context.__exit__.assert_called_once()
    assert factory.call_args.args[0].batch_name == "BLMMVMVBUILDING"
