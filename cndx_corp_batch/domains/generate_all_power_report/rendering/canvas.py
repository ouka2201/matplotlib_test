"""ページ内のmm座標を使い、見出し・注釈・グラフ・表を描画する共通処理。"""

from typing import Any

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator

from .icons import draw_advice_bulb
from .styles import BLACK, HEIGHT, TITLE, WIDTH


class PageCanvas:
    """ページのFigureと、左上を原点とするmm座標を保持する。"""

    def __init__(self) -> None:
        """外枠内281×194mmのFigureと、左上を原点とする配置用Axesを準備する。"""
        self.fig = plt.figure(
            figsize=(WIDTH / 25.4, HEIGHT / 25.4), dpi=190, facecolor="white"
        )
        self.canvas = self.fig.add_axes([0, 0, 1, 1])
        self.canvas.set(xlim=(0, WIDTH), ylim=(HEIGHT, 0))
        self.canvas.axis("off")

    def text(
        self,
        x: float,
        y: float,
        value: str,
        size: float = 7,
        color: str = BLACK,
        bold: bool = False,
        **kwargs: Any,
    ) -> Any:
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
    """1ページ目の描画形式。各帳票No.の配置はsections内の描画処理で指定する。"""

    def title(self, x: float, y: float, number: int, label: str) -> Any:
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
        self.text(x + 5, y - 0.1, label, size=11.5, color=TITLE, bold=True)

    def note(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        lines: list[str],
        advice: bool = False,
        centered: bool = False,
    ) -> Any:
        """黄色の結果欄または青色の助言欄を描画する。

        描画した文字幅と高さを確認し、必要に応じて縮小する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            w (float): 描画領域の幅（mm）。
            h (float): 描画領域の高さ（mm）。
            lines (list[str]): 説明欄に表示する行ごとの文字列。
            advice (bool): TrueならICON.png付きの青い助言欄、
                Falseなら黄色い結果欄を描く。
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
                facecolor="#b5d7ea" if advice else "#fff2cc",
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
            linespacing=1.35,
        )
        # 画像中の文字はブラウザー側で検査できないため、実際の描画幅を測って調整する。
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

    def chart_axes(self, x: float, y: float, w: float, h: float, ylabel: str) -> Any:
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
        ax.grid(axis="y", color="#f2f2f2", lw=0.4)
        ax.set_axisbelow(True)
        ax.set_ylim(bottom=0)
        return ax


class SecondPageCanvas(PageCanvas):
    """2ページ目の描画形式。各帳票No.の配置はsections内の描画処理で指定する。"""

    def title(self, y: float, number: int, label: str) -> Any:
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
        self.text(7, y, label, size=11.5, color=TITLE, bold=True)

    def note(
        self, x: Any, y: Any, w: Any, h: Any, lines: Any, advice: Any = False
    ) -> Any:
        """黄色の結果欄または青色の助言欄を描画する。

        描画した文字幅と高さを確認し、必要に応じて縮小する。

        Args:
            x (float): 左上を原点とする横位置（mm）。
            y (float): 左上を原点とする縦位置（mm）。
            w (float): 描画領域の幅（mm）。
            h (float): 描画領域の高さ（mm）。
            lines (list[str]): 説明欄に表示する行ごとの文字列。
            advice (bool): TrueならICON.png付きの青い助言欄、
                Falseなら黄色い結果欄を描く。

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
                facecolor="#b5d7ea" if advice else "#fff2cc",
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
        size = item.get_fontsize() * scale * 0.99
        item.set_fontsize(max(5.5, size))
        if size < 5.5:
            # 余裕を持たせた計算で最小サイズを下回っても、
            # 5.5ptで実測した文字が欄内に収まれば描画する。
            box = item.get_window_extent(self.fig.canvas.get_renderer())
            if (
                box.width > (w - 4) / WIDTH * frame.width
                or box.height > (h - 3) / HEIGHT * frame.height
            ):
                raise ValueError(
                    "2ページ目の説明欄が長すぎます。説明文を短くしてください"
                )

    def axes(
        self, x: Any, y: Any, w: Any, h: Any, ylabel: Any, grid: Any = True
    ) -> Any:
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

    def table(
        self,
        x: Any,
        y: Any,
        w: Any,
        h: Any,
        headers: Any,
        rows: Any,
        widths: Any,
        size: Any,
    ) -> Any:
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
        for (r, _c), cell in t.get_celld().items():
            cell.set_edgecolor("#202020")
            cell.set_linewidth(0.4)
            cell.set_facecolor("#e5e5e5" if headers is not None and r == 0 else "white")
            cell.PAD = 0.035
        # 順位表は幅が狭いため、日付や小数が隣の列にはみ出さないようにする。
        renderer = self.fig.canvas.get_renderer()
        table_width = ax.get_window_extent(renderer).width
        for (_, column), cell in t.get_celld().items():
            item = cell.get_text()
            text_width = renderer.get_text_width_height_descent(
                item.get_text(), item.get_fontproperties(), False
            )[0]
            available = table_width * widths[column] * (1 - 2 * cell.PAD)
            if text_width > available:
                item.set_fontsize(size * available / text_width * 0.98)
        return t
