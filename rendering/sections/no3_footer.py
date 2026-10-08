"""仕様書No.3のロゴ画像と、部分的に太字の説明文をmatplotlibで配置する。"""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import matplotlib.image as mpimg
from matplotlib import font_manager, rcParams

from rendering.styles import DEFAULT_NOTES

EMPHASIS = "料金の算定期間とは異なる場合があります"


@lru_cache(maxsize=1)
def load_footer_logo():
    """同梱のTEPCOロゴPNGを読み込み、プロセス内で再利用する。

    顧客ごとの画像ファイル作成は行わない。ワーカープロセスごとに
    一度だけ画像を読み、1000件の処理でも同じロゴを再利用する。

    Returns:
        numpy.ndarray: matplotlibのimshowに渡すロゴ画像。

    Raises:
        OSError: 同梱ロゴの読み込みに失敗した場合。
    """
    path = Path(__file__).resolve().parents[2] / "assets" / "tepco_logo.png"
    return mpimg.imread(BytesIO(path.read_bytes()), format="png")


def draw_no3(page, config):
    """1ページ目の仕様書No.3を、ロゴと仕様書の説明文で描画する。

    ページの左上が原点、座標単位はmm。説明文の強調部分だけを
    別のTextオブジェクトとして描画し、太字にする。
    文字幅を実測して折り返し、外枠と中央の破線に収める。

    Args:
        page (FirstPageCanvas): 1ページ目の共通描画先。
        config (dict): notesで説明文を任意に置き換えられる。省略時は仕様書の全文。

    Raises:
        ValueError: 説明文が5.5pt以上で配置領域に収まらない場合。
        OSError: ロゴ画像を読み込めない場合。
    """
    canvas = page.canvas
    logo = load_footer_logo()
    # ロゴは文字列の代用ではなくPNGを貼り付け、元の縦横比を保つ。
    logo_x, logo_y, logo_width = 3, 180, 26
    logo_height = logo_width * logo.shape[0] / logo.shape[1]
    canvas.imshow(
        logo,
        extent=(logo_x, logo_x + logo_width, logo_y + logo_height, logo_y),
        aspect="auto",
    )

    x, y, width, height = 59, 184, 79.5, 9
    value = str(config.get("notes", DEFAULT_NOTES))
    start = value.find(EMPHASIS)
    fig = canvas.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    px_per_mm = canvas.get_window_extent(renderer).width / 281
    # テキストと太字の幅を描画フォントで測る。ページのmm座標へ換算して折り返す。
    for size in (5.7, 5.6, 5.5):
        props = {
            bold: font_manager.FontProperties(
                family=rcParams["font.family"],
                size=size,
                weight="bold" if bold else "normal",
            )
            for bold in (False, True)
        }
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
        line_height = size * 25.4 / 72 * 1.3
        if len(lines) * line_height <= height:
            break
    else:
        raise ValueError("No.3の注記が長すぎます。notesを短くしてください")

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
