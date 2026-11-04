"""データ準備PGを外部DBに接続せず検証する。"""

import importlib.util
from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text

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
                "org_name TEXT, delete_flg BOOLEAN)"
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
                "INSERT INTO db_corp.m_user_organization_info VALUES "
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
