"""管理テーブルの1件ずつの着手・状態更新・並列投入を検証する。"""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from sqlalchemy import Boolean, Column, DateTime, MetaData, String, Table, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import batch
from services.database_source import POINT, DATE, SLOTS, CONTRACT_POINT, CONTRACT_POWER
from services.report_job_source import (
    ReportJobSource,
    MANAGEMENT_POINT,
    MANAGEMENT_MONTH,
    STATUS,
    normalize_report_ym,
)

POINT_VALUE = "0000000000000000000001"


def claim_in_process(settings, target):
    """別プロセス内でDBを開き、同じ対象の着手を試みる。

    Args:
        settings (dict): テスト用SQLite接続の環境変数名とテーブル設定。
        target (dict): 管理テーブルの取得レコード。

    Returns:
        bool: このプロセスが着手できたか。
    """
    source = ReportJobSource(settings)
    try:
        claimed = source.claim(target)
        if claimed:
            # 2が対象なので、処理権を保持したまま完了させてから解放する。
            path = (
                Path(
                    os.environ["REPORT_JOBS_TEST_URL"].removeprefix("sqlite:///")
                ).parent
                / "test.pdf"
            )
            path.write_bytes(b"saved PDF bytes")
            source.finish(target, output=path)
        return claimed
    finally:
        source.close()


class ReportJobsTests(unittest.TestCase):
    """実SQLiteと実プロセスで、主キー・状態・顧客情報の分離を確認する。"""

    def setUp(self):
        """管理・ARVE・契約電力・48枠テーブルを一時DBに作る。"""
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.settings = {
            "schema": None,
            "url_env": "REPORT_JOBS_TEST_URL",
            "customer_filters": {"CMN_BusinessType__c": "2"},
        }
        self.environment = patch.dict(
            os.environ,
            {"REPORT_JOBS_TEST_URL": f"sqlite:///{self.root / 'jobs.sqlite'}"},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.source = ReportJobSource(self.settings)
        self.addCleanup(self.source.close)
        metadata = MetaData()
        self.management = Table(
            "t_power_report_mng_info",
            metadata,
            Column(MANAGEMENT_POINT, String(27), primary_key=True),
            Column(MANAGEMENT_MONTH, String(6), primary_key=True),
            Column("COMPANY_ID", String(14)),
            Column("SYOUSAPO_FLG", Boolean),
            Column(STATUS, String(1)),
            Column("ERROR_MESSAGE", String(100)),
            Column("FILE_NAME", String(255)),
            Column("FILE_PATH", String(255)),
            Column("REPORT_CREATED_AT", DateTime),
            Column("CREATED_BY", String(50)),
            Column("CREATED_AT", DateTime),
            Column("UPDATED_BY", String(50)),
            Column("UPDATED_AT", DateTime),
        )
        self.name_column = "CMN_DemandLocationFullName_Ref__c"
        self.customer = Table(
            "t_arve_customer_info",
            metadata,
            Column("CMN_SupplyPointSpecificNum__c", String(22)),
            Column("CMN_BusinessType__c", String(4)),
            Column(self.name_column, String(130)),
            Column("CMN_DemandLocationAddress__c", String(130)),
            Column("CMN_OldCustomerNum__c", String(16)),
        )
        self.daily = Table(
            "t_ep_electricity_data_30min",
            metadata,
            Column(POINT, String(22)),
            Column(DATE, String(8)),
            *[Column(name, String(9)) for name in SLOTS],
        )
        self.contract = Table(
            "t_ep_contracted_power",
            metadata,
            Column(CONTRACT_POINT, String(22)),
            Column(CONTRACT_POWER, String(10)),
        )
        metadata.create_all(self.source.engine)
        self.config_path = self.root / "config.json"
        self.base_config = {
            "notes": "共通注記",
            "customer_name": "使ってはいけない名義",
        }
        self.config_path.write_text(json.dumps(self.base_config), encoding="utf-8")

    def insert_target(self, month="202606", status="2", point=POINT_VALUE, joined=True):
        """主キー・状態が指定された管理レコードを登録する。

        Args:
            month (str): 管理テーブルのYYYYMM。
            status (str): 作成状態。
            point (str): 供給地点。
            joined (bool): 省サポ加入フラグ。

        Returns:
            dict: 対象取得と同じ形式のレコード。
        """
        target = {
            "supply_point": point,
            "target_year_month": month,
            "company_id": "COMPANY0000001",
            "syousapo_flg": joined,
        }
        with self.source.engine.begin() as connection:
            connection.execute(
                self.management.insert(),
                {
                    MANAGEMENT_POINT: point,
                    MANAGEMENT_MONTH: month,
                    "COMPANY_ID": target["company_id"],
                    "SYOUSAPO_FLG": joined,
                    STATUS: status,
                    "ERROR_MESSAGE": "previous",
                    "FILE_NAME": "old.pdf",
                },
            )
        return target

    def read_target(self, month="202606", point=POINT_VALUE):
        """管理レコードの実DB値を読み直す。

        Args:
            month (str): 対象年月。
            point (str): 供給地点。

        Returns:
            dict: テーブルの全列の値。
        """
        with self.source.engine.connect() as connection:
            return dict(
                connection.execute(
                    select(self.management).where(
                        self.management.c[MANAGEMENT_MONTH] == month,
                        self.management.c[MANAGEMENT_POINT] == point,
                    )
                )
                .mappings()
                .one()
            )

    def prepare_customer(self):
        """ARVE契約情報と1日だけのkWh実績を登録する。"""
        with self.source.engine.begin() as connection:
            connection.execute(
                self.customer.insert(),
                {
                    "CMN_SupplyPointSpecificNum__c": POINT_VALUE,
                    "CMN_BusinessType__c": "2",
                    self.name_column: "ARVEテスト工場",
                    "CMN_DemandLocationAddress__c": "東京都テスト1丁目",
                    "CMN_OldCustomerNum__c": "0012345678901234",
                },
            )
            connection.execute(
                self.daily.insert(),
                {
                    POINT: POINT_VALUE,
                    DATE: "20260601",
                    **{slot: "1.5" for slot in SLOTS},
                },
            )
            connection.execute(
                self.contract.insert(),
                {
                    CONTRACT_POINT: POINT_VALUE,
                    CONTRACT_POWER: "500",
                },
            )

    def test_select_pending_and_failed_only(self):
        """指定月の2・5だけを取得し、他の月・状態を除外する。"""
        for index, status in enumerate("12345", start=1):
            self.insert_target(point=f"{index:022}", status=status)
        self.insert_target(month="202605", point=f"{9:022}", status="2")
        self.insert_target(month="202605", point=f"{8:022}", status="5")
        rows = self.source.fetch_targets("202606")
        self.assertEqual(
            [row["supply_point"] for row in rows], [f"{2:022}", f"{5:022}"]
        )
        self.assertTrue(all(row["target_year_month"] == "202606" for row in rows))
        self.assertTrue(all(row["company_id"] == "COMPANY0000001" for row in rows))
        self.assertTrue(all(row["syousapo_flg"] for row in rows))
        self.assertEqual(rows, self.source.fetch_targets("2026-06"))

    def test_two_processes_claim_same_key_once(self):
        """同じ主キーへ2プロセスから着手し、1件だけ成功することを確認する。"""
        import multiprocessing

        target = self.insert_target()
        self.insert_target("202605")
        with ProcessPoolExecutor(
            max_workers=2, mp_context=multiprocessing.get_context("spawn")
        ) as pool:
            futures = [
                pool.submit(claim_in_process, self.settings, target) for _ in range(2)
            ]
            results = [future.result(timeout=30) for future in futures]
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.read_target()[STATUS], "3")
        self.assertIsNone(self.read_target()["ERROR_MESSAGE"])
        self.assertEqual(self.read_target()["FILE_NAME"], "test.pdf")
        self.assertEqual(self.read_target("202605")[STATUS], "2")

    def test_success_updates_metadata_and_cannot_finish_twice(self):
        """PDFの保存先・作成日時と3を記録し、完了済み行を再更新しない。"""
        target = self.insert_target()
        self.assertTrue(self.source.claim(target))
        path = self.root / f"{POINT_VALUE}_202606.pdf"
        path.write_bytes(b"saved PDF bytes")
        self.source.finish(target, output=path)
        row = self.read_target()
        self.assertEqual(row[STATUS], "3")
        self.assertEqual(row["FILE_NAME"], path.name)
        self.assertEqual(row["FILE_PATH"], str(path))
        self.assertIsNotNone(row["REPORT_CREATED_AT"])
        self.assertEqual(row["UPDATED_BY"], "electricity_report_batch")
        self.assertFalse(self.source.claim(target))
        with self.assertRaisesRegex(RuntimeError, "更新できません"):
            self.source.finish(target, error="late failure")
        self.assertEqual(self.read_target()[STATUS], "3")

    def test_error_is_truncated_and_available_on_next_run(self):
        """失敗を5・100文字以内で記録し、次回の対象に戻す。"""
        target = self.insert_target()
        self.source.claim(target)
        self.source.finish(target, error="エラー" * 100)
        row = self.read_target()
        self.assertEqual(row[STATUS], "5")
        self.assertEqual(len(row["ERROR_MESSAGE"]), 100)
        self.assertIsNone(row["REPORT_CREATED_AT"])
        self.assertIsNone(row["FILE_PATH"])
        self.assertEqual(self.source.fetch_targets("202606"), [target])

    def test_arve_customer_and_filter(self):
        """名義列を解決し、同じ供給地点でも高圧2以外の行は選択しない。"""
        self.prepare_customer()
        with self.source.engine.begin() as connection:
            connection.execute(
                self.customer.insert(),
                {
                    "CMN_SupplyPointSpecificNum__c": POINT_VALUE,
                    "CMN_BusinessType__c": "1",
                    self.name_column: "別の業務種別",
                },
            )
        customer = self.source.load_customer(POINT_VALUE)
        self.assertEqual(
            customer,
            {
                "customer_name": "ARVEテスト工場",
                "address": "東京都テスト1丁目",
                "customer_number": "0012345678901234",
            },
        )
        self.source.settings["customer_filters"] = {}
        with self.assertRaisesRegex(ValueError, "重複"):
            self.source.load_customer(POINT_VALUE)

    def test_explicit_customer_name_mapping(self):
        """名義の物理列を明示した場合は、先頭一致の自動解決より優先する。"""
        self.prepare_customer()
        self.source.settings["customer_columns"] = {
            "customer_name": "CMN_OldCustomerNum__c"
        }
        self.assertEqual(
            self.source.load_customer(POINT_VALUE)["customer_name"], "0012345678901234"
        )
        self.source.settings["customer_columns"] = {"customer_name": "UNKNOWN_COLUMN"}
        with self.assertRaisesRegex(ValueError, "必要な列"):
            self.source.load_customer(POINT_VALUE)

    def test_zero_jobs_does_not_start_workers(self):
        """0件なら空の結果となり、ブラウザー・子プロセスを起動しない。"""
        jobs = batch.load_managed_jobs(
            self.settings, self.root, self.config_path, "2026-06"
        )
        self.assertEqual(jobs, [])
        with patch.object(batch, "ProcessPoolExecutor") as pool:
            self.assertEqual(list(batch.run_jobs(jobs, workers=2, managed=True)), [])
            pool.assert_not_called()

    def test_management_cli_zero_jobs_exits_normally(self):
        """新CLIで0件を取得した場合も、空のresults.jsonを保存して正常終了する。"""
        database_config = self.root / "database.json"
        database_config.write_text(json.dumps(self.settings), encoding="utf-8")
        output = self.root / "output"
        argv = [
            "batch.py",
            "--from-management",
            "--report-month",
            "202606",
            "--db-config",
            str(database_config),
            "--config",
            str(self.config_path),
            "--output-dir",
            str(output),
        ]
        with patch.object(sys, "argv", argv), patch.object(
            batch, "ProcessPoolExecutor"
        ) as pool, patch("builtins.print"):
            batch.main()
        self.assertEqual(json.loads((output / "results.json").read_text()), [])
        pool.assert_not_called()

    def test_managed_worker_initializes_own_services(self):
        """ワーカー初期化が管理対応のDBサービスを選び、終了時に両方を閉じる。"""
        with patch("services.report_service.ReportService") as service, patch(
            "services.report_job_source.ReportJobSource"
        ) as source, patch.object(batch, "Finalize"), patch.object(
            batch, "_source", None
        ), patch.object(
            batch, "_service", None
        ):
            batch._init_worker(None, None, self.settings, managed=True)
            source.assert_called_once_with(self.settings)
            self.assertIs(batch._source, source.return_value)
            batch._close_worker()
            service.return_value.close.assert_called_once()
            source.return_value.close.assert_called_once()

    def test_worker_success_uses_arve_and_short_history(self):
        """取得した1件からARVE名義・対象月・1日実績を渡し、保存後に3へ更新する。"""
        self.insert_target()
        self.prepare_customer()
        jobs = batch.load_managed_jobs(
            self.settings, self.root, self.config_path, "2026-06"
        )
        service = Mock()

        def generate(source, point, month, config, output):
            frame, power = source.load(point, month)
            self.assertEqual(len(frame), 48)
            self.assertTrue((frame.kw == 3).all())
            self.assertEqual(power, 500)
            self.assertEqual(config["customer_name"], "ARVEテスト工場")
            self.assertEqual(config["customer_number"], "0012345678901234")
            self.assertEqual(config["target_month"], "2026-06")
            self.assertTrue(config["syousapo_flg"])
            self.assertEqual(config["notes"], "共通注記")
            self.assertEqual(self.read_target()[STATUS], "2")
            output.write_bytes(b"saved PDF bytes")
            return {"status": "succeeded", "output": str(output), "bytes": 15}

        service.generate_database.side_effect = generate
        with patch.object(batch, "_source", self.source), patch.object(
            batch, "_service", service
        ):
            result = batch._run_job(jobs[0])
        self.assertEqual(result["status"], "succeeded")
        expected = f"COMPANY0000001_{POINT_VALUE}_syousapo_202606.pdf"
        self.assertEqual(Path(result["output"]).name, expected)
        self.assertEqual(self.read_target()["FILE_NAME"], expected)
        self.assertEqual(self.read_target()["FILE_PATH"], result["output"])
        self.assertEqual(self.read_target()[STATUS], "3")
        self.assertEqual(jobs[0]["config_values"], self.base_config)

    def test_not_joined_worker_filename_and_database_metadata(self):
        """未加入時は企業IDを付け、syousapoなしの実保存名をDBに記録する。"""
        self.insert_target(joined=False)
        self.prepare_customer()
        jobs = batch.load_managed_jobs(
            self.settings, self.root, self.config_path, "2026-06"
        )
        service = Mock()

        def generate(source, point, month, config, output):
            self.assertFalse(config["syousapo_flg"])
            output.write_bytes(b"saved PDF bytes")
            return {"status": "succeeded", "output": str(output)}

        service.generate_database.side_effect = generate
        with patch.object(batch, "_source", self.source), patch.object(
            batch, "_service", service
        ):
            result = batch._run_job(jobs[0])
        expected = f"COMPANY0000001_{POINT_VALUE}_202606.pdf"
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(Path(result["output"]).name, expected)
        self.assertTrue(Path(result["output"]).exists())
        self.assertEqual(self.read_target()["FILE_NAME"], expected)
        self.assertEqual(self.read_target()["FILE_PATH"], result["output"])

    def test_filename_preserves_zeros_and_rejects_invalid_values(self):
        """先頭ゼロを保持し、企業ID欠損・パス区切り・文字列の加入フラグを拒否する。"""
        target = {
            "company_id": "00000000000001",
            "supply_point": POINT_VALUE,
            "target_year_month": "202606",
            "syousapo_flg": False,
        }
        self.assertEqual(
            batch.managed_report_filename(target),
            f"00000000000001_{POINT_VALUE}_202606.pdf",
        )
        for values in (
            {"company_id": None},
            {"company_id": ""},
            {"company_id": "../company"},
            {"company_id": 1},
            {"company_id": "A" * 15},
            {"supply_point": "../point"},
            {"syousapo_flg": "False"},
            {"syousapo_flg": None},
            {"target_year_month": "202613"},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                batch.managed_report_filename({**target, **values})

    def test_failure_does_not_stop_next_job(self):
        """不正な1件を5へ戻し、次の1件は継続して完了できる。"""
        self.insert_target(point="0000000000000000000002")
        self.insert_target()
        self.prepare_customer()
        jobs = batch.load_managed_jobs(
            self.settings, self.root, self.config_path, "2026-06"
        )
        service = Mock()
        service.generate_database.return_value = {"status": "succeeded", "bytes": 15}
        with patch.object(batch, "_source", self.source), patch.object(
            batch, "_service", service
        ):
            results = [batch._run_job(job) for job in jobs]
        self.assertEqual(
            sorted(row["status"] for row in results), ["failed", "succeeded"]
        )
        with self.source.engine.connect() as connection:
            status = connection.execute(
                select(self.management.c[STATUS]).where(
                    self.management.c[MANAGEMENT_POINT] == "0000000000000000000002"
                )
            ).scalar_one()
        self.assertEqual(status, "5")
        self.assertEqual(self.read_target()[STATUS], "3")
        self.assertEqual(service.generate_database.call_count, 1)

    def test_already_claimed_job_is_skipped(self):
        """取得後に先に着手された対象は、ARVE取得・PDF生成を行わずスキップする。"""
        target = self.insert_target()
        jobs = batch.load_managed_jobs(
            self.settings, self.root, self.config_path, "2026-06"
        )
        self.source.claim(target)
        service = Mock()
        with patch.object(batch, "_source", self.source), patch.object(
            batch, "_service", service
        ):
            self.assertEqual(batch._run_job(jobs[0])["status"], "skipped")
        service.generate_database.assert_not_called()

    def test_state_update_error_is_reported(self):
        """DB状態更新の障害を、通常の顧客エラーと区別して結果へ記録する。"""
        self.insert_target()
        jobs = batch.load_managed_jobs(
            self.settings, self.root, self.config_path, "2026-06"
        )
        with patch.object(batch, "_source", self.source), patch.object(
            batch, "_service", Mock()
        ), patch.object(
            self.source, "finish", side_effect=RuntimeError("DB unavailable")
        ):
            result = batch._run_job(jobs[0])
        self.assertEqual(result["status"], "failed")
        self.assertIn("DB unavailable", result["state_update_error"])
        self.assertEqual(self.read_target()[STATUS], "2")

    def test_invalid_pending_states_rejected(self):
        """取得対象の2・5以外を指定する設定は拒否する。"""
        for statuses in (["1"], ["3"], ["4"], [], "2"):
            with self.subTest(statuses=statuses), self.assertRaises(ValueError):
                ReportJobSource({**self.settings, "pending_statuses": statuses})

    def test_report_month_formats_and_validation(self):
        """年月は2形式を受け付け、不正な形式や月をDB接続前に拒否する。"""
        self.assertEqual(normalize_report_ym("202606"), "202606")
        self.assertEqual(normalize_report_ym("2026-06"), "202606")
        for value in (None, 202606, "2026-6", "202613", "202600", "2026-06-01"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_report_ym(value)
        with patch.object(self.source.engine, "connect") as connect:
            with self.assertRaises(ValueError):
                self.source.fetch_targets("202613")
            connect.assert_not_called()

    def test_management_cli_requires_report_month(self):
        """対象年月を省略すると、DB取得やワーカー起動前にエラーにする。"""
        database_config = self.root / "database.json"
        database_config.write_text(json.dumps(self.settings))
        argv = ["batch.py", "--from-management", "--db-config", str(database_config)]
        with patch.object(sys, "argv", argv), patch.object(
            batch, "load_managed_jobs"
        ) as load, patch("sys.stderr"):
            with self.assertRaises(SystemExit) as error:
                batch.main()
        self.assertEqual(error.exception.code, 2)
        load.assert_not_called()

    def test_management_schema_can_differ_from_data_schema(self):
        """管理スキーマは独立して指定でき、省略時は共通設定を使う。"""
        for settings, expected in (
            ({"schema": "db_corp", "management_schema": "corp"}, "corp"),
            ({"schema": "db_corp"}, "db_corp"),
        ):
            self.source.management = None
            with patch.dict(self.source.settings, settings), patch(
                "services.report_job_source.Table"
            ) as table:
                self.source._management_table(Mock())
                self.assertEqual(table.call_args.kwargs["schema"], expected)
        self.source.management = None

    def test_postgres_lock_is_held_until_finish(self):
        """PostgreSQLでは着手コミット後も同じ接続のロックを保持し、完了後に解放する。"""
        target = self.insert_target(status="5")
        self.source.management = self.management
        connection = MagicMock()
        connection.execute.return_value.scalar_one.return_value = True
        connection.execute.return_value.rowcount = 1
        engine = Mock()
        engine.dialect.name = "postgresql"
        engine.connect.return_value = connection
        with patch.object(self.source, "engine", engine):
            self.assertTrue(self.source.claim(target))
            self.assertEqual(connection.commit.call_count, 1)
            connection.close.assert_not_called()
            self.assertFalse(self.source.claim(target))
            engine.connect.assert_called_once()
            self.source.finish(target, output=self.root / "report.pdf")
        calls = connection.execute.call_args_list
        self.assertIn("pg_try_advisory_lock", str(calls[0].args[0]))
        self.assertIn("pg_advisory_unlock", str(calls[-1].args[0]))
        self.assertEqual(calls[0].args[1], calls[-1].args[1])
        self.assertEqual(connection.commit.call_count, 3)
        connection.close.assert_called_once()
        self.assertIsNone(self.source._claim_connection)

    def test_postgres_locked_target_is_skipped_without_update(self):
        """他ワーカーが処理中なら待機せず、状態更新もPDF生成も行わない。"""
        target = self.insert_target()
        self.source.management = self.management
        connection = MagicMock()
        connection.execute.return_value.scalar_one.return_value = False
        engine = Mock()
        engine.dialect.name = "postgresql"
        engine.connect.return_value = connection
        with patch.object(self.source, "engine", engine):
            self.assertFalse(self.source.claim(target))
        connection.execute.assert_called_once()
        connection.close.assert_called_once()
        self.assertIsNone(self.source._claim_connection)

    def test_postgres_unlock_failure_discards_connection(self):
        """解放SQLの失敗時には接続を破棄し、ロック付き接続を再利用しない。"""
        target = self.insert_target()
        self.source.management = self.management
        connection = MagicMock()
        connection.execute.return_value.scalar_one.return_value = True
        connection.execute.return_value.rowcount = 1
        engine = Mock()
        engine.dialect.name = "postgresql"
        engine.connect.return_value = connection
        with patch.object(self.source, "engine", engine):
            self.assertTrue(self.source.claim(target))
            connection.execute.side_effect = RuntimeError("unlock failed")
            self.source.release_claim()
        connection.invalidate.assert_called_once()
        connection.close.assert_called_once()
        self.assertIsNone(self.source._claim_connection)

    def test_default_workers_use_cpu_count(self):
        """並列数を省略するとCPU数を使い、各対象を1件ずつ渡す。"""
        from concurrent.futures import Future

        jobs = [{"id": str(index)} for index in range(5)]

        def completed(function, job):
            future = Future()
            future.set_result({"id": job["id"], "status": "succeeded"})
            return future

        with patch.object(batch, "cpu_workers", return_value=3), patch.object(
            batch, "ProcessPoolExecutor"
        ) as pool:
            pool.return_value.__enter__.return_value.submit.side_effect = completed
            results = list(batch.run_jobs(jobs, managed=True))
        self.assertEqual(pool.call_args.kwargs["max_workers"], 3)
        calls = pool.return_value.__enter__.return_value.submit.call_args_list
        self.assertEqual([call.args[1] for call in calls], jobs)
        self.assertEqual(len(results), len(jobs))

    def test_thousand_jobs_are_submitted_once_with_bounded_queue(self):
        """1000件を1件ずつ投入し、指定並列数2と待機上限4を守る。"""
        jobs = [{"id": str(index)} for index in range(1000)]
        counts = {"active": 0, "maximum": 0, "queue_maximum": 0}
        lock = threading.Lock()

        class TestExecutor(ThreadPoolExecutor):
            def __init__(self, max_workers, **kwargs):
                super().__init__(max_workers=max_workers)
                self.submitted = []

            def submit(self, function, job):
                future = super().submit(function, job)
                self.submitted = [item for item in self.submitted if not item.done()]
                self.submitted.append(future)
                counts["queue_maximum"] = max(
                    counts["queue_maximum"], len(self.submitted)
                )
                return future

        def run_one(job):
            with lock:
                counts["active"] += 1
                counts["maximum"] = max(counts["maximum"], counts["active"])
            time.sleep(0.001)
            with lock:
                counts["active"] -= 1
            return {"id": job["id"], "status": "succeeded"}

        with patch.object(batch, "ProcessPoolExecutor", TestExecutor), patch.object(
            batch, "_run_job", run_one
        ):
            results = list(batch.run_jobs(jobs, workers=2, managed=True))
        self.assertEqual(len(results), 1000)
        self.assertEqual(
            {row["id"] for row in results}, {str(index) for index in range(1000)}
        )
        self.assertEqual(counts["maximum"], 2)
        self.assertLessEqual(counts["queue_maximum"], 4)
