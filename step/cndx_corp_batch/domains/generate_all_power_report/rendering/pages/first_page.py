"""1ページ目の合成。各帳票No.の描画はsections内の処理で行う。"""

from ..canvas import FirstPageCanvas
from ..sections.no0_contract import draw_no0
from ..sections.no1_daily_maximum import draw_no1
from ..sections.no2_daily_demand import draw_no2
from ..sections.no3_footer import draw_no3
from ..sections.no4_monthly_energy import draw_no4
from ..sections.no5_monthly_power import draw_no5


def draw_first_page(series, config):
    """帳票レイアウト：帳票出力項目仕様説明書_No.0～5を1ページ目に配置する。

    Args:
        series (dict): build_contextによる集計結果。
        config (dict): 契約情報と対象年月。

    Returns:
        matplotlib.figure.Figure: 1ページ目。保存とcloseによる終了処理は呼び出し側で行う。
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
