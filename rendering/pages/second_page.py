"""2ページ目の合成。No.6を上段、No.7を下段に配置する。"""

from rendering.canvas import SecondPageCanvas
from rendering.sections.no6_duration import draw_no6
from rendering.sections.no7_load_curve import draw_no7


def draw_second_page(series, config, context, duration_data=None):
    """No.6・No.7を1枚のFigureに合成する。

    Args:
        series (dict): build_contextによる全枠・TOP50・対象週の集計。
        config (dict): 帳票設定。将来のページ配置設定にも使う共通引数。
        context (dict): 期間・順位表・日別表などの表示用辞書。
        duration_data (tuple | None): 46区間の中央日時。省略時はNo.6側で作る。

    Returns:
        matplotlib.figure.Figure: 2ページ目。保存とcloseは呼び出し側で行う。
    """
    page = SecondPageCanvas()
    draw_no6(page, series, context, duration_data)
    draw_no7(page, series, context)
    return page.fig
