"""実運用側の変換・DB更新・バッチ制御を、外部接続なしで検証する。"""

import logging
import os
import queue
import sys
import tempfile
import unittest
from concurrent.futures import Future
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cndx_corp_batch.common.config import load_config
from cndx_corp_batch.common.logger import BatchLogger
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import calc_offset_month
from cndx_corp_batch.domains.generate_all_power_report.jobs import (
    generate_all_power_report_job as jobs,
    get_power_report_target as target_job,
    register_unregistered_report_target_job as registration,
)
from cndx_corp_batch.domains.generate_all_power_report.services import (
    create_power_report_service as worker,
)
from cndx_corp_batch.domains.generate_all_power_report.services.database_source import SLOTS
from cndx_corp_batch.domains.generate_all_power_report.services.report_service import ReportService
from cndx_corp_batch.domains.generate_all_power_report.services.chart_service import ChartService
from cndx_corp_batch.domains.generate_all_power_report.rendering.canvas import SecondPageCanvas
from cndx_corp_batch.domains.generate_all_power_report.rendering.styles import WIDTH, HEIGHT
from cndx_corp_batch.entrypoints import generate_all_power_report as entrypoint


def context():
    return SimpleNamespace(
        batch_id="test",
        batch_name="power-report",
        logger=BatchLogger("test", "power-report"),
        config=SimpleNamespace(
            db_url="sqlite://",
            cut_off_day=15,
            report_month_offset_before=3,
            report_month_offset_after=2,
        ),
    )


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.enterContext(patch.dict(os.environ, {"REPORT_OUTPUT_DIR": self.folder.name}))
        self.service = Mock()
        self.enterContext(patch.object(worker, "_report_service", self.service))
        self.enterContext(patch.object(worker, "get_session", self.session))
        self.enterContext(patch.dict(worker._SQL_QUERIES, {
            "select_cust": text(load_sql_file("select_power_report_cust.sql")),
            "select_30min": text(load_sql_file("select_power_report_30min.sql")),
            "update_target": text(load_sql_file("update_power_report_target.sql")),
        }, clear=True))
        with self.engine.begin() as connection:
            connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS db_corp")
            connection.exec_driver_sql("""CREATE TABLE db_corp.t_arve_customer_info (
                cmn_supplypointspecificnum__c TEXT PRIMARY KEY,
                cmn_demandlocationfullname_ref__c TEXT,
                cmn_demandlocationaddress__c TEXT, cmn_oldcustomernum__c TEXT,
                cmn_kigyoid_fk__c TEXT, recordtypeid TEXT)""")
            connection.exec_driver_sql("""CREATE TABLE db_corp.t_ep_contracted_power (
                qsqb_dcis2_spl_pt_spc_no TEXT PRIMARY KEY, qsqb_dcis2_hvpw_ctrt TEXT)""")
            columns = ", ".join(f"{column} TEXT" for column in SLOTS)
            connection.exec_driver_sql(f"""CREATE TABLE db_corp.t_ep_electricity_data_30min (
                t01_kyo_ctn_tok_no TEXT, t01_get_ymd TEXT, {columns},
                PRIMARY KEY (t01_kyo_ctn_tok_no, t01_get_ymd))""")
            connection.exec_driver_sql("""CREATE TABLE db_corp.t_power_report_mng_info (
                supply_point_number TEXT, target_year_month TEXT, company_id TEXT,
                syousapo_flg BOOLEAN, file_name TEXT DEFAULT '', file_path TEXT DEFAULT '',
                report_created_at TEXT, create_status TEXT, error_message TEXT DEFAULT '',
                created_by TEXT, created_at TEXT, updated_by TEXT, updated_at TEXT,
                PRIMARY KEY (supply_point_number, target_year_month))""")
            connection.exec_driver_sql("""CREATE TABLE db_corp.t_30min_import_mng (
                supply_point_number TEXT, target_year_month TEXT, create_status TEXT)""")
        self.target = self.seed("0001", joined=True)

    @contextmanager
    def session(self):
        with Session(self.engine) as session:
            with session.begin():
                yield session

    def seed(self, point, joined):
        with self.engine.begin() as connection:
            connection.execute(text("""INSERT INTO db_corp.t_arve_customer_info VALUES
                (:point, 'テスト工場', '東京都', '000-001', '001', :recordtype)"""),
                {"point": point, "recordtype": "省エネサポートサービス" if joined else "通常"})
            connection.execute(text("INSERT INTO db_corp.t_ep_contracted_power VALUES (:point, '200')"), {"point": point})
            connection.execute(text("""INSERT INTO db_corp.t_power_report_mng_info
                (supply_point_number,target_year_month,company_id,syousapo_flg,create_status,created_at)
                VALUES (:point,'202607','001',:joined,'2','2026-08-01')"""), {"point": point, "joined": joined})
            connection.execute(text("INSERT INTO db_corp.t_30min_import_mng VALUES (:point,'202607','3')"), {"point": point})
            columns = ",".join(["t01_kyo_ctn_tok_no", "t01_get_ymd", *SLOTS])
            placeholders = ",".join([":point", ":day", *[f":v{i}" for i in range(48)]])
            for day in ("20260701", "20260702", "20260801"):
                connection.execute(text(f"INSERT INTO db_corp.t_ep_electricity_data_30min ({columns}) VALUES ({placeholders})"),
                    {"point": point, "day": day, **{f"v{i}": "50" for i in range(48)}})
        return SimpleNamespace(supply_point_number=point, company_id="001", syousapo_flg=joined)

    def stored(self, point="0001"):
        with self.engine.connect() as connection:
            return dict(connection.execute(text("SELECT * FROM db_corp.t_power_report_mng_info WHERE supply_point_number=:point"), {"point": point}).mappings().one())

    def test_joined_and_unjoined_names_and_period(self):
        other = self.seed("0002", joined=False)
        for target, suffix in [(self.target, "_syousapo"), (other, "")]:
            with self.subTest(joined=target.syousapo_flg):
                worker.execute(target, date(2026, 7, 1))
                row = self.stored(target.supply_point_number)
                name = f"001_{target.supply_point_number}{suffix}_202607.pdf"
                self.assertEqual(row["file_name"], name)
                self.assertEqual(row["file_path"], str(Path(self.folder.name, name)))
                self.assertEqual(row["create_status"], "3")
                frame = self.service.generate_frame.call_args.kwargs["df"]
                self.assertEqual(len(frame), 96)
                self.assertTrue((frame.kw == 100).all())

    def test_numeric_failure_keeps_warning_and_logs_key(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql("UPDATE db_corp.t_ep_electricity_data_30min SET t01_30t_syr02='bad' WHERE t01_get_ymd='20260702'")
        with self.assertLogs("batch.worker", level="WARNING") as logs:
            worker.execute(self.target, date(2026, 7, 1))
        row = self.stored()
        self.assertEqual(row["create_status"], "4")
        self.assertEqual(row["error_message"], "数値変換エラー：20260702")
        self.service.generate_frame.assert_not_called()
        self.assertIn("LMMRCRC0401", logs.output[0])
        self.assertIn("主キー=20260702", logs.output[0])
        self.assertIn("T01_30T_SYR02", logs.output[0])

    def test_contract_conversion_warning_does_not_repeat_supply_point(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql("UPDATE db_corp.t_ep_contracted_power SET qsqb_dcis2_hvpw_ctrt='bad'")
        with self.assertLogs("batch.worker", level="WARNING") as logs:
            worker.execute(self.target, date(2026, 7, 1))
        self.assertEqual(self.stored()["create_status"], "4")
        self.assertEqual(self.stored()["error_message"], "数値変換エラー：")
        self.assertIn("contract_kw", logs.output[0])
        self.service.generate_frame.assert_not_called()

    def test_unexpected_error_recorded_and_next_target_succeeds(self):
        other = self.seed("0002", joined=False)
        self.service.generate_frame.side_effect = [OSError("x" * 150), None]
        with self.assertLogs("batch.worker", level="ERROR"):
            self.assertIsNone(worker.execute(self.target, date(2026, 7, 1)))
        self.assertEqual(self.stored()["create_status"], "5")
        self.assertEqual(self.stored()["error_message"], "x" * 97 + "...")
        worker.execute(other, date(2026, 7, 1))
        self.assertEqual(self.stored("0002")["create_status"], "3")

    def test_rendering_value_error_is_unexpected_not_conversion_warning(self):
        self.service.generate_frame.side_effect = ValueError("layout error")
        with self.assertLogs("batch.worker", level="ERROR"):
            worker.execute(self.target, date(2026, 7, 1))
        self.assertEqual(self.stored()["create_status"], "5")

    def test_customer_query_failure_keeps_existing_handling(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql("DELETE FROM db_corp.t_ep_contracted_power")
        with self.assertRaises(NoResultFound):
            worker.execute(self.target, date(2026, 7, 1))
        self.assertEqual(self.stored()["create_status"], "2")
        self.assertEqual(self.stored()["error_message"], "")

    def test_registration_and_target_fetch_use_real_sql(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql("DELETE FROM db_corp.t_power_report_mng_info")
        with patch.object(registration, "get_session", self.session):
            job = registration.RegisterUnregisteredReportTargetJob(context(), date(2026, 7, 1))
            job.execute()
            job.execute()
        with patch.object(target_job, "get_session", self.session):
            rows = target_job.GetPowerReportTarget(context(), date(2026, 7, 1)).execute()
        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].supply_point_number, "0001")
        self.assertTrue(rows[0].syousapo_flg)


class BatchControlTests(unittest.TestCase):
    def test_date_boundary_and_year_rollover(self):
        for day, expected in [(14, (2026, 2)), (15, (2026, 3)), (16, (2026, 3))]:
            with self.subTest(day=day):
                result = calc_offset_month(date(2026, 5, day), 15, 3, 2)
                self.assertEqual((result.year, result.month), expected)
        result = calc_offset_month(date(2026, 1, 15), 15, 3, 2)
        self.assertEqual((result.year, result.month), (2025, 11))

    def test_numeric_environment_settings(self):
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite://", "CUT_OFF_DAY": "15", "REPORT_MONTH_OFFSET_BEFORE": "3", "REPORT_MONTH_OFFSET_AFTER": "2"}, clear=True):
            config = load_config()
        self.assertEqual((config.cut_off_day, config.report_month_offset_before, config.report_month_offset_after), (15, 3, 2))
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite://", "CUT_OFF_DAY": "invalid"}):
            with self.assertRaises(ValueError):
                load_config()

    def test_registration_precedes_empty_target_exit(self):
        job = jobs.GenerateAllPowerReportJob(context(), batch_date=date(2026, 9, 15))
        calls = Mock()
        job.register_report_job.execute = calls.register
        job.get_report_target_job.execute = calls.targets
        calls.targets.return_value = []
        with patch.object(jobs.multiprocessing, "Manager") as manager, patch.object(jobs, "ProcessPoolExecutor") as pool:
            job.execute()
        self.assertEqual([call[0] for call in calls.mock_calls], ["register", "targets"])
        self.assertEqual(job.report_ymd, date(2026, 7, 15))
        manager.assert_not_called()
        pool.assert_not_called()

    def test_worker_failure_does_not_stop_later_targets(self):
        job = jobs.GenerateAllPowerReportJob(context(), batch_date=date(2026, 9, 15))
        job.register_report_job.execute = Mock()
        job.get_report_target_job.execute = Mock(return_value=["first", "second"])
        job.logger = Mock()
        first, second = Future(), Future()
        first.set_exception(RuntimeError("query failed"))
        second.set_result(None)
        manager = MagicMock()
        manager.__enter__.return_value.Queue.return_value = queue.Queue()
        pool = MagicMock()
        pool.__enter__.return_value.submit.side_effect = [first, second]
        with patch.object(jobs.multiprocessing, "Manager", return_value=manager), patch.object(jobs, "ProcessPoolExecutor", return_value=pool), patch.object(jobs.logging.handlers, "QueueListener") as listener:
            self.assertIsNone(job.execute())
        self.assertEqual(pool.__enter__.return_value.submit.call_count, 2)
        job.logger.exception.assert_called_once()
        listener.return_value.stop.assert_called_once()
        manager.__exit__.assert_called_once()

    def test_entrypoint_accepts_execution_date_and_closes_context(self):
        ctx = Mock()
        with patch.object(entrypoint, "load_config"), patch.object(entrypoint, "BatchContext", return_value=ctx), patch.object(entrypoint, "setup_logging"), patch.object(entrypoint, "GenerateAllPowerReportJob") as job:
            self.assertEqual(entrypoint.main(["--batch-date", "2026-05-15"]), 0)
        job.assert_called_once_with(ctx, batch_date=date(2026, 5, 15))
        ctx.close.assert_called_once()

    def test_worker_finalizer_registered_and_cleanup_closes_both_resources(self):
        service = Mock()
        logger = logging.getLogger("batch.worker")
        handlers, level, propagate = logger.handlers[:], logger.level, logger.propagate
        self.addCleanup(setattr, logger, "handlers", handlers)
        self.addCleanup(setattr, logger, "level", level)
        self.addCleanup(setattr, logger, "propagate", propagate)
        with patch.object(worker, "init_db"), patch.object(worker, "ReportService", return_value=service), patch.object(worker, "Finalize") as finalize, patch.object(worker, "_report_service", None):
            worker.multiprocessing_initializer("sqlite://", queue.Queue())
            finalize.assert_called_once_with(None, worker.close_worker, exitpriority=10)
            service.close.side_effect = RuntimeError("close failed")
            with patch.object(worker, "close_db") as close_db:
                with self.assertRaises(RuntimeError):
                    worker.close_worker()
            close_db.assert_called_once()
            self.assertIsNone(worker._report_service)

    def test_report_close_does_not_reference_removed_font_service(self):
        service = ReportService.__new__(ReportService)
        service.printer = Mock()
        service.close()
        service.printer.close.assert_called_once()


class AdviceLayoutTests(unittest.TestCase):
    def setUp(self):
        ChartService()
        self.page = SecondPageCanvas()
        self.addCleanup(plt.close, self.page.fig)

    def test_standard_advice_fits_at_minimum_font_size(self):
        self.page.note(96.2, 179.5, 81.9, 11.2, [
            "年間を通じて日中を中心に電気を使用しており、",
            "かつ土・日曜日も使用している場合、",
            "特に太陽光発電システムの導入が効果的です",
        ], advice=True)
        item = self.page.canvas.texts[-1]
        self.assertGreaterEqual(item.get_fontsize(), 5.5)
        self.page.fig.canvas.draw()
        box = item.get_window_extent(self.page.fig.canvas.get_renderer())
        frame = self.page.canvas.get_window_extent()
        self.assertLessEqual(box.width / frame.width * WIDTH, 77.9)
        self.assertLessEqual(box.height / frame.height * HEIGHT, 8.2)

    def test_text_that_really_overflows_is_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "説明欄が長すぎ"):
            self.page.note(96.2, 179.5, 81.9, 11.2, ["説明文" * 200])


if __name__ == "__main__":
    unittest.main()
