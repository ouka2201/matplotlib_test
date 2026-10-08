"""帳票内のアイコンをmatplotlibの図形で描く。画像ファイルや絵文字は使わない。"""

from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.transforms import Affine2D


def draw_advice_bulb(ax, x, y):
    """青色の助言枠の左上に、青い電球アイコンを描画する。

    電球の輪郭・口金・白いフィラメントを図形で描くため、フォントに
    電球の文字がなくても同じ形を表示できる。PNGはページ全体の生成時に
    メモリ上で作られ、アイコン用の画像ファイルは作成しない。

    Args:
        ax (matplotlib.axes.Axes): 左上原点・mm単位のページ配置用Axes。
        x (float): 助言枠の左端（mm）。
        y (float): 助言枠の上端（mm）。
    """
    color = "#4b9ec0"
    # 電球の中心を枠の左上に置き、口金は枠内へ少し重ねる。
    cx, cy = x + 1, y - 0.8
    outline = Path(
        [
            (0, -1.15),
            (-0.68, -1.15),
            (-1.25, -0.61),
            (-1.25, 0),
            (-1.25, 0.61),
            (-0.65, 0.68),
            (-0.6, 1.3),
            (0.6, 1.3),
            (0.65, 0.68),
            (1.25, 0.61),
            (1.25, 0),
            (1.25, -0.61),
            (0.68, -1.15),
            (0, -1.15),
            (0, -1.15),
        ],
        [Path.MOVETO]
        + [Path.CURVE4] * 6
        + [Path.LINETO]
        + [Path.CURVE4] * 6
        + [Path.CLOSEPOLY],
    )
    ax.add_patch(
        PathPatch(
            outline,
            transform=Affine2D().translate(cx, cy) + ax.transData,
            facecolor=color,
            edgecolor="none",
            zorder=3,
        )
    )
    # 口金を2段に分け、丸印ではなく電球だと分かる形にする。
    for left, top, width, height in (
        (-0.58, 1.43, 1.16, 0.3),
        (-0.43, 1.86, 0.86, 0.23),
    ):
        ax.add_patch(
            Rectangle(
                (cx + left, cy + top),
                width,
                height,
                facecolor=color,
                edgecolor="none",
                zorder=3,
            )
        )
    # 白いフィラメントは描画済みの電球本体に重ねる。
    ax.plot(
        [cx - 0.42, cx - 0.16, cx, cx + 0.16, cx + 0.42],
        [cy + 0.08, cy + 0.42, cy + 0.18, cy + 0.42, cy + 0.08],
        color="white",
        linewidth=0.45,
        solid_capstyle="round",
        zorder=4,
    )
    for offset in (-0.16, 0.16):
        ax.plot(
            [cx + offset, cx + offset],
            [cy + 0.42, cy + 1.13],
            color="white",
            linewidth=0.4,
            zorder=4,
        )
