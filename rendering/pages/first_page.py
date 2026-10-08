"""1ページ目の合成。各No.の具体的な描画はsectionsで行う。"""

from rendering.canvas import FirstPageCanvas
from rendering.sections.no0_contract import draw_no0
from rendering.sections.no1_daily_maximum import draw_no1
from rendering.sections.no2_daily_demand import draw_no2
from rendering.sections.no3_footer import draw_no3
from rendering.sections.no4_monthly_energy import draw_no4
from rendering.sections.no5_monthly_power import draw_no5


def draw_first_page(series, config):
    """No.0〜No.5を見本の配置で1枚のFigureに合成する。

    Args:
        series (dict): build_contextによる集計結果。
        config (dict): 契約情報と対象年月。

    Returns:
        matplotlib.figure.Figure: 1ページ目。保存とcloseは呼び出し側で行う。
    """
    page = FirstPageCanvas()
    # 全No.を同じFigureへ直接描画する。配置・寸法は各No.のファイルで調整する。
    draw_no0(page, config)
    draw_no1(page, series["daily"], config)
    # 既存の描画順を維持する。③・④は仕様書ではNo.4・No.5に対応する。
    draw_no4(page, series)
    draw_no5(page, series, config)
    draw_no2(page, series)
    draw_no3(page, config)
    return page.fig
