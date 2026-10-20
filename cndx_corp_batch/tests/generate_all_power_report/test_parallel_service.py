"""レポート一括作成ジョブの並列数の計算を検証する。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cndx_corp_batch.common.logger import BatchLogger
from cndx_corp_batch.domains.generate_all_power_report.jobs.generate_all_power_report_job import (
    GenerateAllPowerReportJob,
)


def context():
    return SimpleNamespace(
        batch_id="test", batch_name="electric_vis",
        logger=BatchLogger("test", "electric_vis"),
        config=SimpleNamespace(
            cut_off_day=15,
            report_month_offset_before=3,
            report_month_offset_after=2,
            db_url="postgresql://test",
        ),
    )


def test_worker_count_is_limited_by_target_count(monkeypatch):
    job = GenerateAllPowerReportJob(context(), date(2026, 5, 15))
    job.register_report_job.execute = Mock()
    job.get_report_target_job.execute = Mock(return_value=["one", "two"])
    monkeypatch.setattr("cndx_corp_batch.domains.generate_all_power_report.jobs.generate_all_power_report_job.cpu_workers", lambda: 8)

    class Executor:
        def __init__(self, max_workers, **kwargs):
            assert max_workers == 2

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, *args):
            future = Mock()
            future.result.return_value = None
            return future

    class Manager:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def Queue(self):
            return object()

    with patch("cndx_corp_batch.domains.generate_all_power_report.jobs.generate_all_power_report_job.ProcessPoolExecutor", Executor), patch(
        "cndx_corp_batch.domains.generate_all_power_report.jobs.generate_all_power_report_job.multiprocessing.Manager",
        Manager,
    ), patch("cndx_corp_batch.domains.generate_all_power_report.jobs.generate_all_power_report_job.logging.handlers.QueueListener") as listener:
        job.execute()
    listener.return_value.start.assert_called_once()
    listener.return_value.stop.assert_called_once()
