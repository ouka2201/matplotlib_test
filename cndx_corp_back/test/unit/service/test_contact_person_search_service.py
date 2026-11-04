"""実際の検索SQLをインメモリDBで検証する（外部DBは変更しない）。"""

from contextlib import contextmanager
from typing import Iterator

import pytest
from sqlalchemy import Connection, create_engine, text

from cndx_corp_back.service.contact_person import search_service


@pytest.fixture
def search_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Connection]:
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.execute(text("ATTACH DATABASE ':memory:' AS db_corp"))
        connection.execute(
            text(
                "CREATE TABLE db_corp.m_user_organization_info "
                "(org_id TEXT, org_name TEXT, delete_flg BOOLEAN)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE db_corp.m_user (user_id TEXT, org_id TEXT, "
                "user_name TEXT, email_address TEXT, delete_flg BOOLEAN)"
            )
        )
        for org_id, name, deleted in [
            ("BNK0001001", "A銀行", False),
            ("BNK0001002", "A銀行", False),
            ("BNK0002001", "B銀行", False),
            ("REP0001", "C組織", False),
            ("BNK0001003", "削除組織", True),
        ]:
            connection.execute(
                text(
                    "INSERT INTO db_corp.m_user_organization_info "
                    "VALUES (:id, :name, :del)"
                ),
                {"id": org_id, "name": name, "del": deleted},
            )
        for user_id, org_id, name, email, deleted in [
            ("00000001", "BNK0001001", "B担当", "sales1@example.com", False),
            ("00000002", "BNK0001002", "A担当", "sales2@example.com", False),
            ("00000003", "BNK0002001", "他行担当", "sales3@example.com", False),
            ("00000004", "REP0001", "一般担当", "a_b%z@example.com", False),
            ("00000005", "BNK0001001", "削除担当", "sales5@example.com", True),
            ("00000006", "BNK0001003", "削除組織担当", "sales6@example.com", False),
        ]:
            connection.execute(
                text(
                    "INSERT INTO db_corp.m_user VALUES (:id, :org, :name, :email, :del)"
                ),
                {
                    "id": user_id,
                    "org": org_id,
                    "name": name,
                    "email": email,
                    "del": deleted,
                },
            )

        @contextmanager
        def session_scope() -> Iterator[Connection]:
            yield connection

        monkeypatch.setattr(search_service, "get_scoped_session", session_scope)
        yield connection
    engine.dispose()


def _search(query: str, search_type: str = "email_address", bank: bool = False) -> list:
    context = {
        "org_id": "BNK0001000" if bank else "EP0001",
        "org_type_code": "02" if bank else "01",
        "role": "9" if bank else "0",
    }
    data = {
        "org_id": context["org_id"],
        "org_type_code": context["org_type_code"],
        "user_role": context["role"],
        "search_query": query,
        "search_type": search_type,
    }
    return search_service.search_managers(data, context)


def test_ep_search_and_sort(search_db: Connection) -> None:
    rows = _search("sales")
    assert [row["user_id"] for row in rows] == ["00000002", "00000001", "00000003"]
    assert set(rows[0]) == {
        "email_address",
        "company_name",
        "org_id",
        "user_name",
        "user_id",
    }


def test_bank_search_is_scoped_for_both_modes(search_db: Connection) -> None:
    assert [row["user_id"] for row in _search("sales", bank=True)] == [
        "00000002",
        "00000001",
    ]
    assert len(_search("銀行", "all", bank=True)) == 2
    assert _search("他行担当", "all", bank=True) == []


def test_search_modes_and_no_match(search_db: Connection) -> None:
    assert _search("A担当") == []
    assert len(_search("A担当", "all")) == 1
    assert len(_search("B銀行", "all")) == 1
    assert _search("存在しない") == []


def test_query_is_literal_and_bound(search_db: Connection) -> None:
    assert len(_search("_b%")) == 1
    assert _search("' OR 1=1 --") == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("org_id", "BNK0002000"),
        ("org_type_code", "01"),
        ("user_role", "0"),
    ],
)
def test_spoofed_authority_is_rejected(field: str, value: str) -> None:
    context = {"org_id": "BNK0001000", "org_type_code": "02", "role": "9"}
    data = {
        "org_id": "BNK0001000",
        "org_type_code": "02",
        "user_role": "9",
        "search_query": "sales",
        "search_type": "all",
        field: value,
    }
    with pytest.raises(PermissionError):
        search_service.search_managers(data, context)


def test_invalid_role_and_search_type() -> None:
    with pytest.raises(PermissionError):
        search_service.search_managers({}, {})
    with pytest.raises(ValueError):
        _search("sales", "invalid")
