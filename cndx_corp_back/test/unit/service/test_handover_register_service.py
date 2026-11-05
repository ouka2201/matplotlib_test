from contextlib import contextmanager
from typing import Iterator

import pytest
from sqlalchemy.sql.elements import TextClause

from cndx_corp_back.logic.contact_person.handover_validation_logic import (
    validate_handover,
)
from cndx_corp_back.service.contact_person import handover_register_service

CONTEXT = {
    "user_id": "00000001",
    "org_id": "00000000000000000001",
    "org_type_code": "01",
    "role": "0",
}
DATA = {
    "handover_from_org_id": "00000000000000000002",
    "handover_from_user_id": "00000002",
    "handover_to_org_id": "00000000000000000003",
    "handover_to_user_id": "00000003",
    "handover_schedule_date": "20261221",
    "report_data_flg": True,
    "handover_type": "0",
    "corp_number_list": ["1234567890123"],
    "user_id": CONTEXT["user_id"],
    "org_id": CONTEXT["org_id"],
}


def test_handover_validation_rejects_wrong_role_and_spoofed_registrant() -> None:
    with pytest.raises(PermissionError):
        validate_handover(DATA, {**CONTEXT, "role": "1"}, "0")
    with pytest.raises(PermissionError):
        validate_handover({**DATA, "user_id": "00000099"}, CONTEXT, "0")


@pytest.mark.parametrize("handover_type", ["0", "1"])
def test_handover_validation_accepts_lowercase_user_ids(handover_type: str) -> None:
    context = {**CONTEXT, "user_id": "user01"}
    data = {
        **DATA,
        "user_id": "user01",
        "handover_from_user_id": "sales01",
        "handover_to_user_id": "Sales02",
        "handover_type": handover_type,
    }
    validate_handover(data, context, handover_type)
    with pytest.raises(PermissionError):
        validate_handover({**data, "user_id": "USER01"}, context, handover_type)


@pytest.mark.parametrize("user_id", ["", "123456789", "user 01", "ユーザー", None, 1])
def test_handover_validation_rejects_invalid_user_ids(user_id: object) -> None:
    with pytest.raises(ValueError, match="user_idが不正"):
        validate_handover({**DATA, "user_id": user_id}, CONTEXT, "0")


def test_handover_validation_checks_date_and_company_number() -> None:
    with pytest.raises(ValueError):
        validate_handover({**DATA, "handover_schedule_date": "20260230"}, CONTEXT, "0")
    with pytest.raises(ValueError):
        validate_handover({**DATA, "corp_number_list": ["bad"]}, CONTEXT, "0")
    assert validate_handover(DATA, CONTEXT, "0") == ["1234567890123"]


class Result:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    def scalars(self) -> "Result":
        return self

    def all(self) -> list[str]:
        return self.values

    def first(self) -> str | None:
        return self.values[0] if self.values else None

    def __iter__(self) -> Iterator[str]:
        return iter(self.values)


class Session:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute(self, statement: TextClause, params: dict) -> Result:
        sql = str(statement)
        self.calls.append((sql, params))
        if "FROM db_corp.m_staff_info" in sql:
            return Result(["1234567890123"])
        if "SELECT corporate_number FROM db_corp.t_sales_user_handover_info" in sql:
            return Result(["9999999999999"])
        if "INSERT INTO" in sql:
            return Result([params["corporate_number"]])
        return Result([])


def test_individual_registration_removes_only_unselected_plans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Session()

    @contextmanager
    def scoped_session() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(handover_register_service, "get_scoped_session", scoped_session)
    handover_register_service.register_handover(DATA, CONTEXT, "0")
    inserts = [(sql, params) for sql, params in session.calls if "INSERT INTO" in sql]
    deletes = [(sql, params) for sql, params in session.calls if "DELETE FROM" in sql]
    assert len(inserts) == 1
    assert inserts[0][1]["corporate_number"] == "1234567890123"
    assert len(deletes) == 1
    assert deletes[0][1]["corporate_number"] == "9999999999999"
    assert "handover_status = :status" in deletes[0][0]
    assert deletes[0][1]["status"] == "1"


def test_bulk_registration_uses_assigned_companies_without_deleting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Session()

    @contextmanager
    def scoped_session() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(handover_register_service, "get_scoped_session", scoped_session)
    handover_register_service.register_handover(
        {**DATA, "handover_type": "1"}, CONTEXT, "1"
    )
    assert sum("INSERT INTO" in sql for sql, _ in session.calls) == 1
    assert not any("DELETE FROM" in sql for sql, _ in session.calls)


def test_completed_handover_cannot_be_overwritten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CompletedSession(Session):
        def execute(self, statement: TextClause, params: dict) -> Result:
            if "INSERT INTO" in str(statement):
                return Result([])
            return super().execute(statement, params)

    session = CompletedSession()

    @contextmanager
    def scoped_session() -> Iterator[Session]:
        yield session

    monkeypatch.setattr(handover_register_service, "get_scoped_session", scoped_session)
    with pytest.raises(ValueError, match="実施済み"):
        handover_register_service.register_handover(DATA, CONTEXT, "0")
    assert not any("DELETE FROM" in sql for sql, _ in session.calls)
