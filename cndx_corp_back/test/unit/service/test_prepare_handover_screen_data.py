"""データ準備PGを外部DBに接続せず検証する。"""

import importlib.util
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Engine,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)

from cndx_corp_back.query.contact_person_search_query import SELECT_HANDOVER_MANAGERS

SPEC = importlib.util.spec_from_file_location(
    "handover_screen_seed",
    Path(__file__).parents[2] / "prepare_handover_screen_data.py",
)
seed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seed)


@pytest.fixture
def engine() -> Iterator[Engine]:
    database = create_engine("sqlite://")
    with database.begin() as connection:
        connection.execute(text("ATTACH DATABASE ':memory:' AS db_corp"))
        connection.execute(
            text(
                "CREATE TABLE db_corp.m_user_organization_info "
                "(org_id TEXT PRIMARY KEY, org_type_code TEXT, "
                "org_name TEXT, delete_flg BOOLEAN, company_name TEXT, "
                "parent_org_id TEXT, created_by TEXT, created_at TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE db_corp.m_user (user_id TEXT PRIMARY KEY, org_id TEXT, "
                "user_role TEXT, email_address TEXT UNIQUE, user_name TEXT, "
                "company_name TEXT, delete_flg BOOLEAN, created_by TEXT, "
                "created_at TIMESTAMP, user_password TEXT)"
            )
        )
        connection.execute(text("CREATE TABLE db_corp.m_staff_info (user_id TEXT)"))
        connection.execute(
            text(
                "CREATE TABLE db_corp.t_sales_user_handover_info "
                "(handover_from_user_id TEXT, handover_to_user_id TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO db_corp.m_user_organization_info "
                "(org_id, org_type_code, org_name, delete_flg) VALUES "
                "('BNK0001000','02','本店',false), ('BNK0001001','03','支店',false), "
                "('BNK0002000','02','他行',false)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO db_corp.m_user (user_id, org_id, user_role, delete_flg) "
                "VALUES ('00000001','BNK0001000','9',false)"
            )
        )
    yield database
    database.dispose()


def _args(*flags: str) -> object:
    return seed.parse_args(
        [
            "--login-user-id",
            "00000001",
            "--from-org-id",
            "BNK0001000",
            "--to-org-id",
            "BNK0001001",
            *flags,
        ]
    )


def _count(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM db_corp.m_user")
        ).scalar_one()


def test_dry_run_apply_search_repeat_cleanup(engine: Engine) -> None:
    seed.run(_args(), engine)
    assert _count(engine) == 1
    seed.run(_args("--apply"), engine)
    seed.run(_args("--apply"), engine)
    assert _count(engine) == 3
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text(SELECT_HANDOVER_MANAGERS),
                {
                    "pattern": "%handover-%",
                    "is_ep_admin": False,
                    "bank_pattern": "BNK0001%",
                    "search_all": False,
                },
            )
            .mappings()
            .all()
        )
        assert {row["user_id"] for row in rows} == {"99009001", "99009002"}
    seed.run(_args("--cleanup"), engine)
    assert _count(engine) == 1


def test_collision_does_not_overwrite_or_partially_insert(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO db_corp.m_user (user_id, created_by) "
                "VALUES ('99009002','other')"
            )
        )
    with pytest.raises(ValueError, match="衝突"):
        seed.run(_args("--apply"), engine)
    assert _count(engine) == 2
    with pytest.raises(ValueError, match="衝突"):
        seed.run(_args("--cleanup"), engine)
    assert _count(engine) == 2


def test_other_bank_rejected(engine: Engine) -> None:
    args = _args("--apply")
    args.to_org_id = "BNK0002000"
    with pytest.raises(ValueError, match="同一金融機関"):
        seed.run(args, engine)
    assert _count(engine) == 1


def test_in_use_cleanup_rejected(engine: Engine) -> None:
    seed.run(_args("--apply"), engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO db_corp.t_sales_user_handover_info "
                "VALUES ('99009001','99009002')"
            )
        )
    with pytest.raises(ValueError, match="使用中"):
        seed.run(_args("--cleanup"), engine)
    assert _count(engine) == 3


def test_login_id_cannot_be_seed_target() -> None:
    with pytest.raises(SystemExit):
        _args("--from-user-id", "00000001")


def _new_org_args(*flags: str) -> object:
    return _args(
        "--create-organizations",
        "--from-org-id",
        "BNK0001901",
        "--to-org-id",
        "BNK0001902",
        *flags,
    )


def _org_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM db_corp.m_user_organization_info")
        ).scalar_one()


def test_create_organizations_repeat_search_cleanup(engine: Engine) -> None:
    seed.run(_new_org_args(), engine)
    assert _org_count(engine) == 3
    seed.run(_new_org_args("--apply"), engine)
    seed.run(_new_org_args("--apply"), engine)
    assert _org_count(engine) == 5
    with engine.connect() as connection:
        rows = connection.execute(
            text(SELECT_HANDOVER_MANAGERS),
            {
                "pattern": "%handover-%",
                "is_ep_admin": False,
                "bank_pattern": "BNK0001%",
                "search_all": False,
            },
        ).all()
        assert len(rows) == 2
    seed.run(_new_org_args("--cleanup"), engine)
    seed.run(_new_org_args("--cleanup"), engine)
    assert _org_count(engine) == 3
    assert _count(engine) == 1


def test_existing_org_not_overwritten(engine: Engine) -> None:
    with pytest.raises(ValueError, match="衝突"):
        seed.run(_new_org_args("--to-org-id", "BNK0001001", "--apply"), engine)
    assert _org_count(engine) == 3
    assert _count(engine) == 1


def test_other_org_reference_rolls_back_cleanup(engine: Engine) -> None:
    seed.run(_new_org_args("--apply"), engine)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE db_corp.example_business (creator_org_id TEXT)")
        )
        connection.execute(
            text("INSERT INTO db_corp.example_business VALUES ('BNK0001901')")
        )
    with pytest.raises(ValueError, match="使用中"):
        seed.run(_new_org_args("--cleanup"), engine)
    assert _org_count(engine) == 5
    assert _count(engine) == 3


def test_new_org_user_collision_leaves_no_organizations(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO db_corp.m_user (user_id, created_by) "
                "VALUES ('99009002','other')"
            )
        )
    with pytest.raises(ValueError, match="衝突"):
        seed.run(_new_org_args("--apply"), engine)
    assert _org_count(engine) == 3


def test_new_org_outside_bank_rejected(engine: Engine) -> None:
    with pytest.raises(ValueError, match="同一金融機関"):
        seed.run(_new_org_args("--to-org-id", "BNK0002901", "--apply"), engine)
    assert _org_count(engine) == 3


def test_same_organization_created_once(engine: Engine) -> None:
    args = _new_org_args("--to-org-id", "BNK0001901", "--apply")
    seed.run(args, engine)
    assert _org_count(engine) == 4
    assert _count(engine) == 3
    args.apply = False
    args.cleanup = True
    seed.run(args, engine)
    assert _org_count(engine) == 3


@pytest.fixture
def business_engine(engine: Engine) -> Engine:
    from cndx_corp_batch.test.prepare_sales_user_handover_cases import TABLE_NAMES

    metadata = MetaData()
    entity_dir = Path(__file__).parents[3] / "entity"
    for name in [n for k, n in TABLE_NAMES.items() if k != "handover"] + [
        "m_corporate_details_info"
    ]:
        spec = importlib.util.spec_from_file_location(
            name, entity_dir / f"{name}_entity.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        next(iter(module.Base.metadata.tables.values())).to_metadata(metadata)
    Table(
        "t_sales_user_handover_info",
        metadata,
        Column("corporate_number", String(13), primary_key=True),
        Column("handover_from_org_id", String(20), primary_key=True),
        Column("handover_from_user_id", String(8), primary_key=True),
        *[
            Column(n, String(20))
            for n in (
                "handover_to_org_id",
                "handover_to_user_id",
                "handover_schedule_date",
                "handover_status",
                "handover_type",
                "creator_id",
                "creator_org_id",
                "created_by",
                "updated_by",
            )
        ],
        Column("report_data_flg", Boolean),
        *[
            Column(n, DateTime)
            for n in ("handovered_at", "insert_datetime", "created_at", "updated_at")
        ],
        schema="db_corp",
    )
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE db_corp.m_staff_info"))
        connection.execute(text("DROP TABLE db_corp.t_sales_user_handover_info"))
        metadata.create_all(connection)
    return engine


@pytest.mark.parametrize("has_reports", [False, True])
def test_screen_registration_and_batch_sql(
    business_engine: Engine, monkeypatch: pytest.MonkeyPatch, has_reports: bool
) -> None:
    from cndx_corp_back.service.contact_person import handover_register_service
    from cndx_corp_batch.domains.sales_user_handover.constants import (
        HANDOVER_DATA_QUERY_FILES,
    )

    args = _new_org_args(
        "--with-business-data", "--apply", "--schedule-date", "2026-12-21"
    )
    seed.run(args, business_engine)
    args.apply = False
    args.verify_stage = "registered"
    with pytest.raises(ValueError, match="2法人"):
        seed.run(args, business_engine)
    with business_engine.begin() as connection:

        @contextmanager
        def scope() -> Iterator:
            yield connection

        monkeypatch.setattr(handover_register_service, "get_scoped_session", scope)
        handover_register_service.register_handover(
            {
                "handover_from_org_id": args.from_org_id,
                "handover_from_user_id": args.from_user_id,
                "handover_to_org_id": args.to_org_id,
                "handover_to_user_id": args.to_user_id,
                "handover_type": "1",
                "handover_schedule_date": "20261221",
                "report_data_flg": has_reports,
                "user_id": "00000001",
                "org_id": "BNK0001000",
            },
            {
                "user_id": "00000001",
                "org_id": "BNK0001000",
                "org_type_code": "02",
                "role": "9",
            },
            "1",
        )
    assert "確認OK" in seed.run(args, business_engine)
    query_dir = Path(__file__).parents[4] / "cndx_corp_batch/query"
    with business_engine.begin() as connection:
        targets = (
            connection.execute(
                text(
                    (query_dir / "select_sales_user_handover_targets.sql").read_text(
                        encoding="utf-8"
                    )
                ),
                {"handover_status": "1", "batch_date": "20261221"},
            )
            .mappings()
            .all()
        )
        assert len(targets) == 2
        for target in targets:
            params = {
                **target,
                "handover_status": "0",
                "planned_status": "1",
                "batch_date": "20261221",
            }
            files = ["update_handover_staff.sql"]
            if has_reports:
                files += list(HANDOVER_DATA_QUERY_FILES.values())
            files += ["update_sales_user_handover_status.sql"]
            for file in files:
                connection.execute(
                    text((query_dir / file).read_text(encoding="utf-8")), params
                )
    args.verify_stage = "completed"
    assert "確認OK" in seed.run(args, business_engine)
    args.verify_stage = None
    args.cleanup = True
    seed.run(args, business_engine)
    assert _count(business_engine) == 1
    assert _org_count(business_engine) == 3


def test_business_failure_rolls_back_new_users_and_orgs(
    business_engine: Engine,
) -> None:
    with business_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO db_corp.m_corporate_basic "
                "(corporate_number, created_by) VALUES ('9900000900001','other')"
            )
        )
    with pytest.raises(ValueError, match="準備PG以外"):
        seed.run(_new_org_args("--with-business-data", "--apply"), business_engine)
    assert _count(business_engine) == 1
    assert _org_count(business_engine) == 3


def test_business_same_org_dry_run_and_cleanup(business_engine: Engine) -> None:
    args = _new_org_args("--with-business-data", "--to-org-id", "BNK0001901")
    seed.run(args, business_engine)
    assert _count(business_engine) == 1
    assert _org_count(business_engine) == 3
    args.apply = True
    seed.run(args, business_engine)
    assert _count(business_engine) == 3
    assert _org_count(business_engine) == 4
    args.apply = False
    args.cleanup = True
    seed.run(args, business_engine)
    assert _count(business_engine) == 1
    assert _org_count(business_engine) == 3
