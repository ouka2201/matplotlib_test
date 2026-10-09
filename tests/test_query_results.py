"""既存SQLの取得結果からの変換と、スレッド/プロセスへの接続を検証する。"""

from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from examples import existing_sql_batch as integration
from services.database_source import DATE, POINT, SLOTS
from services.query_result_service import prepare_query_results, row_to_dict
from services.report_service import ReportService
from services import query_result_worker as worker

POINT_VALUE = "0000000000000000000001"


def customer():
    """テスト用契約情報を返す。"""
    return {
        "customer_name": "テスト工場",
        "address": "東京都テスト1番地",
        "customer_number": "0000000000000001",
        "contract_kw": "39",
    }


def daily(day="20260601", value="1.5"):
    """供給地点列を含まない、日付+48枠の取得結果を返す。"""
    return {DATE.lower(): day, **{slot.lower(): value for slot in SLOTS}}


class QueryResultTests(unittest.TestCase):
    """セッションを持たない取得結果と既存の帳票処理の接続を確認する。"""

    def test_date_and_48_lowercase_columns(self):
        """日付+48枠だけから1日実績を作り、kWhの2倍と時刻を確認する。"""
        frame, config = prepare_query_results(
            customer(), [daily()], POINT_VALUE, "2026-06"
        )
        self.assertEqual(len(frame), 48)
        self.assertEqual(frame.timestamp.iloc[0].strftime("%H:%M"), "00:00")
        self.assertEqual(frame.timestamp.iloc[-1].strftime("%H:%M"), "23:30")
        self.assertTrue((frame.kw == 3).all())
        self.assertEqual(frame.kw.sum() * 0.5, 72)
        self.assertEqual(config["contract_kw"], 39)
        self.assertEqual(config["customer_number"], "0000000000000001")

    def test_alias_columns_and_original_config_are_preserved(self):
        """別名の契約・日付・枠列を対応表で変換し、共通設定を変更しない。"""
        columns = {name: f"SQL_{name.upper()}" for name in customer()}
        cust = {columns[name]: value for name, value in customer().items()}
        slots = [f"energy{index:02}" for index in range(1, 49)]
        row = {
            "ymd": "20260601",
            **{name: str(index) for index, name in enumerate(slots)},
        }
        base = {"notes": "共通注記", "contract_kw": 999, "target_month": "2025-01"}
        before = dict(base)
        frame, config = prepare_query_results(
            cust,
            [row],
            POINT_VALUE,
            "2026-06",
            customer_columns=columns,
            date_column="YMD",
            slot_columns=slots,
            config=base,
        )
        self.assertEqual(frame.kw.iloc[-1], 94)
        self.assertEqual(config["notes"], "共通注記")
        self.assertEqual(config["contract_kw"], 39)
        self.assertEqual(config["target_month"], "2026-06")
        self.assertEqual(base, before)

    def test_all_rows_are_used_and_sorted(self):
        """取得した全日分を使用し、入力が逆順でも正しい日時順へ揃える。"""
        frame, _ = prepare_query_results(
            customer(), [daily("20260602", "2"), daily()], POINT_VALUE, "2026-06"
        )
        self.assertEqual(len(frame), 96)
        self.assertEqual(frame.timestamp.iloc[0].strftime("%Y%m%d"), "20260601")
        self.assertEqual(frame.kw.iloc[48], 4)

    def test_invalid_data_is_not_filled_with_zero(self):
        """不足列・不正値・実績の空白日を補完せず、既存の検証で拒否する。"""
        missing = daily()
        missing.pop(SLOTS[-1].lower())
        for rows in (
            [],
            [missing],
            [daily(value="-1")],
            [daily(value="nan")],
            [daily(), daily("20260603")],
            [daily(), daily()],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                prepare_query_results(customer(), rows, POINT_VALUE, "2026-06")

    def test_customer_and_quality_validation(self):
        """不正な契約値・別地点・非0の品質件数を拒否する。"""
        for updates in (
            {"customer_name": ""},
            {"customer_number": 123},
            {"contract_kw": "0"},
            {"contract_kw": "nan"},
        ):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                prepare_query_results(
                    {**customer(), **updates}, [daily()], POINT_VALUE, "2026-06"
                )
        with self.assertRaisesRegex(ValueError, "別の供給地点"):
            prepare_query_results(
                customer(), [{**daily(), POINT: "other"}], POINT_VALUE, "2026-06"
            )
        with self.assertRaisesRegex(ValueError, "欠測"):
            prepare_query_results(
                customer(),
                [{**daily(), "quality_count": 1}],
                POINT_VALUE,
                "2026-06",
                quality_columns=["QUALITY_COUNT"],
            )

    def test_bad_column_options_and_tuple_rows_are_rejected(self):
        """曖昧な列名、列順不足、列名のないタプルを拒否する。"""
        for options in (
            {"slot_columns": SLOTS[:47]},
            {"slot_columns": [SLOTS[0]] * 48},
            {"customer_columns": {"unknown": "x"}},
            {"customer_columns": {"customer_name": "missing"}},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                prepare_query_results(
                    customer(), [daily()], POINT_VALUE, "2026-06", **options
                )
        with self.assertRaises(ValueError):
            prepare_query_results(
                {**customer(), "CUSTOMER_NAME": "other"},
                [daily()],
                POINT_VALUE,
                "2026-06",
            )
        with self.assertRaises(TypeError):
            row_to_dict(("20260601", 1))

    def test_sqlalchemy_row_is_accepted(self):
        """画像のone()で得られるRowにも、列名を用いてアクセスできる。"""
        engine = create_engine("sqlite://")
        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text(
                        "SELECT '工場' AS customer_name, '住所' AS address, '0001' AS customer_number, 39 AS contract_kw"
                    )
                ).one()
                frame, config = prepare_query_results(
                    row, [daily()], POINT_VALUE, "2026-06"
                )
                self.assertEqual(config["customer_number"], "0001")
                self.assertEqual(len(frame), 48)
        finally:
            engine.dispose()

    def test_service_uses_generated_frame_without_database_access(self):
        """新入口が取得結果だけを変換し、既存のページ生成へ渡す。"""
        service = ReportService.__new__(ReportService)
        service.generate_frame = Mock(return_value={"status": "succeeded"})
        output = Path("report.pdf")
        result = service.generate_query_results(
            customer(), [daily()], POINT_VALUE, "2026-06", output
        )
        self.assertEqual(result["status"], "succeeded")
        frame, config, path, debug = service.generate_frame.call_args.args
        self.assertEqual(len(frame), 48)
        self.assertEqual(config["contract_kw"], 39)
        self.assertEqual(path, output)
        self.assertIsNone(debug)

    def test_existing_sql_collects_all_rows_before_rendering(self):
        """セッション内で全行を取得し、排他的な終了日と軽い辞書をPDF側へ渡す。"""
        sessions = []
        parameters = []
        cust = customer()

        @contextmanager
        def get_session():
            session = Mock()
            session.closed = False
            if not sessions:
                session.execute.return_value.mappings.return_value.one.return_value = (
                    cust
                )
            else:
                session.execute.return_value.mappings.return_value.all.return_value = [
                    daily(),
                    daily("20260602"),
                ]
            sessions.append(session)
            try:
                yield session
            finally:
                parameters.append(session.execute.call_args.args[1])
                session.closed = True

        pool = Mock()

        def submit(function, payload):
            self.assertTrue(all(session.closed for session in sessions))
            self.assertEqual(len(payload["daily_rows"]), 2)
            self.assertEqual(payload["report_month"], "2026-06")
            self.assertEqual(
                payload["output"].name,
                f"COMPANY0000001_{POINT_VALUE}_syousapo_202606.pdf",
            )
            self.assertIs(function, worker.render_query_result_job)
            future = Future()
            future.set_result({"status": "succeeded", "output": str(payload["output"])})
            return future

        pool.submit.side_effect = submit
        target = {
            "supply_point_number": POINT_VALUE,
            "company_id": "COMPANY0000001",
            "syousapo_flg": True,
        }
        result = integration.create_report_from_existing_sql(
            target, date(2026, 6, 1), get_session, lambda name: "SELECT 1", pool, "out"
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(parameters[1]["start_date"], "20250701")
        self.assertEqual(parameters[1]["end_date"], "20260701")

    def test_worker_initializes_once_and_closes(self):
        """PDF側でサービスを初期化・再利用し、終了時に閉じる。"""
        with patch.object(worker, "_service", None), patch.object(
            worker, "Finalize"
        ), patch("services.report_service.ReportService") as service:
            worker.initialize_query_worker()
            worker.render_query_result_job({"output": Path("a.pdf")})
            worker.render_query_result_job({"output": Path("b.pdf")})
            service.assert_called_once()
            self.assertEqual(service.return_value.generate_query_results.call_count, 2)
            worker._close_query_worker()
            service.return_value.close.assert_called_once()

    def test_empty_targets_do_not_start_any_pool(self):
        """対象0件ではDB取得・ブラウザー・プロセスを起動しない。"""
        with patch.object(integration, "ProcessPoolExecutor") as pool:
            result = integration.run_existing_sql_batch(
                [], "202606", Mock(), Mock(), "out"
            )
            self.assertEqual(result, [])
            pool.assert_not_called()

    def test_cpu_count_and_failure_continuation(self):
        """CPU数を使用し、1件の失敗後も全対象の結果を返す。"""
        targets = [{"supply_point_number": str(index)} for index in range(10)]

        def create(target, *args):
            if target["supply_point_number"] == "3":
                raise ValueError("bad customer")
            return {"status": "succeeded"}

        callback = Mock()
        with patch.object(integration, "cpu_workers", return_value=2), patch.object(
            integration, "ProcessPoolExecutor"
        ) as pool, patch.object(
            integration, "create_report_from_existing_sql", side_effect=create
        ):
            results = integration.run_existing_sql_batch(
                targets, "202606", Mock(), Mock(), "out", on_result=callback
            )
        self.assertEqual(pool.call_args.kwargs["max_workers"], 2)
        self.assertEqual(len(results), 10)
        self.assertEqual(sum(row["status"] == "failed" for row in results), 1)
        self.assertEqual(callback.call_count, 10)

    def test_duplicate_targets_are_rejected(self):
        """同じ保存先へ並列に書かないよう、対象リストの地点重複を拒否する。"""
        with patch.object(integration, "ProcessPoolExecutor") as pool:
            with self.assertRaises(ValueError):
                integration.run_existing_sql_batch(
                    [{"supply_point_number": POINT_VALUE}] * 2,
                    "202606",
                    Mock(),
                    Mock(),
                    "out",
                )
            pool.assert_not_called()
