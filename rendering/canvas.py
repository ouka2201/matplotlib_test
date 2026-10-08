"""ページ内のmm座標、見出し、注釈、グラフ・表の共通描画。"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.ticker import FuncFormatter, MaxNLocator
from rendering.styles import WIDTH, HEIGHT, TITLE, BLACK
from rendering.icons import draw_advice_bulb


class PageCanvas:
    """ページのFigureと、左上原点のmm座標を保持する。"""

    def __init__(self):
        """外枠内281×194mmのFigureと、左上原点の配置用Axesを準備する。"""
        self.fig = plt.figure(
            figsize=(WIDTH / 25.4, HEIGHT / 25.4), dpi=190, facecolor="white"
        )
        self.canvas = self.fig.add_axes([0, 0, 1, 1])
        self.canvas.set(xlim=(0, WIDTH), ylim=(HEIGHT, 0))
        self.canvas.axis("off")

    def text(self, x, y, value, size=7, color=BLACK, bold=False, **kwargs):
        """ページの固定座標に文字列を描画する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            value (str): 表示する文字列。
            size (float): 文字サイズ（pt）。
            color (str): matplotlibで使用する文字色。
            bold (bool): Trueなら登録済みの太字書体を使用する。
            **kwargs (Any): ax.textに渡す配置や行間などの追加引数。

        Returns:
            matplotlib.text.Text: 描画した文字オブジェクト。
        """
        item = self.canvas.text(
            x,
            y,
            value,
            fontsize=size,
            color=color,
            va="top",
            fontweight="bold" if bold else "normal",
            **kwargs,
        )
        return item


class FirstPageCanvas(PageCanvas):
    """1ページ目の描画形式。各No.の配置はsections側で指定する。"""

    def title(self, x, y, number, label):
        """丸い節番号と青い見出しを描画する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            number (int): 見出しの丸印に表示する節番号。
            label (str): 表示する文字列。
        """
        self.canvas.add_patch(
            Circle((x + 1.8, y + 1.8), 1.75, facecolor=TITLE, edgecolor="none")
        )
        self.text(
            x + 1.8,
            y + 0.3,
            str(number),
            size=8.1,
            color="white",
            ha="center",
            bold=True,
        )
        self.text(x + 5, y - 0.1, label, size=10.2, color=TITLE, bold=True)

    def note(self, x, y, w, h, lines, advice=False, centered=False):
        """黄色の結果欄または青色の助言欄を描画する。

        描画した文字幅と高さを確認し、必要に応じて縮小する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            w (float): 描画領域の幅（mm）。
            h (float): 描画領域の高さ（mm）。
            lines (list[str]): 説明欄に表示する行ごとの文字列。
            advice (bool): TrueならICON.png付きの青い助言欄、Falseなら黄色い結果欄を描く。
            centered (bool): Trueなら説明文を中央揃えにする。

        Raises:
            ValueError: 説明文を5.5pt以上で説明欄に収められない場合。
                またはICON.pngのサイズが90×89ピクセルではない場合。
            OSError: advice=Trueでassets/ICON.pngを読み込めない場合。
        """
        self.canvas.add_patch(
            Rectangle(
                (x, y),
                w,
                h,
                facecolor="#b7cce0" if advice else "#fff2c5",
                edgecolor="none",
            )
        )
        if advice:
            draw_advice_bulb(self.canvas, x, y)
        item = self.text(
            x + w / 2 if centered else x + 2,
            y + 2.3,
            "\n".join(lines),
            size=7.1,
            ha="center" if centered else "left",
            linespacing=1.55,
        )
        # 画像中の文字はブラウザー側で検査できないため、実際の描画幅で調整。
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        box = item.get_window_extent(renderer)
        limit = self.canvas.get_window_extent(renderer).width * (w - 4) / WIDTH
        if box.width > limit:
            item.set_fontsize(item.get_fontsize() * limit / box.width * 0.98)
        self.fig.canvas.draw()
        box = item.get_window_extent(self.fig.canvas.get_renderer())
        height_limit = self.canvas.get_window_extent().height * (h - 3) / HEIGHT
        if box.height > height_limit:
            item.set_fontsize(item.get_fontsize() * height_limit / box.height * 0.98)
        if item.get_fontsize() < 5.5:
            raise ValueError("1ページ目の説明欄が長すぎます。説明文を短くしてください")

    def chart_axes(self, x, y, w, h, ylabel):
        """固定位置にグラフ用Axesを作り、縦軸の基本書式を設定する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            w (float): 描画領域の幅（mm）。
            h (float): 描画領域の高さ（mm）。
            ylabel (str): 縦軸に表示する名前と単位。

        Returns:
            matplotlib.axes.Axes: グラフを描画するAxes。
        """
        # ページのmm座標を、Figureが要求する0〜1の相対座標へ変換する。
        ax = self.fig.add_axes([x / WIDTH, 1 - (y + h) / HEIGHT, w / WIDTH, h / HEIGHT])
        ax.set_ylabel(ylabel, fontsize=6.5, color=BLACK, labelpad=3)
        ax.tick_params(length=0, labelsize=6, colors=BLACK)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.spines[["top", "right"]].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#969696")
            ax.spines[side].set_linewidth(0.4)
        ax.set_ylim(bottom=0)
        return ax


class SecondPageCanvas(PageCanvas):
    """2ページ目の描画形式。各No.の配置はsections側で指定する。"""

    def title(self, y, number, label):
        """丸い節番号と青い見出しを描画する。

        Args:
            y (float): 左上を原点とする縦位置（mm）。
            number (int): 見出しの丸印に表示する節番号。
            label (str): 表示する文字列。
        """
        self.canvas.add_patch(
            Circle((3.8, y + 1.8), 1.75, facecolor=TITLE, edgecolor="none")
        )
        self.text(
            3.8, y + 0.3, str(number), size=8.1, color="white", bold=True, ha="center"
        )
        self.text(7, y, label, size=10.2, color=TITLE, bold=True)

    def note(self, x, y, w, h, lines, advice=False):
        """黄色の結果欄または青色の助言欄を描画する。

        描画した文字幅と高さを確認し、必要に応じて縮小する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            w (float): 描画領域の幅（mm）。
            h (float): 描画領域の高さ（mm）。
            lines (list[str]): 説明欄に表示する行ごとの文字列。
            advice (bool): TrueならICON.png付きの青い助言欄、Falseなら黄色い結果欄を描く。

        Raises:
            ValueError: 説明文を5.5pt以上で説明欄に収められない場合。
                またはICON.pngのサイズが90×89ピクセルではない場合。
            OSError: advice=Trueでassets/ICON.pngを読み込めない場合。
        """
        self.canvas.add_patch(
            Rectangle(
                (x, y),
                w,
                h,
                facecolor="#b7cce0" if advice else "#fff2c5",
                edgecolor="none",
            )
        )
        if advice:
            draw_advice_bulb(self.canvas, x, y)
        item = self.text(x + 2, y + 2, "\n".join(lines), size=7.1, linespacing=1.4)
        self.fig.canvas.draw()
        box = item.get_window_extent(self.fig.canvas.get_renderer())
        frame = self.canvas.get_window_extent()
        # 説明文の実際の描画幅と高さから縮小率を決め、欄内に収める。
        scale = min(
            1,
            (w - 4) / WIDTH * frame.width / box.width,
            (h - 3) / HEIGHT * frame.height / box.height,
        )
        item.set_fontsize(item.get_fontsize() * scale * 0.99)
        if item.get_fontsize() < 5.5:
            raise ValueError("2ページ目の説明欄が長すぎます。説明文を短くしてください")

    def axes(self, x, y, w, h, ylabel, grid=True):
        """固定位置にグラフ用Axesを作り、縦軸と補助線を設定する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            w (float): 描画領域の幅（mm）。
            h (float): 描画領域の高さ（mm）。
            ylabel (str): 縦軸に表示する名前と単位。
            grid (bool): Trueなら横方向の補助線を描く。

        Returns:
            matplotlib.axes.Axes: グラフを描画するAxes。
        """
        ax = self.fig.add_axes([x / WIDTH, 1 - (y + h) / HEIGHT, w / WIDTH, h / HEIGHT])
        ax.set_ylabel(ylabel, fontsize=6.5, labelpad=3, color=BLACK)
        ax.tick_params(length=0, labelsize=6, colors=BLACK)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.spines[["top", "right"]].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#999999")
            ax.spines[side].set_linewidth(0.4)
        if grid:
            ax.grid(axis="y", color="#d6d6d6", lw=0.4)
            ax.set_axisbelow(True)
        return ax

    def table(self, x, y, w, h, headers, rows, widths, size):
        """固定寸法の領域に、罫線付きの集計表を描画する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            w (float): 描画領域の幅（mm）。
            h (float): 描画領域の高さ（mm）。
            headers (list[str] | None): 表の列見出し。Noneなら見出し行を作らない。
            rows (list[list]): 表に表示する行データ。
            widths (list[float]): 各列の幅の比率。合計を1にする。
            size (float): 文字サイズ（pt）。

        Returns:
            matplotlib.table.Table: 描画した表オブジェクト。
        """
        ax = self.fig.add_axes([x / WIDTH, 1 - (y + h) / HEIGHT, w / WIDTH, h / HEIGHT])
        ax.axis("off")
        t = ax.table(
            cellText=rows,
            colLabels=headers,
            colWidths=widths,
            cellLoc="right",
            loc="center",
            bbox=[0, 0, 1, 1],
        )
        t.auto_set_font_size(False)
        t.set_fontsize(size)
        for (r, c), cell in t.get_celld().items():
            cell.set_edgecolor("#858b91")
            cell.set_linewidth(0.45)
            cell.set_facecolor("#e1e6eb" if headers is not None and r == 0 else "white")
            cell.PAD = 0.035
        return t
