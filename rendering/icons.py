"""青い助言枠の左上に、指定されたICON.pngを配置する。"""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import matplotlib.image as mpimg

# 実行時の作業フォルダーによらず、プロジェクト内の画像を参照する。
ICON_PATH = Path(__file__).resolve().parents[1] / "assets" / "ICON.png"
ICON_SIZE_PX = (90, 89)  # 元画像の幅・高さ。帳票上の寸法はmmで指定する。
ICON_WIDTH_MM = 3.3


@lru_cache(maxsize=1)
def load_advice_icon():
    """90×89ピクセルのICON.pngを読み込み、プロセス内で再利用する。

    1000件の並列処理でも、各ワーカーは画像を一度だけ読み込む。
    顧客別のアイコン画像や一時ファイルは作成しない。画像を差し替えた
    場合は、読み込み済みのワーカープロセスを起動し直す。

    Returns:
        numpy.ndarray: matplotlibで描画する画像。PNGの透過情報も保持する。

    Raises:
        FileNotFoundError: assets/ICON.pngが配置されていない場合。
        OSError: PNG画像の読み込みに失敗した場合。
        ValueError: 画像の幅・高さが90×89ピクセルではない場合。
    """
    if not ICON_PATH.is_file():
        raise FileNotFoundError(
            f"青い助言枠の画像がありません。90×89ピクセルのICON.pngを"
            f"次の場所に配置してください: {ICON_PATH}"
        )
    icon = mpimg.imread(BytesIO(ICON_PATH.read_bytes()), format="png")
    height, width = icon.shape[:2]
    if (width, height) != ICON_SIZE_PX:
        raise ValueError(
            f"ICON.pngは幅90×高さ89ピクセルで用意してください。"
            f"現在のサイズ: 幅{width}×高さ{height}ピクセル"
        )
    return icon


def draw_advice_bulb(ax, x, y):
    """助言枠の左上に、ICON.pngを元の縦横比で描画する。

    PNGはページFigureへ直接配置する。幅3.3mmで縮小し、上端は枠より
    2mm上、左端は枠より0.25mm左に置き、下側を枠内に少し重ねる。

    Args:
        ax (matplotlib.axes.Axes): 左上原点・mm単位のページ配置用Axes。
        x (float): 助言枠の左端（mm）。
        y (float): 助言枠の上端（mm）。

    Returns:
        matplotlib.image.AxesImage: ページに配置したアイコン画像。

    Raises:
        FileNotFoundError: assets/ICON.pngが配置されていない場合。
        OSError: PNG画像の読み込みに失敗した場合。
        ValueError: 画像の幅・高さが90×89ピクセルではない場合。
    """
    icon = load_advice_icon()
    left, top = x - 0.25, y - 2
    height = ICON_WIDTH_MM * icon.shape[0] / icon.shape[1]
    # y軸は下向き。originとextentを指定して上下を反転させずに配置する。
    # aspect="auto"で、ページ全体のmm座標や他のグラフの位置を維持する。
    return ax.imshow(
        icon,
        extent=(left, left + ICON_WIDTH_MM, top + height, top),
        origin="upper",
        aspect="auto",
        interpolation="lanczos",
        zorder=3,
    )
