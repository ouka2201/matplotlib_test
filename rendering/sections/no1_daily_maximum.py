"""No.1の見出し・カレンダー・TOP3を、ページへ直接描画する。"""

import calendar
from datetime import timedelta

from matplotlib.patches import Ellipse, Rectangle
import pandas as pd
from services.data_service import calendar_power
from rendering.styles import WIDTH

TITLE_BLUE = "#4a95c0"
SUNDAY = "#d59aa8"
SATURDAY = "#89b9df"
WEEKDAY = "#b4b8bb"
SUNDAY_BG = "#ffd7de"
WEEKDAY_BG = "#f2f2f2"
SATURDAY_BG = "#e7f0fb"
NOTE_BG = "#fff3ca"
TEXT = "#202020"


def draw_no1(page, daily, config):
    """No.1のカレンダーとTOP3を、既存のページFigureに描画する。

    左上原点・mm単位を使用する。対象月の4〜6週を固定領域に収め、
    日曜・平日・土曜の背景を仕様色で表示する。TOP3は丸め前の最大値から
    選び、同値では日時が早い日を優先する。表示電力はkWhを四捨五入して2倍する。

    Args:
        page (FirstPageCanvas): 1ページ目の共通描画先。
        daily (pandas.DataFrame): 各日1行のtimestamp・kw列を持つ日別最大電力。
        config (dict): target_monthに対象年月をYYYY-MM形式で指定する。

    Raises:
        ValueError: TOP3の文字が4.9pt以上で説明欄に収まらない場合。
        KeyError: 対象月の日別データまたは必須設定がない場合。
    """
    month = pd.Timestamp(config["target_month"] + "-01")
    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(month.year, month.month)
    by_day = {row.timestamp.day: row for _, row in daily.iterrows()}
    canvas = page.canvas

    # 年月部分も白地に青文字。写真に写った選択時の背景色は描かない。
    canvas.add_patch(
        Ellipse(
            (3.7935, 62.5456), 4.496, 4.3456, facecolor=TITLE_BLUE, edgecolor="none"
        )
    )
    canvas.text(
        3.7935,
        62.5456,
        "1",
        fontsize=9.6,
        color="white",
        ha="center",
        va="center",
        fontweight="bold",
    )
    canvas.text(
        7.306,
        62.5456,
        f"日ごとの最大電力：{month:%Y年%m月}",
        fontsize=11.1,
        fontweight="bold",
        color=TITLE_BLUE,
        ha="left",
        va="center",
    )
    canvas.text(
        5.62,
        69.2192,
        "日ごとの最大電力［kW］を表示したものです",
        fontsize=6.9,
        color=TEXT,
        ha="left",
        va="center",
    )

    left, width = 2.1075, 90.6225
    cell_width = width / 7
    header_top, header_height = 72.168, 5.3544
    for column, weekday in enumerate("日月火水木金土"):
        color = SUNDAY if column == 0 else SATURDAY if column == 6 else WEEKDAY
        canvas.add_patch(
            Rectangle(
                (left + column * cell_width, header_top),
                cell_width,
                header_height,
                facecolor=color,
                edgecolor="none",
            )
        )
        canvas.text(
            left + (column + 0.5) * cell_width,
            header_top + header_height / 2,
            weekday,
            fontsize=7.3,
            color="white",
            ha="center",
            va="center",
        )

    # 56.8808mmの表領域を週数で等分し、月の日数が変わっても下端を揃える。
    row_height = 56.8808 / len(weeks)
    for row_index, week in enumerate(weeks):
        top = header_top + header_height + row_index * row_height
        for column, day in enumerate(week):
            x = left + column * cell_width
            background = (
                SUNDAY_BG if column == 0 else SATURDAY_BG if column == 6 else WEEKDAY_BG
            )
            canvas.add_patch(
                Rectangle(
                    (x + 0.1405, top + 0.1164),
                    cell_width - 0.281,
                    row_height - 0.2328,
                    facecolor=background,
                    edgecolor="none",
                )
            )
            # 前月・翌月の空白セルは背景だけ描く。
            if not day:
                continue
            item = by_day[day]
            labels = [
                f"{month.month:02d}/{day:02d}",
                item.timestamp.strftime("%H:%M"),
                f"{calendar_power(item.kw):,}kW",
            ]
            for line_index, label in enumerate(labels):
                canvas.text(
                    x + cell_width / 2,
                    top + row_height * (0.27 + 0.23 * line_index),
                    label,
                    fontsize=6.4 if len(weeks) <= 5 else 6.0,
                    color=TEXT,
                    ha="center",
                    va="center",
                    fontweight="bold",
                )

    note_x, note_y, note_width, note_height = 94.5565, 97.5432, 44.5385, 19.5552
    canvas.add_patch(
        Rectangle(
            (note_x, note_y),
            note_width,
            note_height,
            facecolor=NOTE_BG,
            edgecolor="none",
        )
    )
    note_texts = [
        canvas.text(
            note_x + 1.405,
            note_y + 2.5608,
            "TOP3は以下のとおりでした",
            fontsize=6.8,
            color=TEXT,
            ha="left",
            va="center",
            fontweight="bold",
        )
    ]
    # 表示時の丸めで順位が変わらないよう、元のkwと日時で選ぶ。
    top3 = daily.sort_values(["kw", "timestamp"], ascending=[False, True]).head(3)
    for rank, (_, item) in enumerate(top3.iterrows(), start=1):
        ts = item.timestamp
        weekday = "月火水木金土日"[ts.weekday()]
        label = f"{rank}位 {ts.day}日（{weekday}） {ts:%H:%M}〜{ts + timedelta(minutes=30):%H:%M} {calendar_power(item.kw):,}kW"
        note_texts.append(
            canvas.text(
                note_x + 1.405,
                note_y + 2.5608 + rank * 4.656,
                label,
                fontsize=6.2,
                color=TEXT,
                ha="left",
                va="center",
            )
        )
    page.fig.canvas.draw()
    renderer = page.fig.canvas.get_renderer()
    available_width = (
        canvas.get_window_extent(renderer).width * (note_width - 2.81) / WIDTH
    )
    for text in note_texts:
        text_width = text.get_window_extent(renderer).width
        if text_width > available_width:
            size = text.get_fontsize() * available_width / text_width * 0.98
            if size < 4.9:
                raise ValueError(
                    "No.1のTOP3文字列が長すぎます。no1_daily_maximum.pyの配置を調整してください"
                )
            text.set_fontsize(size)
