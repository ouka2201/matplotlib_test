"""電力見える化レポートの描画テストで使用する共通設定。"""

import matplotlib

matplotlib.use("Agg")

import pytest

from cndx_corp_batch.domains.generate_all_power_report.services.chart_service import (
    ChartService,
)


@pytest.fixture(scope="session", autouse=True)
def configure_report_font():
    """帳票描画前に同梱フォントを登録し、日本語グリフ警告を防ぐ。"""
    ChartService()
