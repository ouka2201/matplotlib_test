"""ページ画像の生成からPDF保存までを、ブラウザー起動なしで確認する。"""

import base64
import re
from unittest.mock import Mock

from cndx_corp_batch.domains.generate_all_power_report.services.chart_service import ChartService
from cndx_corp_batch.domains.generate_all_power_report.services.database_source import DATE, SLOTS
from cndx_corp_batch.domains.generate_all_power_report.services.pdf_service import HtmlRenderer
from cndx_corp_batch.domains.generate_all_power_report.services.report_service import ReportService


def test_report_embeds_both_pages_and_saves_pdf(tmp_path):
    service = ReportService.__new__(ReportService)
    service.charts = ChartService()
    service.html = HtmlRenderer()
    service.printer = Mock()
    service.printer.print_html.return_value = b"test PDF bytes"
    rows = [
        {DATE: f"202607{day:02d}", **dict.fromkeys(SLOTS, "50")}
        for day in range(1, 32)
    ]
    output = tmp_path / "report.pdf"

    result = service.generate_query_results(
        {"customer_name": "テスト工場", "address": "東京都", "customer_number": "0001", "contract_kw": 200},
        rows, "0001", "202607", output,
    )

    html = service.printer.print_html.call_args.args[0]
    images = re.findall(r'src="data:image/png;base64,([^"]+)"', html)
    assert len(images) == 2
    assert all(base64.b64decode(data).startswith(b"\x89PNG\r\n\x1a\n") for data in images)
    assert output.read_bytes() == b"test PDF bytes"
    assert result["status"] == "succeeded"
