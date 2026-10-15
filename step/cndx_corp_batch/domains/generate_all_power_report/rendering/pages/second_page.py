"""2ページ目の合成。No.6を上段、No.7を下段に配置する。"""

from ..canvas import SecondPageCanvas
from ..sections.no6_duration import draw_no6
from ..sections.no7_load_curve import draw_no7


def draw_second_page(series, context):
    """帳票レイアウト：帳票出力項目仕様説明書_No.6・7を2ページ目に配置する。

    Args:
        series (dict): build_contextによる全枠・TOP50・対象週の集計。
        context (dict): 期間・順位表・日別表などの表示用辞書。

    Returns:
        matplotlib.figure.Figure: 2ページ目。保存とcloseは呼び出し側で行う。
    """
    page = SecondPageCanvas()
    draw_no6(page, series, context)
    draw_no7(page, series, context)
    return page.fig
