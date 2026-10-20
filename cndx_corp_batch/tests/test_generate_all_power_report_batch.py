"""電力見える化レポート一括作成バッチの自動テスト。"""

from contextlib import contextmanager
from datetime import date, datetime
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from cndx_corp_batch.common import db
from cndx_corp_batch.common.logger import BatchLogger
from cndx_corp_batch.domains.generate_all_power_report.jobs import (
    generate_all_power_report_job as job_module,
)
from cndx_corp_batch.domains.generate_all_power_report.services import (
    create_power_report_service as worker_module,
    report_service as report_service_module,
)
from cndx_corp_batch.domains.generate_all_power_report.services.database_source import (
    NumericConversionError,
)
from cndx_corp_batch.domains.generate_all_power_report.services.query_result_service import (
    prepare_query_results,
)
from cndx_corp_batch.domains.generate_all_power_report.services.report_service import (
    ReportService,
)


def make_context():
    config = SimpleNamespace(
        cut_off_day=15,
        report_month_offset_before=3,
        report_month_offset_after=2,
        db_url="postgresql://test",
    )
    return SimpleNamespace(
        config=config,
        batch_id="test-batch",
        batch_name="electric_vis",
        logger=BatchLogger("test-batch", "electric_vis"),
    )


def target(point="0000000000000000000001", company="C001", syousapo=False):
    return SimpleNamespace(
        supply_point_number=point,
        company_id=company,
        syousapo_flg=syousapo,
    )


@pytest.mark.parametrize(
    ("run_day", "expected"),
    [(date(2026, 5, 14), "202602"), (date(2026, 5, 15), "202603")],
)
def test_batch_date_selects_the_designated_report_month(run_day, expected):
    job = job_module.GenerateAllPowerReportJob(make_context(), run_day)
    assert job.report_ymd.strftime("%Y%m") == expected


def test_empty_target_does_not_start_worker_pool(monkeypatch, caplog):
    job = job_module.GenerateAllPowerReportJob(make_context(), date(2026, 5, 15))
    job.register_report_job.execute = Mock()
    job.get_report_target_job.execute = Mock(return_value=[])
    pool = Mock(side_effect=AssertionError("対象0件ではワーカーを起動しない"))
    monkeypatch.setattr(job_module, "ProcessPoolExecutor", pool)

    with caplog.at_level(logging.INFO, logger="batch"):
        assert job.execute() is None

    pool.assert_not_called()
    assert "作成対象は0件です" in caplog.text


class _FakeFuture:
    def __init__(self, row, failed=False):
        self.row = row
        self.failed = failed

    def result(self):
        if self.failed:
            raise RuntimeError("個別対象の失敗")
        return None


class _FakeExecutor:
    instances = []

    def __init__(self, max_workers, initializer, initargs):
        self.max_workers = max_workers
        self.initializer = initializer
        self.initargs = initargs
        self.submitted = []
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, function, row, report_month):
        self.submitted.append((function, row, report_month))
        return _FakeFuture(row, row.supply_point_number == "bad")


class _FakeManager:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def Queue(self):
        return object()


class _FakeListener:
    def __init__(self, queue, handler):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_each_target_is_submitted_once_and_error_does_not_stop_later_targets(
    monkeypatch, caplog
):
    _FakeExecutor.instances.clear()
    rows = [target("ok-1"), target("bad"), target("ok-2")]
    job = job_module.GenerateAllPowerReportJob(make_context(), date(2026, 5, 15))
    job.register_report_job.execute = Mock()
    job.get_report_target_job.execute = Mock(return_value=rows)
    monkeypatch.setattr(job_module, "cpu_workers", lambda: 8)
    monkeypatch.setattr(job_module, "ProcessPoolExecutor", _FakeExecutor)
    monkeypatch.setattr(job_module.multiprocessing, "Manager", _FakeManager)
    monkeypatch.setattr(job_module.logging.handlers, "QueueListener", _FakeListener)

    with caplog.at_level(logging.INFO, logger="batch"):
        job.execute()

    executor = _FakeExecutor.instances[0]
    assert executor.max_workers == 3
    assert [row.supply_point_number for _, row, _ in executor.submitted] == [
        "ok-1",
        "bad",
        "ok-2",
    ]
    assert "タスク 2/3 エラー" in caplog.text
    assert "タスク 3/3 処理終了" in caplog.text


class _Result:
    def __init__(self, customer=None, daily=None):
        self.customer = customer
        self.daily = daily
        self.updated = []

    def mappings(self):
        return self

    def one(self):
        return self.customer

    def all(self):
        return self.daily


def fake_worker_session(customer, daily, updated):
    @contextmanager
    def session_context():
        class Session:
            def execute(self, query, params):
                if query == "customer":
                    return _Result(customer=customer)
                if query == "daily":
                    return _Result(daily=daily)
                updated.append(params.copy())
                return _Result()

        yield Session()

    return session_context


def run_worker(monkeypatch, tmp_path, row, prepare_side_effect=None, render_side_effect=None):
    updated = []
    worker_module._SQL_QUERIES.clear()
    worker_module._SQL_QUERIES.update(
        select_cust="customer", select_30min="daily", update_target="update"
    )
    customer = {"customer_name": "テスト企業", "address": "東京都", "customer_number": "001", "contract_kw": 100}
    daily = [{"T01_GET_YMD": "20260301", **{f"T01_30T_SYR{i:02d}": "1" for i in range(1, 49)}}]
    service = Mock()
    if render_side_effect:
        service.generate_frame.side_effect = render_side_effect
    monkeypatch.setattr(worker_module, "get_session", fake_worker_session(customer, daily, updated))
    monkeypatch.setattr(worker_module, "get_current_time", lambda: datetime(2026, 5, 15, 1, 2, 3))
    monkeypatch.setattr(worker_module, "get_sysuser", lambda: "test-user")
    monkeypatch.setattr(worker_module, "_report_service", service)
    if prepare_side_effect is not None:
        monkeypatch.setattr(worker_module, "prepare_query_results", Mock(side_effect=prepare_side_effect))
    else:
        monkeypatch.setattr(worker_module, "prepare_query_results", Mock(return_value=("frame", {"target_month": "202603"})))
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))
    worker_module.execute(row, date(2026, 3, 1))
    return updated, service


def test_worker_success_uses_joined_filename_and_status_three(monkeypatch, tmp_path):
    updated, service = run_worker(
        monkeypatch, tmp_path, target("0001", "C001", True)
    )
    params = updated[0]
    assert params["file_name"] == "C001_0001_syousapo_202603.pdf"
    assert params["file_path"] == str(Path(tmp_path) / params["file_name"])
    assert params["create_status"] == "3"
    assert params["error_message"] == ""
    service.generate_frame.assert_called_once_with(
        df="frame", config={"target_month": "202603"},
        output=Path(tmp_path) / "C001_0001_syousapo_202603.pdf", debug_dir=None
    )


def test_worker_numeric_error_sets_warning_status_and_skips_pdf(monkeypatch, tmp_path, caplog):
    updated, service = run_worker(
        monkeypatch,
        tmp_path,
        target("0002", "C002"),
        prepare_side_effect=NumericConversionError("20260301", "T01_30T_SYR01"),
    )
    params = updated[0]
    assert params["create_status"] == "4"
    assert params["error_message"] == "数値変換エラー：20260301"
    service.generate_frame.assert_not_called()
    assert "LMMRCRC0401" in caplog.text


def test_worker_unexpected_error_sets_error_status_with_100_character_message(
    monkeypatch, tmp_path, caplog
):
    updated, service = run_worker(
        monkeypatch,
        tmp_path,
        target("0003", "C003"),
        render_side_effect=RuntimeError("x" * 200),
    )
    params = updated[0]
    assert params["create_status"] == "5"
    assert len(params["error_message"]) == 100
    assert params["error_message"].endswith("...")
    assert "レポート作成エラー" in caplog.text


def test_query_result_conversion_expands_48_half_hour_slots_and_reports_bad_column():
    customer = {
        "customer_name": "企業", "address": "住所", "customer_number": "001", "contract_kw": "100"
    }
    row = {"T01_GET_YMD": "20260301", **{f"T01_30T_SYR{i:02d}": str(i) for i in range(1, 49)}}
    frame, config = prepare_query_results(customer, [row], "0001", "202603")
    assert len(frame) == 48
    assert frame.iloc[0].kw == 2
    assert frame.iloc[-1].timestamp.strftime("%H:%M") == "23:30"
    assert config["contract_kw"] == 100.0

    row["T01_30T_SYR17"] = "不正値"
    with pytest.raises(NumericConversionError) as error:
        prepare_query_results(customer, [row], "0001", "202603")
    assert error.value.primary_key == "20260301"
    assert error.value.column == "T01_30T_SYR17"


def test_report_service_writes_only_the_requested_pdf(tmp_path, monkeypatch):
    service = ReportService.__new__(ReportService)
    service.charts = Mock()
    service.charts.create_all.return_value = {"first_page": "data:image/png;base64,one"}
    service.html = Mock()
    service.html.render.return_value = "<html>report</html>"
    service.printer = Mock()
    service.printer.print_html.return_value = b"%PDF-test"
    monkeypatch.setattr(report_service_module, "validate_data", lambda frame, month: frame)
    monkeypatch.setattr(report_service_module, "build_context", lambda frame, config: (config, {"df": frame}))
    output = tmp_path / "report.pdf"

    result = ReportService.generate_frame(
        service, object(), {"target_month": "202603"}, output
    )

    assert result == {"status": "succeeded", "output": str(output), "bytes": 9}
    assert output.read_bytes() == b"%PDF-test"
    service.printer.print_html.assert_called_once_with("<html>report</html>")


def test_db_session_commits_on_success_and_rolls_back_on_error():
    sessions = []

    class Session:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0
            self.closed = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

        def close(self):
            self.closed += 1

    def factory():
        session = Session()
        sessions.append(session)
        return session

    with patch.object(db, "_Session", factory):
        with db.get_session():
            pass
        with pytest.raises(RuntimeError, match="rollback"):
            with db.get_session():
                raise RuntimeError("rollback")

    assert sessions[0].commits == 1 and sessions[0].rollbacks == 0
    assert sessions[1].commits == 0 and sessions[1].rollbacks == 1
    assert all(session.closed == 1 for session in sessions)
