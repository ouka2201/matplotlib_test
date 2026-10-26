"""投入内容・実DB列への適合・投入失敗時の原子性を検証する。"""

import importlib.util
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError

from cndx_corp_batch.test import prepare_sales_user_handover_cases as seed

ROOT = Path(__file__).resolve().parents[2]
QUERY = ROOT / "cndx_corp_batch" / "query"
ENTITY = ROOT / "cndx_corp_back" / "entity"
VARIANTS = [
    (n, v)
    for n in range(1, 79)
    for v in (("target", "comparison") if n in seed.SPLIT_CASES else (None,))
]


def plan(number, variant=None, **kwargs):
    return seed.build_plan(str(number), variant=variant, **kwargs)


@pytest.fixture
def database(tmp_path):
    metadata = MetaData()
    for key, name in seed.TABLE_NAMES.items():
        if key == "handover":
            continue
        path = ENTITY / f"{name}_entity.py"
        spec = importlib.util.spec_from_file_location(f"seed_test_{name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = next(iter(module.Base.metadata.tables.values()))
        source.to_metadata(metadata, schema=None)
    Table(
        "t_sales_user_handover_info",
        metadata,
        Column("corporate_number", String(13), primary_key=True),
        Column("handover_from_org_id", String(20), primary_key=True),
        Column("handover_from_user_id", String(8), primary_key=True),
        Column("handover_to_org_id", String(20)),
        Column("handover_to_user_id", String(8)),
        Column("handover_schedule_date", String(8), nullable=False),
        Column("handover_status", String(1), nullable=False),
        Column("handover_type", String(1), nullable=False),
        Column("report_data_flg", Boolean),
        Column("handovered_at", DateTime),
        Column("creator_id", String(8)),
        Column("creator_org_id", String(20)),
        Column("insert_datetime", DateTime),
        Column("created_by", String(50)),
        Column("created_at", DateTime),
        Column("updated_by", String(50)),
        Column("updated_at", DateTime),
    )
    settings = {"url": f"sqlite:///{tmp_path / 'handover.db'}", "schema": None}
    engine = create_engine(settings["url"])
    metadata.create_all(engine)
    yield settings, engine, metadata
    engine.dispose()


def read_rows(database, key):
    _, engine, metadata = database
    with engine.connect() as connection:
        return (
            connection.execute(select(metadata.tables[seed.TABLE_NAMES[key]]))
            .mappings()
            .all()
        )


def test_catalog_matches_case_numbers():
    cases = seed.load_catalog()["cases"]
    assert [c["number"] for c in cases] == list(range(1, 79))
    assert [c["source_row"] for c in cases] == list(range(7, 85))
    assert cases[55]["title"] == "引継先組織ID不一致を除外"


@pytest.mark.parametrize("number,variant", VARIANTS)
def test_every_case_inserts_against_existing_entity_definitions(
    database, number, variant
):
    prepared = plan(number, variant)
    assert all(
        row["HANDOVER_TYPE"] == ("1" if number in (61, 62) else "0")
        for row in prepared["rows"]["handover"]
    )
    counts = seed.insert_plan(database[0], prepared)
    assert counts == {key: len(read_rows(database, key)) for key in seed.TABLE_NAMES}


@pytest.mark.parametrize(
    "number,expected",
    [
        (3, 0),
        (8, 0),
        (9, 0),
        (10, 0),
        (11, 0),
        (2, 1),
        (4, 1),
        (5, 1),
        (6, 1),
        (12, 1),
        (61, 3),
        (62, 300),
        (64, 0),
    ],
)
def test_actual_target_sql_selects_intended_rows(database, number, expected):
    prepared = plan(number)
    seed.insert_plan(database[0], prepared)
    sql = (QUERY / "select_sales_user_handover_targets.sql").read_text(encoding="utf-8")
    with database[1].connect() as conn:
        # SQLのテーブル名だけSQLiteのmainへ対応させ、条件式は本体を使用する。
        selected = (
            conn.execute(
                text(sql.replace("db_corp.", "main.")),
                {
                    "batch_date": prepared["batch_date"].replace("-", ""),
                    "handover_status": "1",
                },
            )
            .mappings()
            .all()
        )
    assert len(selected) == expected


@pytest.mark.parametrize(
    "number,order", [(13, (2, 1, 3)), (14, (2, 1, 3)), (15, (1, 2, 3))]
)
def test_registration_and_update_order(database, number, order):
    prepared = plan(number)
    seed.insert_plan(database[0], prepared)
    sql = (QUERY / "select_sales_user_handover_targets.sql").read_text(encoding="utf-8")
    with database[1].connect() as conn:
        selected = (
            conn.execute(
                text(sql.replace("db_corp.", "main.")),
                {"batch_date": "20261026", "handover_status": "1"},
            )
            .mappings()
            .all()
        )
    values = [r["corporate_number"] for r in selected]
    expected = [prepared["identifiers"][f"C{i}"] for i in order]
    assert values == expected if number != 15 else set(values) == set(expected)


@pytest.mark.parametrize(
    "number,key,filename",
    [
        (33, "A", "monthly_building"),
        (35, "B", "annual_building"),
        (37, "C", "monthly_corporate"),
        (39, "D", "annual_corporate"),
        (41, "E", "report_storage"),
        (43, "F", "building"),
        (44, "G", "cn_application"),
        (46, "H", "building_info"),
    ],
)
def test_history_range_fixtures_allow_real_update_without_key_collision(
    database, number, key, filename
):
    prepared = plan(number)
    seed.insert_plan(database[0], prepared)
    before = read_rows(database, key)
    ids = prepared["identifiers"]
    field = "agreement_org" if key == "F" else "org_id"
    sql = (QUERY / f"update_handover_{filename}.sql").read_text(encoding="utf-8")
    with database[1].begin() as conn:
        result = conn.execute(
            text(sql.replace("db_corp.", "main.")),
            {
                "corporate_number": ids["C1"],
                "handover_from_org_id": ids["O1"],
                "handover_to_org_id": ids["O2"],
            },
        )
        assert result.rowcount == 2
    after = read_rows(database, key)
    expected = [
        dict(r, **{field: ids["O2"]})
        if r["corporate_number"] == ids["C1"] and r[field] == ids["O1"]
        else dict(r)
        for r in before
    ]
    assert sorted(str(sorted(r.items())) for r in after) == sorted(
        str(sorted(r.items())) for r in expected
    )


def test_missing_rows_and_other_corporation_presence():
    for n in (25, 65):
        assert plan(n)["rows"]["staff"] == []
    for n in (26, 71):
        p = plan(n)
        assert all(r["USER_ID"] != p["identifiers"]["U1"] for r in p["rows"]["staff"])
    p = plan(27)
    assert [r["CORPORATE_NUMBER"] for r in p["rows"]["staff"]] == [
        p["identifiers"]["C2"]
    ]
    for n, key in seed.MISSING_CASES.items():
        assert {k: len(plan(n)["rows"][k]) for k in seed.HISTORY} == {
            k: int(k != key) for k in seed.HISTORY
        }
    for n in (49, 51, 66, 75, 78):
        p = plan(n)
        assert not any(
            r["CORPORATE_NUMBER"] == p["identifiers"]["C1"] for r in p["rows"]["F"]
        )
    p = plan(50)
    assert p["rows"]["F"][0]["AGREEMENT_ORG"] == p["identifiers"]["O3"]


def test_staff_control_rows_and_nullable_flag():
    for number, expected in [
        (21, ("C2", "U1")),
        (22, ("C1", "U3")),
        (24, ("C1", "U2")),
    ]:
        p = plan(number)
        row = p["rows"]["staff"][1]
        assert (row["CORPORATE_NUMBER"], row["USER_ID"]) == tuple(
            p["identifiers"][v] for v in expected
        )
    assert plan(32)["rows"]["handover"][0]["REPORT_DATA_FLG"] is None
    assert [r["REPORT_DATA_FLG"] for r in plan(61)["rows"]["handover"]] == [
        True,
        False,
        True,
    ]


@pytest.mark.parametrize(
    "number,time",
    [(16, "00:58:59"), (17, "00:59:00"), (18, "00:59:59"), (19, "01:00:00")],
)
def test_cutoff_timestamps(number, time):
    assert plan(number)["rows"]["handover"][0][
        "INSERT_DATETIME"
    ] == datetime.fromisoformat(f"2026-10-26T{time}")


@pytest.mark.parametrize(
    "number,field,expected",
    [
        (56, "HANDOVER_TO_ORG_ID", "O3"),
        (57, "HANDOVER_STATUS", "0"),
        (58, "HANDOVER_SCHEDULE_DATE", "20261027"),
    ],
)
def test_split_cases_keep_exact_key_and_change_only_comparison_field(
    number, field, expected
):
    with pytest.raises(ValueError, match="variant"):
        plan(number)
    target = plan(number, "target")
    comparison = plan(number, "comparison")
    original = deepcopy(target["rows"]["handover"][0])
    original[field] = target["identifiers"].get(expected, expected)
    assert comparison["rows"]["handover"] == [original]
    assert comparison["execution_scope"] == "status_update_only"


def test_rerun_and_fault_requirements_are_explicit():
    for n in (63, 65):
        p = plan(n)
        assert p["rows"]["handover"][0]["HANDOVER_STATUS"] == "1"
        assert any("2回目" in action for action in p["manual_actions"])
    for n in range(67, 77):
        p = plan(n)
        assert p["fault_injection"]
        assert any("障害注入を実行しない" in action for action in p["manual_actions"])


def test_repeat_insert_and_unrelated_pending_are_rejected(database):
    seed.insert_plan(database[0], plan(30))
    before = {k: read_rows(database, k) for k in seed.TABLE_NAMES}
    with pytest.raises(ValueError, match="未処理予定"):
        seed.insert_plan(database[0], plan(30))
    with pytest.raises(ValueError, match="未処理予定"):
        seed.insert_plan(database[0], plan(20))
    assert {k: read_rows(database, k) for k in seed.TABLE_NAMES} == before


def test_existing_rows_in_absent_table_are_rejected(database):
    p = plan(49)
    existing = plan(30, start_id=p["start_id"])
    existing["rows"]["handover"] = []
    seed.insert_plan(database[0], existing)
    with pytest.raises(ValueError, match="既存行"):
        seed.insert_plan(database[0], p)


def test_failed_last_insert_rolls_back_all_tables(database):
    with database[1].begin() as conn:
        conn.execute(
            text(
                "CREATE TRIGGER reject_handover BEFORE INSERT ON t_sales_user_handover_info "
                "BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
            )
        )
    with pytest.raises(IntegrityError):
        seed.insert_plan(database[0], plan(30))
    assert all(not read_rows(database, k) for k in seed.TABLE_NAMES)


@pytest.mark.parametrize("number", [24, 26, 61, 66])
def test_reset_restores_processed_rows_and_can_be_repeated(database, number):
    prepared = plan(number)
    seed.insert_plan(database[0], prepared, reset=True)
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
    with database[1].begin() as conn:
        for key in seed.HISTORY:
            table = database[2].tables[seed.TABLE_NAMES[key]]
            field = "agreement_org" if key == "F" else "org_id"
            conn.execute(table.update().values({field: prepared["identifiers"]["O2"]}))
        conn.execute(
            text(
                "UPDATE t_sales_user_handover_info SET handover_status = '0', handovered_at = CURRENT_TIMESTAMP"
            )
        )
        conn.execute(text("DELETE FROM m_staff_info"))
        if number == 26:
            conn.execute(text("DELETE FROM t_sales_user_handover_info"))
    for _ in range(2):
        seed.insert_plan(database[0], prepared, reset=True)
        assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before


def test_cleanup_allows_switching_cases_and_keeps_other_corporations(database):
    other = plan(8)
    seed.insert_plan(database[0], other)
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
    prepared = plan(61)
    seed.insert_plan(database[0], prepared)
    counts = seed.insert_plan(database[0], prepared, cleanup=True)
    assert counts == {key: len(rows) for key, rows in prepared["rows"].items()}
    assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before
    assert not any(seed.insert_plan(database[0], prepared, cleanup=True).values())
    seed.insert_plan(database[0], plan(12), reset=True)


@pytest.mark.parametrize("operation", ["reset", "cleanup"])
@pytest.mark.parametrize("creator", [None, "manual"])
def test_reset_and_cleanup_refuse_unowned_rows(database, operation, creator):
    prepared = plan(30)
    seed.insert_plan(database[0], prepared)
    with database[1].begin() as conn:
        table = database[2].tables[seed.TABLE_NAMES["G"]]
        conn.execute(table.update().values(created_by=creator))
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
    with pytest.raises(ValueError, match="準備PG以外"):
        seed.insert_plan(database[0], prepared, **{operation: True})
    assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before


def test_reset_reinsertion_failure_restores_deleted_data(database):
    prepared = plan(61)
    seed.insert_plan(database[0], prepared)
    with database[1].begin() as conn:
        conn.execute(
            text("UPDATE t_sales_user_handover_info SET handover_status = '0'")
        )
        conn.execute(
            text(
                "CREATE TRIGGER reject_reset BEFORE INSERT ON t_sales_user_handover_info "
                "BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
            )
        )
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
    with pytest.raises(IntegrityError):
        seed.insert_plan(database[0], prepared, reset=True)
    assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before


def test_reset_does_not_bypass_other_pending_check(database):
    prepared = plan(8)
    seed.insert_plan(database[0], prepared)
    seed.insert_plan(database[0], plan(61))
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
    with pytest.raises(ValueError, match="未処理予定"):
        seed.insert_plan(database[0], prepared, reset=True)
    assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before


@pytest.mark.parametrize("operation", ["reset", "cleanup"])
def test_cli_repeat_dry_run_is_offline_and_shows_scope(
    tmp_path, monkeypatch, capsys, operation
):
    monkeypatch.setattr(
        seed, "create_engine", lambda *a, **k: pytest.fail("DB接続は不要")
    )
    output = tmp_path / "repeat.json"
    assert (
        seed.main(
            ["--case", "61", f"--{operation}", "--dry-run", "--output", str(output)]
        )
        == 0
    )
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["operation"] == operation
    assert saved["cleanup_scope"]["corporate_numbers"] == [
        "9900000061001",
        "9900000061002",
        "9900000061003",
    ]
    assert saved["cleanup_scope"]["required_created_by"] == seed.SEED_CREATOR
    assert '"mode": "dry-run"' in capsys.readouterr().out


def test_cli_reset_and_cleanup_are_mutually_exclusive():
    with pytest.raises(SystemExit) as error:
        seed.main(["--case", "61", "--reset", "--cleanup", "--dry-run"])
    assert error.value.code == 2


def test_missing_required_column_rejected_before_any_insert(database):
    with database[1].begin() as conn:
        conn.execute(
            text("ALTER TABLE t_sales_user_handover_info DROP COLUMN insert_datetime")
        )
    with pytest.raises(ValueError, match="必須列"):
        seed.insert_plan(database[0], plan(30))
    assert not read_rows(database, "corporate")


@pytest.mark.parametrize("key", ["corporate", "F", "handover"])
def test_missing_table_reports_lookup_name_and_config_key(database, key):
    table_name = seed.TABLE_NAMES[key]
    database[2].tables[table_name].drop(database[1])
    with pytest.raises(ValueError, match="NoSuchTableError") as error:
        seed.insert_plan(database[0], plan(30))
    assert f"見つからないテーブル: {table_name}" in str(error.value)
    assert f"定義取得対象: {table_name}（設定キー: tables.{key}）" in str(error.value)
    assert all(not read_rows(database, k) for k in seed.TABLE_NAMES if k != key)


def test_missing_configured_table_reports_actual_name(database):
    settings = {**database[0], "tables": {"handover": "CUSTOM_HANDOVER"}}
    with pytest.raises(ValueError, match="CUSTOM_HANDOVER") as error:
        seed.insert_plan(settings, plan(30))
    assert "tables.handover" in str(error.value)
    assert all(not read_rows(database, k) for k in seed.TABLE_NAMES)


def test_cli_missing_table_shows_actionable_error_without_connection_url(
    database, tmp_path, monkeypatch, capsys
):
    database[2].tables[seed.TABLE_NAMES["handover"]].drop(database[1])
    settings = {
        **database[0],
        "url": "postgresql://test_user:secret_token@host/test_db",
    }
    config = tmp_path / "database.json"
    config.write_text(json.dumps(settings), encoding="utf-8")
    monkeypatch.setattr(seed, "create_engine", lambda *args, **kwargs: database[1])
    with pytest.raises(SystemExit) as error:
        seed.main(["--case", "30", "--db-config", str(config)])
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert "t_sales_user_handover_info" in captured.err
    assert "tables.handover" in captured.err
    assert "secret_token" not in captured.out + captured.err
    assert "postgresql://" not in captured.out + captured.err
    assert "投入完了" not in captured.out


@pytest.mark.parametrize(
    "field,value",
    [("HANDOVER_TYPE", None), ("HANDOVER_TYPE", "2"), ("HANDOVER_STATUS", "4")],
)
def test_invalid_codes_rejected_without_connecting(field, value):
    prepared = plan(30)
    prepared["rows"]["handover"][0][field] = value
    with pytest.raises(ValueError, match=field):
        seed.insert_plan({"url": "invalid://"}, prepared)


def test_cancelled_handover_is_not_selected_or_status_updated(database):
    prepared = plan(12)
    assert {r["HANDOVER_STATUS"] for r in prepared["rows"]["handover"]} == {
        "0",
        "1",
        "2",
        "3",
    }
    assert len(prepared["rows"]["handover"]) == 6
    cancelled = next(
        r for r in prepared["rows"]["handover"] if r["HANDOVER_STATUS"] == "2"
    )
    cancelled["HANDOVERED_AT"] = datetime(2026, 10, 26, 0, 15)
    seed.insert_plan(database[0], prepared)
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
    with database[1].begin() as conn:
        selected = (
            conn.execute(
                text(
                    (QUERY / "select_sales_user_handover_targets.sql")
                    .read_text(encoding="utf-8")
                    .replace("db_corp.", "main.")
                ),
                {"batch_date": "20261026", "handover_status": "1"},
            )
            .mappings()
            .all()
        )
        assert [r["corporate_number"] for r in selected] == [
            prepared["identifiers"]["C1"]
        ]
        params = {k.lower(): v for k, v in cancelled.items()}
        params.update(batch_date="20261026", planned_status="1")
        sql = text(
            (QUERY / "update_sales_user_handover_status.sql")
            .read_text(encoding="utf-8")
            .replace("db_corp.", "main.")
        )
        for status in ("0", "3"):
            assert (
                conn.execute(sql, {**params, "handover_status": status}).rowcount == 0
            )
    assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before


@pytest.mark.parametrize(
    "kwargs",
    [
        {"case_id": "0"},
        {"case_id": "79"},
        {"case_id": "1", "start_id": 0},
        {"case_id": "1", "start_id": 999701},
        {"case_id": "1", "handover_type": "XX"},
        {"case_id": "1", "handover_type": "2"},
        {"case_id": "1", "handover_type": ""},
        {"case_id": "1", "handover_type": 0},
        {"case_id": "1", "identifiers": {"U1": "x" * 9}},
        {"case_id": "1", "variant": "target"},
    ],
)
def test_invalid_arguments(kwargs):
    with pytest.raises(ValueError):
        seed.build_plan(**kwargs)


def test_custom_identifiers_and_reference_codes():
    p = plan(
        30,
        identifiers={"U1": "USER01", "U2": "USER02", "U3": "USER03"},
        energy_code="010101",
    )
    assert p["rows"]["staff"][0]["USER_ID"] == "USER01"
    assert p["rows"]["A"][0]["ENERGY_CODE"] == "010101"


def test_cli_dry_run_does_not_connect_and_saves_full_plan(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(
        seed, "create_engine", lambda *a, **k: pytest.fail("DB接続は不要")
    )
    output = tmp_path / "plan.json"
    assert seed.main(["--case", "62", "--dry-run", "--output", str(output)]) == 0
    assert '"mode": "dry-run"' in capsys.readouterr().out
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert len(saved["rows"]["handover"]) == 300
    assert {r["HANDOVER_TYPE"] for r in saved["rows"]["handover"]} == {"1"}
    assert "url" not in saved


def test_individual_and_explicit_type():
    assert plan(60)["rows"]["handover"][0]["HANDOVER_TYPE"] == "0"
    prepared = plan(30, handover_type="1")
    assert prepared["rows"]["handover"][0]["HANDOVER_TYPE"] == "1"
    assert prepared["handover_kind"] == "bulk"
