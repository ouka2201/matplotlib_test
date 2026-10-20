"""対象登録・対象取得ジョブのDB呼び出しを検証する。"""

from contextlib import contextmanager
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cndx_corp_batch.common.logger import BatchLogger
from cndx_corp_batch.domains.generate_all_power_report.jobs.get_power_report_target import (
    GetPowerReportTarget,
)
from cndx_corp_batch.domains.generate_all_power_report.jobs.register_unregistered_report_target_job import (
    RegisterUnregisteredReportTargetJob,
)


def context():
    return SimpleNamespace(
        batch_id="test", batch_name="electric_vis",
        logger=BatchLogger("test", "electric_vis"),
        config=SimpleNamespace(),
    )


def session_factory(session):
    @contextmanager
    def factory():
        yield session

    return factory


def test_register_job_uses_report_month_and_system_user():
    session = Mock()
    with patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.register_unregistered_report_target_job.get_session",
        session_factory(session),
    ), patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.register_unregistered_report_target_job.load_sql_file",
        return_value="INSERT SQL",
    ), patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.register_unregistered_report_target_job.get_sysuser",
        return_value="test-user",
    ), patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.register_unregistered_report_target_job.get_current_time",
        return_value=datetime(2026, 5, 15, 1, 2),
    ):
        RegisterUnregisteredReportTargetJob(context(), date(2026, 3, 1)).run()

    query, params = session.execute.call_args.args
    assert "INSERT SQL" in str(query)
    assert params == {
        "user": "test-user",
        "created_at": datetime(2026, 5, 15, 1, 2),
        "report_ym": "202603",
    }


def test_get_target_job_returns_rows_for_the_requested_month():
    session = Mock()
    session.execute.return_value.all.return_value = [("0001", "C001", False)]
    with patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.get_power_report_target.get_session",
        session_factory(session),
    ), patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.get_power_report_target.load_sql_file",
        return_value="SELECT SQL",
    ):
        result = GetPowerReportTarget(context(), date(2026, 3, 1)).run()

    assert result == [("0001", "C001", False)]
    assert session.execute.call_args.args[1] == {"report_ym": "202603"}
