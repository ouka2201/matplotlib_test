"""4テーブルのINSERT・冪等な再実行・ロールバックと実際の帳票取得を検証する。"""

from dataclasses import replace
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import Column, MetaData, String, Table, func, inspect, select, update
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from examples.insert_test_data import (
    SeedOptions,
    seed_database,
    init_sqlite_tables,
    TABLE_NAMES,
    main,
)
from services.database_source import SLOTS, POINT, CONTRACT_POINT
from services.report_job_source import ReportJobSource, CUSTOMER_POINT
from services.data_service import build_context


class InsertTestDataTests(unittest.TestCase):
    """検証専用のSQLiteへ登録し、読み取り側からも整合性を確認する。"""

    def setUp(self):
        """一時DBと、既定と同じ品質列・顧客列設定を準備する。"""
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.settings = json.loads(
            (
                Path(__file__).resolve().parents[1] / "examples/database.test.json"
            ).read_text()
        )
        self.env = patch.dict(
            os.environ,
            {self.settings["url_env"]: f"sqlite:///{self.root / 'data.sqlite'}"},
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.source = ReportJobSource(self.settings)
        self.addCleanup(self.source.close)
        init_sqlite_tables(self.source.engine, self.settings)
        self.tables = {
            kind: Table(name, MetaData(), autoload_with=self.source.engine)
            for kind, name in TABLE_NAMES.items()
        }
        self.options = SeedOptions("2026-06", count=2, days=3, point_prefix="000090")

    def counts(self):
        """実DBの4テーブルの行数を返す。

        Returns:
            dict: テーブル種別から行数への対応。
        """
        with self.source.engine.connect() as connection:
            return {
                kind: connection.scalar(select(func.count()).select_from(table))
                for kind, table in self.tables.items()
            }

    def completed_imports(self):
        """取込完了とARVEを供給地点で照合した、次工程の入力を返す。

        レポート管理テーブルへのINSERTは行わず、準備データだけ確認する。

        Returns:
            list[dict]: 供給地点・対象年月・ARVEの企業ID・レコードタイプID。
        """
        imported, customer = self.tables["import_management"], self.tables["customer"]
        query = (
            select(
                imported.c.SUPPLY_POINT_NUMBER.label("supply_point"),
                imported.c.TARGET_YEAR_MONTH.label("target_year_month"),
                customer.c.CMN_KigyoID_Fk__c.label("company_id"),
                customer.c.RecordTypeId.label("record_type_id"),
            )
            .where(
                imported.c.SUPPLY_POINT_NUMBER == customer.c[CUSTOMER_POINT],
                imported.c.CREATE_STATUS == "3",
            )
            .order_by(imported.c.SUPPLY_POINT_NUMBER)
        )
        with self.source.engine.connect() as connection:
            return [dict(row) for row in connection.execute(query).mappings()]

    def test_insert_four_tables_and_report_readback(self):
        """4テーブルで22桁の供給地点が一致し、取込完了・No.0・48枠を確認する。"""
        result = seed_database(self.settings, self.options)
        self.assertEqual(
            self.counts(),
            {"import_management": 2, "customer": 2, "contract": 2, "daily": 6},
        )
        self.assertEqual(result["start"], "2026-06-28")
        self.assertEqual(result["end"], "2026-06-30")
        self.assertFalse(
            inspect(self.source.engine).has_table(self.settings["management_table"])
        )
        targets = self.completed_imports()
        self.assertEqual(
            [row["record_type_id"] for row in targets], ["TEST_OTHER", "TEST_SYOUSAPO"]
        )
        points = {row["supply_point"] for row in targets}
        point_columns = {
            "import_management": "SUPPLY_POINT_NUMBER",
            "customer": CUSTOMER_POINT,
            "contract": CONTRACT_POINT,
            "daily": POINT,
        }
        with self.source.engine.connect() as connection:
            for kind, column in point_columns.items():
                self.assertEqual(
                    set(
                        connection.execute(
                            select(self.tables[kind].c[column]).distinct()
                        ).scalars()
                    ),
                    points,
                )
            imports = (
                connection.execute(select(self.tables["import_management"]))
                .mappings()
                .all()
            )
        for row in imports:
            self.assertEqual(row["CREATE_STATUS"], "3")
            self.assertEqual(row["TARGET_YEAR_MONTH"], "202606")
            self.assertIsNone(row["LINKED_DATE"])
            self.assertIsNone(row["LINKED_ERROR_MESSAGE"])
        for index, target in enumerate(targets, 1):
            point = target["supply_point"]
            self.assertTrue(point.startswith("000090"))
            self.assertEqual(len(point), 22)
            self.assertEqual(target["company_id"], f"TEST{index:010d}")
            customer = self.source.load_customer(point)
            self.assertEqual(customer["customer_number"], f"{index:016d}")
            self.assertIn("テスト事業所", customer["customer_name"])
            frame, power = self.source.load(point, "2026-06")
            self.assertEqual(len(frame), 144)
            self.assertEqual(frame.kw.max(), 1200)
            self.assertEqual(power, 1600)
            context, _ = build_context(
                frame, {**customer, "target_month": "2026-06", "contract_kw": power}
            )
            self.assertEqual(context["actual_period"], "2026/06/28〜2026/06/30")

    def test_existing_error_and_skip_preserve_completed_record(self):
        """既定の重複エラーとskipを確認し、取込状態・紐付け情報を保持する。"""
        seed_database(self.settings, self.options)
        target = self.completed_imports()[0]
        with self.source.engine.begin() as connection:
            imported = self.tables["import_management"]
            connection.execute(
                update(imported)
                .where(imported.c.SUPPLY_POINT_NUMBER == target["supply_point"])
                .values(CREATE_STATUS="4", LINKED_ERROR_MESSAGE="existing warning")
            )
        before = self.counts()
        with self.assertRaisesRegex(ValueError, "既存キー"):
            seed_database(self.settings, self.options)
        result = seed_database(self.settings, replace(self.options, on_existing="skip"))
        self.assertEqual(self.counts(), before)
        self.assertTrue(all(row["inserted"] == 0 for row in result["tables"].values()))
        with self.source.engine.connect() as connection:
            states = connection.execute(
                select(
                    self.tables["import_management"].c.CREATE_STATUS,
                    self.tables["import_management"].c.LINKED_ERROR_MESSAGE,
                ).order_by(self.tables["import_management"].c.SUPPLY_POINT_NUMBER)
            ).all()
        self.assertEqual(states, [("4", "existing warning"), ("3", None)])

    def test_dry_run_does_not_insert(self):
        """3か月の登録予定を確認しても、テーブルの行数は増えない。"""
        result = seed_database(
            self.settings, replace(self.options, days=None, months=3, dry_run=True)
        )
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["tables"]["daily"]["inserted"], 91 * 2)
        self.assertTrue(all(value == 0 for value in self.counts().values()))

    def test_database_failure_rolls_back_all_tables(self):
        """最後の取込管理INSERTを失敗させ、先に登録した3テーブルも戻す。"""
        with self.source.engine.begin() as connection:
            connection.exec_driver_sql(
                'CREATE TRIGGER reject_seed BEFORE INSERT ON t_30min_import_mng BEGIN SELECT RAISE(ABORT, "test failure"); END'
            )
        with self.assertRaises(IntegrityError):
            seed_database(self.settings, self.options)
        self.assertTrue(all(value == 0 for value in self.counts().values()))

    def test_extra_required_column_and_case_insensitive_defaults(self):
        """実環境の追加必須列を検出し、seed_defaultsで値を指定して登録できる。"""
        with self.source.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE t_30min_import_mng ADD COLUMN REQUIRED_TEST VARCHAR(10) NOT NULL"
            )
        with self.assertRaisesRegex(ValueError, "seed_defaults"):
            seed_database(self.settings, self.options)
        self.assertTrue(all(value == 0 for value in self.counts().values()))
        settings = {
            **self.settings,
            "seed_defaults": {
                "import_management": {
                    "required_test": "extra",
                    "created_by": "custom_test",
                }
            },
        }
        seed_database(settings, self.options)
        with self.source.engine.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT REQUIRED_TEST, CREATED_BY FROM t_30min_import_mng"
            ).all()
        self.assertEqual(rows, [("extra", "custom_test")] * 2)

    def test_full_leap_year_and_daily_kwh_sum(self):
        """うるう年の366日を登録し、元kWhと読み取り後の電力量合計が一致する。"""
        options = replace(self.options, report_month="2024-02", count=1, days=None)
        result = seed_database(self.settings, options)
        self.assertEqual(result["tables"]["daily"]["inserted"], 366)
        point = self.completed_imports()[0]["supply_point"]
        frame, _ = self.source.load(point, "2024-02")
        self.assertEqual(len(frame), 366 * 48)
        with self.source.engine.connect() as connection:
            rows = connection.execute(
                select(*[self.tables["daily"].c[slot] for slot in SLOTS])
            ).all()
        original = sum(float(value) for row in rows for value in row)
        self.assertAlmostEqual(frame.kw.sum() * 0.5, original, places=5)

    def test_thousand_supply_points_one_day(self):
        """1000地点の供給地点が4テーブルで揃い、取込完了1000件を確認する。"""
        seed_database(self.settings, replace(self.options, count=1000, days=1))
        self.assertTrue(all(value == 1000 for value in self.counts().values()))
        targets = self.completed_imports()
        self.assertEqual(len(targets), 1000)
        self.assertEqual(len({row["supply_point"] for row in targets}), 1000)
        self.assertEqual(
            sum(row["record_type_id"] == "TEST_SYOUSAPO" for row in targets), 500
        )
        with self.source.engine.connect() as connection:
            point_columns = {
                "import_management": "SUPPLY_POINT_NUMBER",
                "customer": CUSTOMER_POINT,
                "contract": CONTRACT_POINT,
                "daily": POINT,
            }
            for kind, column in point_columns.items():
                self.assertEqual(
                    set(
                        connection.execute(
                            select(self.tables[kind].c[column])
                        ).scalars()
                    ),
                    {row["supply_point"] for row in targets},
                )
        frame, _ = self.source.load(targets[-1]["supply_point"], "2026-06")
        self.assertEqual(len(frame), 48)

    def test_storage_units_read_back_same_average_power(self):
        """kWh・kW・Whの保存単位ごとに、平均電力への変換が一致する。"""
        for serial, unit in enumerate(["kWh", "kW", "Wh"], 1):
            settings = {**self.settings, "value_unit": unit}
            seed_database(
                settings, replace(self.options, count=1, days=1, start_id=serial)
            )
            source = ReportJobSource(settings)
            try:
                point = "000090" + f"{serial:016d}"
                frame, _ = source.load(point, "2026-06")
                self.assertEqual(frame.kw.max(), 1200)
            finally:
                source.close()

    def test_invalid_options_do_not_open_database(self):
        """件数・期間・番号等が不正なら、接続やINSERTを行わず拒否する。"""
        for values in (
            {"count": 0},
            {"months": 13},
            {"days": 367},
            {"point_prefix": "../"},
            {"contract_kw": -1},
            {"max_kw": float("nan")},
            {"init_sqlite": True, "dry_run": True},
        ):
            with self.subTest(values=values), patch(
                "examples.insert_test_data.DatabaseSource"
            ) as source:
                with self.assertRaises(ValueError):
                    seed_database(self.settings, replace(self.options, **values))
                source.assert_not_called()

        for defaults in ([], {"unknown": {}}, {"daily": None}, {"management": {}}):
            with self.subTest(seed_defaults=defaults), patch(
                "examples.insert_test_data.DatabaseSource"
            ) as source:
                with self.assertRaisesRegex(ValueError, "seed_defaults"):
                    seed_database(
                        {**self.settings, "seed_defaults": defaults}, self.options
                    )
                source.assert_not_called()

        for settings in (
            {"seed_record_type_ids": None},
            {"seed_record_type_ids": {"joined": "X", "not_joined": "X"}},
            {"seed_record_type_ids": {"joined": ""}},
            {"import_management_table": "T_POWER_REPORT_MNG_INFO"},
        ):
            with self.subTest(settings=settings), patch(
                "examples.insert_test_data.DatabaseSource"
            ) as source:
                with self.assertRaises(ValueError):
                    seed_database({**self.settings, **settings}, self.options)
                source.assert_not_called()

    def test_existing_report_management_is_untouched(self):
        """レポート管理が既に存在しても、INSERT・UPDATEせず既存行を保持する。"""
        report = Table(
            self.settings["management_table"],
            MetaData(),
            Column("SUPPLY_POINT_NUMBER", String(27), primary_key=True),
            Column("TARGET_YEAR_MONTH", String(6), primary_key=True),
            Column("CREATE_STATUS", String(1)),
            Column("FILE_NAME", String(255)),
        )
        report.create(self.source.engine)
        original = {
            "SUPPLY_POINT_NUMBER": "0000900000000000000001",
            "TARGET_YEAR_MONTH": "202606",
            "CREATE_STATUS": "5",
            "FILE_NAME": "existing.pdf",
        }
        with self.source.engine.begin() as connection:
            connection.execute(report.insert(), original)
            connection.exec_driver_sql(
                'CREATE TRIGGER reject_report_insert BEFORE INSERT ON t_power_report_mng_info BEGIN SELECT RAISE(ABORT, "must not seed report"); END'
            )
        seed_database(self.settings, self.options)
        with self.source.engine.connect() as connection:
            self.assertEqual(
                [dict(row) for row in connection.execute(select(report)).mappings()],
                [original],
            )
        self.assertEqual(len(self.completed_imports()), 2)

    def test_arve_record_type_modes_and_configured_columns(self):
        """実際の列名・IDの設定を反映し、全件加入・全件未加入のARVE行を作る。"""
        settings = {
            **self.settings,
            "customer_table": "custom_arve",
            "customer_columns": {
                **self.settings["customer_columns"],
                "company_id": "COMPANY_FOR_TEST",
                "record_type_id": "TYPE_FOR_TEST",
            },
            "seed_record_type_ids": {
                "joined": "ACTUAL_JOINED",
                "not_joined": "ACTUAL_OTHER",
            },
        }
        init_sqlite_tables(self.source.engine, settings)
        for serial, mode, record_type in (
            (1, "joined", "ACTUAL_JOINED"),
            (2, "not-joined", "ACTUAL_OTHER"),
        ):
            seed_database(
                settings,
                replace(self.options, count=1, days=1, start_id=serial, syousapo=mode),
            )
        customer = Table("custom_arve", MetaData(), autoload_with=self.source.engine)
        with self.source.engine.connect() as connection:
            rows = connection.execute(
                select(customer.c.COMPANY_FOR_TEST, customer.c.TYPE_FOR_TEST).order_by(
                    customer.c[CUSTOMER_POINT]
                )
            ).all()
        self.assertEqual(
            rows,
            [("TEST0000000001", "ACTUAL_JOINED"), ("TEST0000000002", "ACTUAL_OTHER")],
        )
        before = self.counts()
        conflicting = {
            **self.settings,
            "customer_filters": {"RecordTypeId": "TEST_SYOUSAPO"},
        }
        with self.assertRaisesRegex(ValueError, "一致しません"):
            seed_database(conflicting, replace(self.options, start_id=10))
        self.assertEqual(self.counts(), before)

    def test_cli_inserts_requested_count(self):
        """実CLIの引数から件数・日数を受け取り、その数で4テーブルに登録する。"""
        config_path = self.root / "database.json"
        config_path.write_text(json.dumps(self.settings))
        args = [
            "insert_test_data.py",
            "--db-config",
            str(config_path),
            "--report-month",
            "2026-06",
            "--count",
            "3",
            "--days",
            "1",
        ]
        with patch.object(sys, "argv", args), patch("builtins.print"):
            main()
        self.assertTrue(all(value == 3 for value in self.counts().values()))
