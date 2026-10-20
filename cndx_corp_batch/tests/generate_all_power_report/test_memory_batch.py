"""帳票ページ画像をメモリ上で生成し、必要な場合だけ保存する動作を検証する。"""

import base64
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt

from cndx_corp_batch.domains.generate_all_power_report.services.chart_service import (
    ChartService,
)


def test_save_returns_png_data_uri_and_closes_figure(tmp_path):
    service = ChartService.__new__(ChartService)
    service.output_dir = None
    figure = plt.figure()
    number = figure.number
    with patch.object(Path, "write_bytes", side_effect=AssertionError("不要な保存")):
        uri = service.save("page", figure)
    assert base64.b64decode(uri.split(",", 1)[1]).startswith(b"\x89PNG")
    assert not plt.fignum_exists(number)


def test_save_writes_debug_png_only_when_output_dir_is_set(tmp_path):
    service = ChartService(output_dir=tmp_path)
    figure = plt.figure()
    uri = service.save("page", figure)
    assert (tmp_path / "page.png").read_bytes() == base64.b64decode(
        uri.split(",", 1)[1]
    )
