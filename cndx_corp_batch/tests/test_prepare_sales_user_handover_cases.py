"""投入内容・実DB列への適合・投入失敗時の原子性を検証する。"""

import importlib.util
import json
import re
from contextlib import contextmanager
from datetime import date, datetime
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
def plan(number, **kwargs):
    return seed.build_plan(str(number), **kwargs)


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
    assert [c["number"] for c in cases] == list(range(1, 49))
    assert [c["source_row"] for c in cases] == list(range(7, 55))
    assert all(c["category"] != "状態更新条件" for c in cases)
    assert all(c["category"] != "例外・トランザクション" for c in cases)
    assert cases[41]["title"] == "個別引継ぎ1法人"
    assert cases[45]["title"] == "業務エラー後の次法人"


def test_case22_prepares_monthly_building_rows_and_required_building_master():
    prepared = plan(22)
    assert prepared["title"] == "月別建物エネルギー情報の更新範囲"
    assert prepared["rows"]["handover"][0]["REPORT_DATA_FLG"] is True
    assert {key: len(prepared["rows"][key]) for key in seed.HISTORY} == {
        "A": 5,
        "B": 0,
        "C": 0,
        "D": 0,
        "E": 0,
        "F": 1,
        "G": 0,
        "H": 0,
    }
    target = prepared["identifiers"]["C1"]
    source_org = prepared["identifiers"]["O1"]
    assert (
        sum(
            row["CORPORATE_NUMBER"] == target and row["ORG_ID"] == source_org
            for row in prepared["rows"]["A"]
        )
        == 2
    )
    building = prepared["rows"]["F"][0]
    assert building["CORPORATE_NUMBER"] == target
    assert building["AGREEMENT_ORG"] == source_org


def test_renumbered_case_text_uses_the_generated_identifiers():
    for case in seed.load_catalog()["cases"]:
        prepared = seed.build_plan(case["case_id"])
        assert prepared["start_id"] == case["number"] * 1000 + 1
        ids = set(prepared["identifiers"].values())
        description = "\n".join(case[k] for k in ("data", "procedure", "expected"))
        referenced = set(re.findall(r"9900000\d{6}|[OU]\d{7}", description))
        assert referenced <= ids, (case["number"], referenced - ids)


@pytest.mark.parametrize("number", range(1, 49))
def test_every_case_inserts_against_existing_entity_definitions(database, number):
    prepared = plan(number)
    assert all(
        row["HANDOVER_TYPE"] == ("1" if number == 43 else "0")
        for row in prepared["rows"]["handover"]
    )
    counts = seed.insert_plan(database[0], prepared)
    assert counts == {key: len(read_rows(database, key)) for key in seed.TABLE_NAMES}


@pytest.mark.parametrize(
    "number,expected",
    [
        (3, 0),
        (2, 1),
        (4, 1),
        (43, 3),
        (45, 0),
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
    "number,order", [(5, (2, 1, 3)), (6, (2, 1, 3)), (7, (1, 2, 3))]
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
    assert values == expected if number != 7 else set(values) == set(expected)


@pytest.mark.parametrize(
    "number,key,filename",
    [
        (22, "A", "monthly_building"),
        (24, "B", "annual_building"),
        (26, "C", "monthly_corporate"),
        (28, "D", "annual_corporate"),
        (30, "E", "report_storage"),
        (32, "F", "building"),
        (33, "G", "cn_application"),
        (35, "H", "building_info"),
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
    for n in (16,):
        p = plan(n)
        assert all(r["USER_ID"] != p["identifiers"]["U1"] for r in p["rows"]["staff"])
    p = plan(17)
    assert [r["CORPORATE_NUMBER"] for r in p["rows"]["staff"]] == [
        p["identifiers"]["C2"],
        p["identifiers"]["C2"],
    ]
    for n, key in seed.MISSING_CASES.items():
        assert {k: len(plan(n)["rows"][k]) for k in seed.HISTORY} == {
            k: int(k != key) for k in seed.HISTORY
        }
    for n in (38, 40, 46):
        p = plan(n)
        assert not any(
            r["CORPORATE_NUMBER"] == p["identifiers"]["C1"] for r in p["rows"]["F"]
        )
    p = plan(39)
    assert p["rows"]["F"][0]["AGREEMENT_ORG"] == p["identifiers"]["O3"]


@pytest.mark.parametrize(
    "number,destination_other_corp",
    [(16, False), (17, False), (47, False), (48, False), (47, True)],
)
def test_missing_source_behavior_with_real_sql(
    database, monkeypatch, number, destination_other_corp
):
    from cndx_corp_batch.domains.sales_user_handover.jobs import sales_user_handover_job
    from cndx_corp_batch.tests.test_sales_user_handover import make_context

    prepared = plan(number)
    if destination_other_corp:
        other_corp = str(int(prepared["identifiers"]["C1"]) + 1)
        prepared["rows"]["corporate"].append(
            {**prepared["rows"]["corporate"][0], "CORPORATE_NUMBER": other_corp}
        )
        prepared["rows"]["staff"][0]["CORPORATE_NUMBER"] = other_corp
    seed.insert_plan(database[0], prepared)
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}

    @contextmanager
    def sqlite_session():
        with database[1].begin() as connection:

            class Session:
                def execute(self, statement, params):
                    return connection.execute(
                        text(str(statement).replace("db_corp.", "")), params
                    )

            yield Session()

    monkeypatch.setattr(sales_user_handover_job, "get_session", sqlite_session)
    count = sales_user_handover_job.SalesUserHandoverJob(
        make_context(), date(2026, 10, 26)
    ).execute()
    assert count == (2 if number == 16 else 1)
    remaining = read_rows(database, "handover")
    assert read_rows(database, "corporate") == before["corporate"]
    if number == 16:
        assert len(remaining) == 1
        assert remaining[0]["corporate_number"] == prepared["identifiers"]["C2"]
        assert remaining[0]["handover_status"] == "0"
        assert (
            read_rows(database, "staff")[0]["user_id"] == prepared["identifiers"]["U2"]
        )
    elif number == 17 or destination_other_corp:
        assert not remaining
        assert read_rows(database, "staff") == before["staff"]
    else:
        assert len(remaining) == 1
        assert remaining[0]["handover_status"] == "0"
        assert remaining[0]["handovered_at"] is not None
        assert read_rows(database, "staff") == before["staff"]
    for key in seed.HISTORY:
        expected = [dict(row) for row in before[key]]
        if number == 48:
            for row in expected:
                row["agreement_org" if key == "F" else "org_id"] = prepared[
                    "identifiers"
                ]["O2"]
        assert read_rows(database, key) == expected
    if number == 16:
        completed = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
        assert (
            sales_user_handover_job.SalesUserHandoverJob(
                make_context(), date(2026, 10, 26)
            ).execute()
            == 0
        )
        assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == completed


@pytest.mark.parametrize("number", [12, 13, 14])
def test_staff_update_preserves_org_and_other_columns(database, number):
    prepared = plan(number)
    seed.insert_plan(database[0], prepared)
    before = read_rows(database, "staff")
    ids = prepared["identifiers"]
    sql = (QUERY / "update_handover_staff.sql").read_text(encoding="utf-8")
    with database[1].begin() as connection:
        result = connection.execute(
            text(sql.replace("db_corp.", "main.")),
            {
                "corporate_number": ids["C1"],
                "handover_from_user_id": ids["U1"],
                "handover_to_user_id": ids["U2"],
                "handover_to_org_id": ids["O2"],
            },
        )
        assert result.rowcount == 1
    expected = [
        dict(row, user_id=ids["U2"])
        if row["corporate_number"] == ids["C1"] and row["user_id"] == ids["U1"]
        else dict(row)
        for row in before
    ]
    order = lambda row: (row["corporate_number"], row["user_id"])
    assert sorted(read_rows(database, "staff"), key=order) == sorted(
        expected, key=order
    )


def test_staff_control_rows_and_nullable_flag():
    for number, expected in [
        (12, ("C2", "U1")),
        (13, ("C1", "U3")),
        (15, ("C1", "U2")),
    ]:
        p = plan(number)
        row = p["rows"]["staff"][1]
        assert (row["CORPORATE_NUMBER"], row["USER_ID"]) == tuple(
            p["identifiers"][v] for v in expected
        )
    assert plan(21)["rows"]["handover"][0]["REPORT_DATA_FLG"] is None
    assert [r["REPORT_DATA_FLG"] for r in plan(43)["rows"]["handover"]] == [
        True,
        False,
        True,
    ]


@pytest.mark.parametrize(
    "number,time",
    [(8, "00:58:59"), (9, "00:59:00"), (10, "00:59:59"), (11, "01:00:00")],
)
def test_cutoff_timestamps(number, time):
    assert plan(number)["rows"]["handover"][0][
        "INSERT_DATETIME"
    ] == datetime.fromisoformat(f"2026-10-26T{time}")


def test_rerun_requirements_are_explicit():
    for n in (16, 44):
        p = plan(n)
        assert p["rows"]["handover"][0]["HANDOVER_STATUS"] == "1"
        assert any("2回目" in action for action in p["manual_actions"])


def test_repeat_insert_and_unrelated_pending_are_rejected(database):
    seed.insert_plan(database[0], plan(19))
    before = {k: read_rows(database, k) for k in seed.TABLE_NAMES}
    with pytest.raises(ValueError, match="未処理予定"):
        seed.insert_plan(database[0], plan(19))
    with pytest.raises(ValueError, match="未処理予定"):
        seed.insert_plan(database[0], plan(14))
    assert {k: read_rows(database, k) for k in seed.TABLE_NAMES} == before


def test_existing_rows_in_absent_table_are_rejected(database):
    p = plan(38)
    existing = plan(19, start_id=p["start_id"])
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
        seed.insert_plan(database[0], plan(19))
    assert all(not read_rows(database, k) for k in seed.TABLE_NAMES)


@pytest.mark.parametrize("number", [15, 16, 43, 46])
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
        if number == 16:
            conn.execute(text("DELETE FROM t_sales_user_handover_info"))
    for _ in range(2):
        seed.insert_plan(database[0], prepared, reset=True)
        assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before


def test_cleanup_allows_switching_cases_and_keeps_other_corporations(database):
    other = plan(45)
    seed.insert_plan(database[0], other)
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
    prepared = plan(43)
    seed.insert_plan(database[0], prepared)
    counts = seed.insert_plan(database[0], prepared, cleanup=True)
    assert counts == {key: len(rows) for key, rows in prepared["rows"].items()}
    assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before
    assert not any(seed.insert_plan(database[0], prepared, cleanup=True).values())
    seed.insert_plan(database[0], plan(4), reset=True)


@pytest.mark.parametrize("operation", ["reset", "cleanup"])
@pytest.mark.parametrize("creator", [None, "manual"])
def test_reset_and_cleanup_refuse_unowned_rows(database, operation, creator):
    prepared = plan(19)
    seed.insert_plan(database[0], prepared)
    with database[1].begin() as conn:
        table = database[2].tables[seed.TABLE_NAMES["G"]]
        conn.execute(table.update().values(created_by=creator))
    before = {key: read_rows(database, key) for key in seed.TABLE_NAMES}
    with pytest.raises(ValueError, match="準備PG以外"):
        seed.insert_plan(database[0], prepared, **{operation: True})
    assert {key: read_rows(database, key) for key in seed.TABLE_NAMES} == before


def test_reset_reinsertion_failure_restores_deleted_data(database):
    prepared = plan(43)
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
    prepared = plan(45)
    seed.insert_plan(database[0], prepared)
    seed.insert_plan(database[0], plan(43))
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
            [
                "--case",
                str(43),
                f"--{operation}",
                "--dry-run",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["operation"] == operation
    assert saved["cleanup_scope"]["corporate_numbers"] == [
        "9900000043001",
        "9900000043002",
        "9900000043003",
    ]
    assert saved["cleanup_scope"]["required_created_by"] == seed.SEED_CREATOR
    assert '"mode": "dry-run"' in capsys.readouterr().out


def test_cli_reset_and_cleanup_are_mutually_exclusive():
    with pytest.raises(SystemExit) as error:
        seed.main(["--case", str(43), "--reset", "--cleanup", "--dry-run"])
    assert error.value.code == 2


def test_missing_required_column_rejected_before_any_insert(database):
    with database[1].begin() as conn:
        conn.execute(
            text("ALTER TABLE t_sales_user_handover_info DROP COLUMN insert_datetime")
        )
    with pytest.raises(ValueError, match="必須列"):
        seed.insert_plan(database[0], plan(19))
    assert not read_rows(database, "corporate")


@pytest.mark.parametrize("key", ["corporate", "F", "handover"])
def test_missing_table_reports_lookup_name_and_config_key(database, key):
    table_name = seed.TABLE_NAMES[key]
    database[2].tables[table_name].drop(database[1])
    with pytest.raises(ValueError, match="NoSuchTableError") as error:
        seed.insert_plan(database[0], plan(19))
    assert f"見つからないテーブル: {table_name}" in str(error.value)
    assert f"定義取得対象: {table_name}（設定キー: tables.{key}）" in str(error.value)
    assert all(not read_rows(database, k) for k in seed.TABLE_NAMES if k != key)


def test_missing_configured_table_reports_actual_name(database):
    settings = {**database[0], "tables": {"handover": "CUSTOM_HANDOVER"}}
    with pytest.raises(ValueError, match="CUSTOM_HANDOVER") as error:
        seed.insert_plan(settings, plan(19))
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
        seed.main(["--case", str(19), "--db-config", str(config)])
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
    prepared = plan(19)
    prepared["rows"]["handover"][0][field] = value
    with pytest.raises(ValueError, match=field):
        seed.insert_plan({"url": "invalid://"}, prepared)


def test_cancelled_handover_is_not_selected_or_status_updated(database):
    prepared = plan(4)
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
        {"case_id": "49"},
        {"case_id": "1", "start_id": 0},
        {"case_id": "1", "start_id": 999701},
        {"case_id": "1", "handover_type": "XX"},
        {"case_id": "1", "handover_type": "2"},
        {"case_id": "1", "handover_type": ""},
        {"case_id": "1", "handover_type": 0},
        {"case_id": "1", "identifiers": {"U1": "x" * 9}},
    ],
)
def test_invalid_arguments(kwargs):
    with pytest.raises(ValueError):
        seed.build_plan(**kwargs)


def test_custom_identifiers_and_reference_codes():
    p = plan(
        19,
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
    assert seed.main(["--case", str(43), "--dry-run", "--output", str(output)]) == 0
    assert '"mode": "dry-run"' in capsys.readouterr().out
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert len(saved["rows"]["handover"]) == 3
    assert {r["HANDOVER_TYPE"] for r in saved["rows"]["handover"]} == {"1"}
    assert "url" not in saved


def test_individual_and_explicit_type():
    assert plan(42)["rows"]["handover"][0]["HANDOVER_TYPE"] == "0"
    prepared = plan(19, handover_type="1")
    assert prepared["rows"]["handover"][0]["HANDOVER_TYPE"] == "1"
    assert prepared["handover_kind"] == "bulk"
