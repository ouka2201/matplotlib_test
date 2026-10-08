"""ページ寸法・仕様色・数値表示・共通注記の定義。"""

from decimal import Decimal

# A4横の用紙から左右上下8mmの余白を除いた、外枠内の寸法。
WIDTH, HEIGHT = 281, 194
TITLE = "#398fb9"
# 2ページ目の描画でも参照する共通色。
DURATION_BLUE = "#5684ad"
# No.2の棒色は帳票出力項目仕様に合わせる。他のグラフの配色とは個別に管理する。
DAILY_BLUE = "#72a3c9"
DAILY_RED = "#e15759"
# 仕様書No.4（③月別使用電力量）の棒と最小値の点線に使う色。
ENERGY_BLUE = "#72a3c9"
ENERGY_RED = "#e15759"
# 仕様書No.5（④月別最大電力）の棒と契約電力の点線に使う色。
POWER_BLUE = "#72a3c9"
POWER_RED = "#e15759"
BLACK = "#202020"

TOP_BLUE = "#72a3c9"
TOP_RED = "#e15759"
LOAD_ORANGE = "#f28e2b"


# No.3・No.7で使用する、仕様書の共通注記。
DEFAULT_NOTES = (
    "最大電力とは30分ごとの需要電力の最大値のことです。また、使用電力量とは"
    "30分ごとの使用電力量を対象期間（月初〜月末）において合計した値のことです。"
    "この対象期間は、料金の算定期間とは異なる場合がありますのでご留意ください。"
)


def format_number(value):
    """電力・電力量を桁区切りで表示し、不要な末尾の0を省く。

    No.5の仕様には整数への丸めがないため、小数部のある値も
    ラベルに保持する。例: 1000.5は「1,000.5」、1000.0は「1,000」。

    Args:
        value (float): 検証済みの電力（kW）または電力量（kWh）。

    Returns:
        str: 指数表記を使わない、桁区切りの電力値。
    """
    label = format(Decimal(str(value)), ",f")
    return label.rstrip("0").rstrip(".") if "." in label else label
