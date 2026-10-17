"""バッチ処理内容定義書11／帳票出力項目仕様説明書_No.3：TEPCOロゴ・最大電力／使用電力量説明。"""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import matplotlib.image as mpimg
from matplotlib import font_manager, rcParams

from ..styles import DEFAULT_NOTES

EMPHASIS = "料金の算定期間とは異なる場合があります"


@lru_cache(maxsize=1)
def load_footer_logo():
    """帳票出力項目仕様説明書_No.3 項番1「ロゴ」：TEPCOロゴ画像を読み込む。

    顧客ごとに画像ファイルを作成しない。ワーカープロセスごとに
    一度だけ画像を読み、月間10万件の作成で読み込みを繰り返さない。

    Returns:
        numpy.ndarray: matplotlibのimshowに渡すロゴ画像。

    Raises:
        OSError: 同梱ロゴの読み込みに失敗した場合。
    """
    path = Path(__file__).resolve().parents[2] / "assets" / "tepco_logo.png"
    return mpimg.imread(BytesIO(path.read_bytes()), format="png")


def _wrap_notes(value, start, renderer, props, px_per_mm, width):
    """帳票No.3 項番2の実装補助：実測した文字幅と説明文中の改行位置に従って折り返す。"""
    lines = [[]]
    line_width = 0
    for index, char in enumerate(value):
        if char == "\n":
            lines.append([])
            line_width = 0
            continue
        bold = start >= 0 and start <= index < start + len(EMPHASIS)
        char_width = (
            renderer.get_text_width_height_descent(char, props[bold], False)[0]
            / px_per_mm
        )
        if line_width + char_width > width and lines[-1]:
            lines.append([])
            line_width = 0
        lines[-1].append((char, bold, char_width))
        line_width += char_width
    return lines


def _draw_note_lines(canvas, lines, x, y, size, line_height):
    """帳票No.3 項番2の実装補助：説明文の通常の文字と強調する文字を左揃えで描画する。"""
    for row, line in enumerate(lines):
        current_x = x
        # 同じ書式の連続した文字をまとめて描き、1文字ずつの描画を避ける。
        run, run_bold, run_width = "", False, 0
        runs = []
        for char, bold, char_width in line:
            if run and bold != run_bold:
                runs.append((run, run_bold, run_width))
                run, run_width = "", 0
            run += char
            run_bold = bold
            run_width += char_width
        if run:
            runs.append((run, run_bold, run_width))
        for text, bold, text_width in runs:
            canvas.text(
                current_x,
                y + row * line_height,
                text,
                fontsize=size,
                fontweight="bold" if bold else "normal",
                color="#202020",
                va="top",
            )
            current_x += text_width


def draw_no3(page, config):
    """処理11／帳票出力項目仕様説明書_No.3：ロゴと最大電力・使用電力量説明を作成する。

    項番1はTEPCOロゴ画像、項番2は最大電力・使用電力量・料金算定期間の固定説明文。
    実装では説明文を実測幅で折り返し、文字サイズを5.7～5.5ptで調整する。
    notesによる差し替えと部分太字は描画実装の設定であり、設計書の項目追加ではない。

    Args:
        page (FirstPageCanvas): 帳票1ページ目の描画先。左上原点、単位mm。
        config (dict): notesを省略した場合は設計書の固定説明文を使用する。

    Raises:
        OSError: TEPCOロゴ画像を読み込めない場合。
    """
    canvas = page.canvas
    logo = load_footer_logo()
    # 項番1「ロゴ」：TEPCOの画像を左側に貼り付ける。縦横比を保持する。
    logo_x, logo_y, logo_width = 2.4, 184.7, 26.5
    logo_height = logo_width * logo.shape[0] / logo.shape[1]
    canvas.imshow(
        logo,
        extent=(logo_x, logo_x + logo_width, logo_y + logo_height, logo_y),
        aspect="auto",
    )

    x, y, width, height = 56.3, 183.8, 83.1, 9
    value = str(config.get("notes", DEFAULT_NOTES))
    start = value.find(EMPHASIS)
    fig = canvas.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    px_per_mm = canvas.get_window_extent(renderer).width / 281
    # 項番2「最大電力・使用電力量説明」：固定文を左揃えで配置する。文字幅は描画処理で調整する。
    for size in (5.7, 5.6, 5.5):
        props = {
            bold: font_manager.FontProperties(
                family=rcParams["font.family"],
                size=size,
                weight="bold" if bold else "normal",
            )
            for bold in (False, True)
        }
        lines = _wrap_notes(value, start, renderer, props, px_per_mm, width)
        line_height = size * 25.4 / 72 * 1.3
        if len(lines) * line_height <= height:
            break

    _draw_note_lines(canvas, lines, x, y, size, line_height)
