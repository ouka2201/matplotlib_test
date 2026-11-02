"""レポート用投入PGを現行DDL・実SQL・再実行条件で検証する。"""

from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

import pytest
from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from cndx_corp_batch.common.entity.t_arve_customer_info_entity import TArveCustomerInfo
from cndx_corp_batch.common.entity.t_ep_contracted_power_entity import TEpContractedPower
from cndx_corp_batch.common.entity.t_ep_electricity_data_30min_entity import TEpElectricityData30min
from cndx_corp_batch.domains.generate_all_power_report.services.query_result_service import prepare_query_results
from cndx_corp_batch.test import insert_test_data as seed


@pytest.fixture
def settings(tmp_path):
    return {"url": f"sqlite:///{tmp_path / 'report_seed.db'}", "schema": None}


def rows(settings, table):
    engine = create_engine(settings["url"])
    try:
        with engine.connect() as connection:
            return connection.execute(text(f"SELECT * FROM {table}")).mappings().all()
    finally:
        engine.dispose()


def sql_file(name):
    path = Path(seed.__file__).resolve().parents[1] / "query" / name
    # SQLiteではスキーマ名のみ除外し、結合・抽出・登録には本体のSQLを使う。
    return text(path.read_text(encoding="utf-8").replace("db_corp.", ""))


@pytest.mark.parametrize("physical_schema", [False, True])
def test_seed_is_consumable_by_current_report_sql(settings, physical_schema):
    engine = create_engine(settings["url"])
    try:
        if physical_schema:
            metadata = MetaData()
            for entity in (TArveCustomerInfo, TEpContractedPower, TEpElectricityData30min):
                entity.__table__.to_metadata(metadata, schema=None)
            metadata.create_all(engine)
        result = seed.seed_database(settings, seed.SeedOptions(
            report_month="202602", count=2, days=3, max_kw=1200,
            init_sqlite=True, chunk_size=2,
        ))
        assert result["tables"] == {
            "import_management": {"inserted": 2, "skipped": 0},
            "customer": {"inserted": 2, "skipped": 0},
            "contract": {"inserted": 2, "skipped": 0},
            "daily": {"inserted": 6, "skipped": 0},
        }
        with engine.begin() as connection:
            connection.execute(text("""CREATE TABLE t_power_report_mng_info (
                supply_point_number TEXT, target_year_month TEXT, company_id TEXT,
                syousapo_flg BOOLEAN, file_name TEXT, report_created_at TIMESTAMP,
                create_status TEXT, error_message TEXT, file_path TEXT,
                created_by TEXT, created_at TIMESTAMP,
                PRIMARY KEY (supply_point_number, target_year_month))"""))
            connection.execute(sql_file("insert_unregistered_report_target.sql"), {
                "report_ym": "202602", "user": "test", "created_at": datetime(2026, 4, 16),
            })
            targets = connection.execute(text(
                "SELECT * FROM t_power_report_mng_info ORDER BY supply_point_number"
            )).mappings().all()
            assert [r["syousapo_flg"] for r in targets] == [False, True]
            assert [r["create_status"] for r in targets] == ["2", "2"]
            for target in targets:
                point = target["supply_point_number"]
                customer = connection.execute(sql_file("select_power_report_cust.sql"), {
                    "supply_point_number": point,
                }).mappings().one()
                daily = connection.execute(sql_file("select_power_report_30min.sql"), {
                    "supply_point_number": point, "start_date": "20250301", "end_date": "20260301",
                }).mappings().all()
                frame, config = prepare_query_results(customer, daily, point, "202602")
                assert len(frame) == 3 * 48
                assert frame.kw.max() == 1200
                assert config["contract_kw"] == 1600
                assert config["customer_name"].startswith("テスト事業所")
        for kind, table in seed.TABLE_NAMES.items():
            for row in rows(settings, table):
                normalized = {k.upper(): v for k, v in row.items()}
                assert normalized["CREATED_BY"] == "test_data_seed"
                assert normalized["CREATED_AT"] is not None
                if kind == "daily":
                    assert normalized["T01_KSKJ_KSU"] == normalized["T01_FSIJ_KSU"] == "0"
                    assert all(len(normalized[column]) <= 9 for column in seed.SLOTS)
    finally:
        engine.dispose()


def test_sqlite_definitions_match_current_keys_and_types(settings):
    engine = create_engine(settings["url"])
    try:
        seed.init_sqlite_tables(engine, settings)
        schema = inspect(engine)
        assert schema.get_pk_constraint("t_arve_customer_info")["constrained_columns"] == [seed.CUSTOMER_POINT]
        daily = {c["name"]: c for c in schema.get_columns("t_ep_electricity_data_30min")}
        assert daily[seed.SLOTS[0]]["type"].length == 9
        assert daily["T01_KSKJ_KSU"]["type"].length == 2
        assert not daily["CREATED_AT"]["nullable"]
        contract = {c["name"]: c for c in schema.get_columns("t_ep_contracted_power")}
        assert contract[seed.CONTRACT_POWER]["type"].python_type is int
    finally:
        engine.dispose()


def test_shared_database_config_is_supported(settings):
    config = json.loads(Path(seed.__file__).with_name("database.json").read_text(encoding="utf-8"))
    config.update(settings)
    result = seed.seed_database(config, seed.SeedOptions(
        report_month="2026-06", count=2, days=1, init_sqlite=True,
    ))
    assert all(item == {"inserted": 2, "skipped": 0} for item in result["tables"].values())
    assert rows(settings, "t_arve_customer_info")[0]["cmn_demandlocationfullname_ref__c"] == "テスト事業所000001"


def test_skip_uses_customer_primary_key_even_when_filter_changed(settings):
    options = seed.SeedOptions(report_month="2026-02", count=1, days=2, init_sqlite=True)
    seed.seed_database({**settings, "customer_filters": {"cmn_businesstype__c": "1"}}, options)
    before = rows(settings, "t_arve_customer_info")
    result = seed.seed_database(
        {**settings, "customer_filters": {"cmn_businesstype__c": "2"}},
        replace(options, init_sqlite=False, on_existing="skip"),
    )
    assert result["tables"]["customer"] == {"inserted": 0, "skipped": 1}
    assert result["tables"]["daily"] == {"inserted": 0, "skipped": 2}
    assert rows(settings, "t_arve_customer_info") == before


def test_dry_run_and_duplicate_error_leave_database_unchanged(settings):
    options = seed.SeedOptions(report_month="2026-02", count=1, days=1, init_sqlite=True)
    seed.seed_database(settings, options)
    snapshot = {kind: rows(settings, table) for kind, table in seed.TABLE_NAMES.items()}
    result = seed.seed_database(settings, replace(options, init_sqlite=False, start_id=2, dry_run=True))
    assert all(r["inserted"] == 1 for r in result["tables"].values())
    with pytest.raises(ValueError, match="既存キー") as error:
        seed.seed_database(settings, replace(options, init_sqlite=False))
    message = str(error.value)
    assert "INSERT前のSELECT結果:" in message
    assert "9999000000000000000001" in message
    assert "参照テーブル: t_arve_customer_info" in message
    assert "database=" in message
    assert "この実行で同テーブルへ先行INSERTした件数: 0" in message
    assert f"実行ファイル: {Path(seed.__file__).resolve()}" in message
    assert snapshot == {kind: rows(settings, table) for kind, table in seed.TABLE_NAMES.items()}


def test_late_failure_rolls_back_all_tables(settings):
    engine = create_engine(settings["url"])
    try:
        seed.init_sqlite_tables(engine, settings)
        with engine.begin() as connection:
            connection.execute(text("""CREATE TRIGGER reject_import BEFORE INSERT ON t_30min_import_mng
                BEGIN SELECT RAISE(ABORT, 'test import error'); END"""))
        with pytest.raises(IntegrityError, match="test import error"):
            seed.seed_database(settings, seed.SeedOptions(report_month="2026-02", count=1, days=1))
        assert all(rows(settings, name) == [] for name in seed.TABLE_NAMES.values())
    finally:
        engine.dispose()


@pytest.mark.parametrize("changes", [
    {"value_unit": "kW"}, {"value_unit": "Wh"},
    {"seed_record_type_ids": {"joined": "unknown", "not_joined": "未加入"}},
    {"seed_record_type_ids": {"joined": "省エネサポートサービス", "not_joined": "省エネサポートサービス"}},
])
def test_incompatible_settings_are_rejected_before_connect(settings, changes, monkeypatch):
    monkeypatch.setattr(seed, "create_engine", lambda *a, **kw: pytest.fail("must not connect"))
    with pytest.raises(ValueError):
        seed.seed_database({**settings, **changes}, seed.SeedOptions(report_month="2026-02"))


@pytest.mark.parametrize("changes", [
    {"contract_kw": 1.5}, {"contract_kw": 2147483648},
    {"report_month": "2026-2"}, {"report_month": "2026/02"},
    {"report_month": "202613"}, {"max_kw": float("nan")},
])
def test_invalid_options(changes):
    with pytest.raises(ValueError):
        replace(seed.SeedOptions(report_month="2026-02"), **changes).period()


@pytest.mark.parametrize("month,start,end", [
    ("202402", "2023-03-01", "2024-03-01"),
    ("2024-02", "2023-03-01", "2024-03-01"),
])
def test_twelve_month_period_includes_leap_day(month, start, end):
    first, last = seed.SeedOptions(report_month=month).period()
    assert str(first.date()) == start and str(last.date()) == end
    assert (last - first).days == 366


def test_cli_accepts_bom_config_and_url_env(settings, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SEED_TEST_DATABASE_URL", settings["url"])
    config = tmp_path / "database.json"
    config.write_text(json.dumps({"url_env": "SEED_TEST_DATABASE_URL", "schema": None}), encoding="utf-8-sig")
    seed.main(["--db-config", str(config), "--report-month", "2026-02",
               "--count", "1", "--days", "1", "--init-sqlite"])
    assert json.loads(capsys.readouterr().out)["tables"]["daily"]["inserted"] == 1


def test_multiple_months_do_not_insert_customer_more_than_once(settings):
    options = seed.SeedOptions(
        report_month="2024-02", count=12, months=2, start_id=995, init_sqlite=True,
    )
    result = seed.seed_database(settings, options)
    customers = rows(settings, "t_arve_customer_info")
    points = [r[seed.CUSTOMER_POINT] for r in customers]
    assert len(points) == len(set(points)) == 12
    assert set(points) == {f"999900{serial:016d}" for serial in range(995, 1007)}
    assert result["tables"]["customer"] == {"inserted": 12, "skipped": 0}
    assert result["tables"]["daily"] == {"inserted": 12 * 60, "skipped": 0}


def test_cli_skip_repeated_run_and_add_unused_start_id(settings, tmp_path, capsys):
    config = tmp_path / "database.json"
    config.write_text(json.dumps(settings), encoding="utf-8")
    args = ["--db-config", str(config), "--report-month", "2026-08", "--count", "1", "--months", "12"]
    seed.main([*args, "--init-sqlite"])
    result = json.loads(capsys.readouterr().out)
    assert result["tables"]["customer"] == {"inserted": 1, "skipped": 0}
    assert result["tables"]["daily"] == {"inserted": 365, "skipped": 0}
    with pytest.raises(ValueError, match="t_arve_customer_infoに既存キー"):
        seed.main(args)
    seed.main([*args, "--on-existing", "skip"])
    result = json.loads(capsys.readouterr().out)
    for kind, item in result["tables"].items():
        assert item == {"inserted": 0, "skipped": 365 if kind == "daily" else 1}
    seed.main([*args, "--start-id", "1001"])
    result = json.loads(capsys.readouterr().out)
    for kind, item in result["tables"].items():
        assert item == {"inserted": 365 if kind == "daily" else 1, "skipped": 0}
    assert len(rows(settings, "t_arve_customer_info")) == 2
