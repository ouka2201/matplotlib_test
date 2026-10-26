import logging
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from datetime import date
from types import SimpleNamespace

import pytest

from cndx_corp_batch.domains.sales_user_handover.constants import (
    HANDOVER_STATUS_DONE,
    HANDOVER_STATUS_ERROR,
    HANDOVER_STATUS_PLANNED,
)
from cndx_corp_batch.domains.sales_user_handover.jobs import sales_user_handover_job
from cndx_corp_batch.domains.sales_user_handover.jobs.sales_user_handover_job import (
    SalesUserHandoverJob,
)


class FakeResult:
    def __init__(
        self,
        *,
        rows: list[Mapping[str, object]] | None = None,
        first: object = None,
        mapping: Mapping[str, object] | None = None,
    ) -> None:
        self.rows = rows or []
        self.first_row = first
        self.mapping = mapping

    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[Mapping[str, object]]:
        return self.rows

    def first(self) -> object:
        if self.mapping is not None:
            return self.mapping
        return self.first_row


class FakeSession:
    def __init__(
        self,
        *,
        targets: list[Mapping[str, object]] | None = None,
        source_exists: bool = True,
        destination_exists: bool = False,
        data_flags: Mapping[str, object] | None = None,
        fail_on: str | None = None,
    ) -> None:
        self.targets = targets or []
        self.source_exists = source_exists
        self.destination_exists = destination_exists
        self.data_flags = data_flags or {}
        self.fail_on = fail_on
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def execute(
        self,
        statement: object,
        params: Mapping[str, object] | None = None,
    ) -> FakeResult:
        sql = str(statement)
        self.calls.append((sql, params or {}))
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("database error")
        if "SELECT\n    h.corporate_number" in sql:
            return FakeResult(rows=self.targets)
        if "SELECT 1\nFROM db_corp.m_staff_info" in sql:
            if "handover_to_user_id" in sql:
                return FakeResult(first=(1,) if self.destination_exists else None)
            return FakeResult(first=(1,) if self.source_exists else None)
        if "CASE WHEN EXISTS" in sql:
            return FakeResult(mapping=self.data_flags)
        return FakeResult()


class SessionFactory:
    def __init__(self, *sessions: FakeSession) -> None:
        self.sessions = list(sessions)

    @contextmanager
    def _scope(self, session: FakeSession) -> Iterator[FakeSession]:
        yield session

    def __call__(self) -> AbstractContextManager[FakeSession]:
        if not self.sessions:
            raise AssertionError("想定外のDBセッション取得")
        return self._scope(self.sessions.pop(0))


def make_context() -> SimpleNamespace:
    logger = logging.getLogger("sales-user-handover-test")
    return SimpleNamespace(
        logger=SimpleNamespace(logger=logger, extra={}),
        batch_id="test-batch",
        batch_name="BLMMGMGHANDOVER",
    )


def make_target(report_data_flg: bool = True) -> dict[str, object]:
    return {
        "corporate_number": "1234567890123",
        "handover_from_org_id": "ORG001",
        "handover_from_user_id": "USER001",
        "handover_to_org_id": "ORG002",
        "handover_to_user_id": "USER002",
        "report_data_flg": report_data_flg,
    }


def all_data_flags(**overrides: object) -> dict[str, object]:
    flags = {
        "monthly_building": 1,
        "annual_building": 1,
        "monthly_corporate": 1,
        "annual_corporate": 1,
        "report_storage": 1,
        "building": 1,
        "cn_application": 1,
        "building_info": 1,
    }
    flags.update(overrides)
    return flags


def test_no_target_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    target_session = FakeSession()
    monkeypatch.setattr(
        sales_user_handover_job, "get_session", SessionFactory(target_session)
    )

    result = SalesUserHandoverJob(make_context(), date(2026, 12, 21)).execute()

    assert result == 0
    assert target_session.calls[0][1] == {
        "batch_date": "20261221",
        "handover_status": HANDOVER_STATUS_PLANNED,
    }


def test_report_data_flag_false_updates_staff_and_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = make_target(report_data_flg=False)
    target_session = FakeSession(targets=[target])
    process_session = FakeSession(source_exists=True)
    monkeypatch.setattr(
        sales_user_handover_job,
        "get_session",
        SessionFactory(target_session, process_session),
    )

    result = SalesUserHandoverJob(make_context(), date(2026, 12, 21)).execute()

    assert result == 1
    assert any("UPDATE db_corp.m_staff_info" in sql for sql, _ in process_session.calls)
    status_calls = [
        params for sql, params in process_session.calls if "handovered_at" in sql
    ]
    assert status_calls[0]["handover_status"] == HANDOVER_STATUS_DONE
    assert not any("CASE WHEN EXISTS" in sql for sql, _ in process_session.calls)


def test_missing_source_staff_deletes_handover_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_session = FakeSession(targets=[make_target()])
    process_session = FakeSession(source_exists=False)
    monkeypatch.setattr(
        sales_user_handover_job,
        "get_session",
        SessionFactory(target_session, process_session),
    )

    SalesUserHandoverJob(make_context(), date(2026, 12, 21)).execute()

    assert any(
        "DELETE FROM db_corp.t_sales_user_handover_info" in sql
        for sql, _ in process_session.calls
    )
    assert not any("handovered_at" in sql for sql, _ in process_session.calls)


def test_existing_destination_staff_deletes_source_staff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_session = FakeSession(targets=[make_target(report_data_flg=False)])
    process_session = FakeSession(source_exists=True, destination_exists=True)
    monkeypatch.setattr(
        sales_user_handover_job,
        "get_session",
        SessionFactory(target_session, process_session),
    )

    SalesUserHandoverJob(make_context(), date(2026, 12, 21)).execute()

    assert any(
        "DELETE FROM db_corp.m_staff_info" in sql for sql, _ in process_session.calls
    )
    assert not any(
        "UPDATE db_corp.m_staff_info" in sql for sql, _ in process_session.calls
    )


def test_missing_past_data_sets_registration_error_without_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_session = FakeSession(targets=[make_target()])
    process_session = FakeSession(
        source_exists=True,
        data_flags=all_data_flags(building=0),
    )
    monkeypatch.setattr(
        sales_user_handover_job,
        "get_session",
        SessionFactory(target_session, process_session),
    )

    SalesUserHandoverJob(make_context(), date(2026, 12, 21)).execute()

    status_calls = [
        params for sql, params in process_session.calls if "handovered_at" in sql
    ]
    assert status_calls[0]["handover_status"] == HANDOVER_STATUS_ERROR
    assert not any(
        "SET org_id" in sql and "m_staff_info" not in sql
        for sql, _ in process_session.calls
    )


def test_missing_non_building_data_updates_existing_rows_and_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_session = FakeSession(targets=[make_target()])
    process_session = FakeSession(
        source_exists=True,
        data_flags=all_data_flags(building_info=0),
    )
    monkeypatch.setattr(
        sales_user_handover_job,
        "get_session",
        SessionFactory(target_session, process_session),
    )

    SalesUserHandoverJob(make_context(), date(2026, 12, 21)).execute()

    org_updates = [
        sql
        for sql, _ in process_session.calls
        if "SET org_id" in sql and "m_staff_info" not in sql
    ]
    assert len(org_updates) == 6
    assert not any(
        "UPDATE db_corp.t_building_info" in sql for sql, _ in process_session.calls
    )
    status_calls = [
        params for sql, params in process_session.calls if "handovered_at" in sql
    ]
    assert status_calls[0]["handover_status"] == HANDOVER_STATUS_DONE


def test_all_past_data_is_updated_and_target_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_session = FakeSession(targets=[make_target()])
    process_session = FakeSession(source_exists=True, data_flags=all_data_flags())
    monkeypatch.setattr(
        sales_user_handover_job,
        "get_session",
        SessionFactory(target_session, process_session),
    )

    SalesUserHandoverJob(make_context(), date(2026, 12, 21)).execute()

    org_updates = [
        sql
        for sql, _ in process_session.calls
        if "SET org_id" in sql and "m_staff_info" not in sql
    ]
    assert len(org_updates) == 7
    assert any("SET agreement_org" in sql for sql, _ in process_session.calls)
    status_calls = [
        params for sql, params in process_session.calls if "handovered_at" in sql
    ]
    assert status_calls[0]["handover_status"] == HANDOVER_STATUS_DONE


def test_database_error_records_error_status_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_session = FakeSession(targets=[make_target()])
    process_session = FakeSession(
        source_exists=True, fail_on="UPDATE db_corp.m_staff_info"
    )
    error_session = FakeSession()
    monkeypatch.setattr(
        sales_user_handover_job,
        "get_session",
        SessionFactory(target_session, process_session, error_session),
    )

    with pytest.raises(RuntimeError, match="database error"):
        SalesUserHandoverJob(make_context(), date(2026, 12, 21)).execute()

    status_calls = [
        params for sql, params in error_session.calls if "handovered_at" in sql
    ]
    assert status_calls[0]["handover_status"] == HANDOVER_STATUS_ERROR
