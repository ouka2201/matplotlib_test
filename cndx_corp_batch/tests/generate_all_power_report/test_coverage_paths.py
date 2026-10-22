"""電力見える化レポートの未実行分岐を補う。"""

import logging
from unittest.mock import Mock

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from cndx_corp_batch.domains.generate_all_power_report.rendering.canvas import (
    FirstPageCanvas,
    SecondPageCanvas,
)
from cndx_corp_batch.domains.generate_all_power_report.rendering.sections.no0_contract import (
    draw_no0,
)
from cndx_corp_batch.domains.generate_all_power_report.rendering.sections.no3_footer import (
    _wrap_notes,
)
from cndx_corp_batch.domains.generate_all_power_report.services import (
    chart_service,
    create_power_report_service as worker_module,
    data_service,
    pdf_service,
    query_result_service,
    report_service as report_service_module,
)
from cndx_corp_batch.domains.generate_all_power_report.services.database_source_service import (
    NumericConversionError,
)
from cndx_corp_batch.domains.generate_all_power_report.services.chart_service import (
    ChartService,
)
from cndx_corp_batch.domains.generate_all_power_report.services.report_service import (
    ReportService,
)


class FakePage:
    def __init__(self, problems=()):
        self.problems = problems
        self.pdf_options = None

    def set_content(self, html, wait_until):
        self.content = (html, wait_until)

    def emulate_media(self, media):
        self.media = media

    def evaluate(self, script):
        if script.startswith("async"):
            return None
        return self.problems

    def pdf(self, **options):
        self.pdf_options = options
        return b"pdf"


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, page):
        self.context = FakeContext(page)
        self.closed = False
        self.launch_options = None

    def new_context(self):
        return self.context

    def close(self):
        self.closed = True


class FakePlaywright:
    def __init__(self, page, launch_error=None):
        self.browser = FakeBrowser(page)
        self.chromium = self
        self.launch_error = launch_error
        self.stopped = False

    def launch(self, **options):
        self.browser.launch_options = options
        if self.launch_error:
            raise self.launch_error
        return self.browser

    def stop(self):
        self.stopped = True


class FakePlaywrightStarter:
    def __init__(self, playwright):
        self.playwright = playwright

    def start(self):
        return self.playwright


def test_pdf_printer_prints_with_executable_and_closes_context(monkeypatch, tmp_path):
    page = FakePage()
    playwright = FakePlaywright(page)
    monkeypatch.setattr(
        pdf_service, "sync_playwright", lambda: FakePlaywrightStarter(playwright)
    )

    printer = pdf_service.PdfPrinter(tmp_path / "chrome")
    assert printer.print_html("<html></html>") == b"pdf"
    assert playwright.browser.launch_options["headless"] is True
    assert playwright.browser.launch_options["executable_path"] == str(
        (tmp_path / "chrome").resolve()
    )
    assert playwright.browser.context.closed is True
    assert page.pdf_options["landscape"] is True


def test_pdf_printer_rejects_overflow_and_stops_playwright_on_launch_error(monkeypatch):
    page = FakePage(["overflow"])
    playwright = FakePlaywright(page)
    monkeypatch.setattr(
        pdf_service, "sync_playwright", lambda: FakePlaywrightStarter(playwright)
    )
    printer = pdf_service.PdfPrinter()
    with pytest.raises(RuntimeError, match="印刷領域からはみ出しています"):
        printer.print_html("html")
    assert playwright.browser.context.closed is True

    failed = FakePlaywright(FakePage(), RuntimeError("launch failed"))
    monkeypatch.setattr(
        pdf_service, "sync_playwright", lambda: FakePlaywrightStarter(failed)
    )
    with pytest.raises(RuntimeError, match="launch failed"):
        pdf_service.PdfPrinter()
    assert failed.stopped is True


def test_pdf_printer_close_stops_playwright_even_when_browser_close_fails(monkeypatch):
    playwright = FakePlaywright(FakePage())
    monkeypatch.setattr(
        pdf_service, "sync_playwright", lambda: FakePlaywrightStarter(playwright)
    )
    printer = pdf_service.PdfPrinter()

    def fail_close():
        raise RuntimeError("close failed")

    printer.browser.close = fail_close
    with pytest.raises(RuntimeError, match="close failed"):
        printer.close()
    assert playwright.stopped is True


def test_report_service_constructor_query_results_debug_html_and_close(monkeypatch, tmp_path):
    charts = Mock()
    html = Mock()
    printer = Mock()
    monkeypatch.setattr(report_service_module, "ChartService", lambda: charts)
    monkeypatch.setattr(report_service_module, "HtmlRenderer", lambda: html)
    monkeypatch.setattr(report_service_module, "PdfPrinter", lambda browser: printer)
    service = ReportService("chrome")
    assert service.charts is charts
    assert service.html is html
    assert service.printer is printer

    service = ReportService.__new__(ReportService)
    service.generate_frame = Mock(return_value="result")
    query_module = query_result_service
    monkeypatch.setattr(
        query_module,
        "prepare_query_results",
        lambda *args, **kwargs: ("frame", "config"),
    )
    assert service.generate_query_results(1, 2, 3, 4, 5, 6, option=True) == "result"
    service.generate_frame.assert_called_once_with("frame", "config", 5, 6)

    service.charts = Mock()
    service.html = Mock()
    service.printer = Mock()
    service.html.render.return_value = "html"
    service.printer.print_html.return_value = b"pdf"
    monkeypatch.setattr(report_service_module, "validate_data", lambda frame, month: frame)
    monkeypatch.setattr(
        report_service_module,
        "build_context",
        lambda frame, config: ({"target_month": config["target_month"]}, "series"),
    )
    service.charts.create_all.return_value = {"first_page": "image"}
    output = tmp_path / "debug" / "report.pdf"
    result = ReportService.generate_frame(
        service,
        object(), {"target_month": "202603"}, output, tmp_path / "debug"
    )
    assert result["status"] == "succeeded"
    assert (tmp_path / "debug" / "report.html").read_text() == "html"
    assert output.read_bytes() == b"pdf"
    service.printer.close.reset_mock()
    service.close()
    service.printer.close.assert_called_once_with()


def test_worker_initializer_and_close_worker(monkeypatch):
    initialized = Mock()
    loaded = Mock(side_effect=lambda name: name)
    fake_report = Mock()
    finalized = Mock()
    closed = Mock()
    monkeypatch.setattr(worker_module, "init_db", initialized)
    monkeypatch.setattr(worker_module, "load_sql_file", loaded)
    monkeypatch.setattr(worker_module, "ReportService", lambda: fake_report)
    monkeypatch.setattr(worker_module, "Finalize", finalized)
    monkeypatch.setattr(worker_module, "close_db", closed)
    logger = logging.getLogger("batch.worker")
    old_handlers = logger.handlers[:]
    old_level = logger.level
    old_propagate = logger.propagate
    try:
        worker_module.multiprocessing_initializer("db-url", Mock())
        initialized.assert_called_once_with("db-url")
        assert set(worker_module._SQL_QUERIES) == {
            "select_cust",
            "select_30min",
            "update_target",
        }
        finalized.assert_called_once()
        worker_module.close_worker()
        fake_report.close.assert_called_once_with()
        closed.assert_called_once_with()
        assert worker_module._report_service is None
    finally:
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate
        worker_module._report_service = None


def test_chart_service_create_all_saves_both_pages(monkeypatch):
    service = ChartService.__new__(ChartService)
    service.save = Mock(side_effect=lambda name, fig: f"{name}-image")
    monkeypatch.setattr(chart_service, "draw_first_page", lambda series, config: "first")
    monkeypatch.setattr(
        chart_service, "draw_second_page", lambda series, context: "second"
    )
    assert service.create_all("series", "config", "context") == {
        "first_page": "first_page-image",
        "second_page": "second_page-image",
    }
    assert service.save.call_count == 2


def test_timezone_data_is_converted_to_japan_time():
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-06-01 00:00"], utc=True),
            "kw": [1],
        }
    )
    converted = data_service.validate_data(frame, "202606")
    assert converted.timestamp.iloc[0] == pd.Timestamp("2026-06-01 09:00")


def test_contract_conversion_error_and_newline_note_are_reported():
    with pytest.raises(NumericConversionError):
        query_result_service.prepare_query_results(
            {
                "customer_name": "会社",
                "address": "住所",
                "customer_number": "001",
                "contract_kw": "不正値",
            },
            [],
            "point",
            "202606",
        )

    class Renderer:
        def get_text_width_height_descent(self, char, prop, ismath):
            return (1, 0, 0)

    lines = _wrap_notes(
        "ab\ncd", 1, Renderer(), {False: object(), True: object()}, 1, 10
    )
    assert [[item[0] for item in line] for line in lines] == [["a", "b"], ["c", "d"]]


def test_no0_marks_sample_report_data():
    page = FirstPageCanvas()
    try:
        draw_no0(
            page,
            {
                "customer_name": "会社",
                "address": "住所",
                "customer_number": "001",
                "contract_kw": 10,
                "is_sample": True,
            },
        )
        assert "架空データ" in [text.get_text() for text in page.canvas.texts]
    finally:
        plt.close(page.fig)


def test_canvas_notes_raise_when_text_cannot_fit():
    first = FirstPageCanvas()
    second = SecondPageCanvas()
    try:
        with pytest.raises(ValueError, match="1ページ目の説明欄"):
            first.note(1, 1, 10, 2, ["長い説明" * 100])
        with pytest.raises(ValueError, match="2ページ目の説明欄"):
            second.note(1, 1, 10, 2, ["長い説明" * 100])
    finally:
        plt.close(first.fig)
        plt.close(second.fig)


def test_no5_long_labels_are_scaled():
    from cndx_corp_batch.domains.generate_all_power_report.rendering.sections.no5_monthly_power import (
        draw_no5,
    )

    page = FirstPageCanvas()
    months = pd.period_range("2025-07", periods=12, freq="M")
    series = {
        "monthly": pd.DataFrame(
            {"max": [10**18] * 12}, index=months
        )
    }
    try:
        draw_no5(page, series, {"contract_kw": 1})
    finally:
        plt.close(page.fig)
