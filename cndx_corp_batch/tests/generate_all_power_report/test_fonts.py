"""帳票に組み込んだフォントとHTMLテンプレートを検証する。"""

from pathlib import Path

from cndx_corp_batch.domains.generate_all_power_report.services.pdf_service import HtmlRenderer


# テストディレクトリからバッチのルートへ移動する。
ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "domains" / "generate_all_power_report" / "rendering" / "font"


def test_report_fonts_are_packaged_with_the_batch():
    assert (FONT_DIR / "meiryo.ttc").is_file()
    assert (FONT_DIR / "meiryob.ttc").is_file()


def test_html_renderer_embeds_both_pages_without_external_files():
    html = HtmlRenderer().render(
        {
            "charts": {
                "first_page": "data:image/png;base64,first",
                "second_page": "data:image/png;base64,second",
            }
        }
    )
    assert 'src="data:image/png;base64,first"' in html
    assert 'src="data:image/png;base64,second"' in html
    assert "@font-face" not in html
