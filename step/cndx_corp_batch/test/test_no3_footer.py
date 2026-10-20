"""No.3の注記全文・強調書式・明示改行を検証する。"""

import matplotlib.pyplot as plt
import pytest

from cndx_corp_batch.domains.generate_all_power_report.rendering.canvas import FirstPageCanvas
from cndx_corp_batch.domains.generate_all_power_report.rendering.sections.no3_footer import (
    EMPHASIS,
    draw_no3,
)
from cndx_corp_batch.domains.generate_all_power_report.rendering.styles import DEFAULT_NOTES
from cndx_corp_batch.domains.generate_all_power_report.services.chart_service import ChartService


@pytest.fixture
def page():
    ChartService()
    page = FirstPageCanvas()
    yield page
    plt.close(page.fig)


def test_default_notes_preserve_text_emphasis_and_bounds(page):
    draw_no3(page, {})
    page.fig.canvas.draw()

    assert len(page.canvas.images) == 1
    texts = page.canvas.texts
    assert "".join(item.get_text() for item in texts) == DEFAULT_NOTES
    assert "".join(item.get_text() for item in texts if item.get_fontweight() == "bold") == EMPHASIS
    renderer = page.fig.canvas.get_renderer()
    left, bottom = page.canvas.transData.transform((56.3, 192.8))
    right, top = page.canvas.transData.transform((139.4, 183.8))
    for item in texts:
        box = item.get_window_extent(renderer)
        assert box.x0 >= left - 1
        assert box.x1 <= right + 1
        assert box.y0 >= bottom - 1
        assert box.y1 <= top + 1


def test_custom_notes_preserve_blank_line_without_emphasis(page):
    draw_no3(page, {"notes": "前半\n\n後半"})

    first, last = page.canvas.texts
    assert [first.get_text(), last.get_text()] == ["前半", "後半"]
    assert first.get_fontweight() == last.get_fontweight() == "normal"
    line_height = first.get_fontsize() * 25.4 / 72 * 1.3
    assert last.get_position()[1] - first.get_position()[1] == pytest.approx(2 * line_height)
