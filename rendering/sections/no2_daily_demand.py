"""No.2：②30分ごとの需要電力の推移の描画。"""

from datetime import timedelta
from rendering.styles import DAILY_BLUE, DAILY_RED


def draw_no2(page, series):
    """No.1で1位になった日の48枠と、ピークの時間帯を描画する。

    Args:
        page (FirstPageCanvas): 1ページ目の描画用ページ。
        series (dict): build_contextが返すday。未丸めのkWを使用する。
    """
    text, title, note, chart_axes = page.text, page.title, page.note, page.chart_axes
    # 左下の日別グラフは、指定月内で最大電力が発生した日の48枠を表示する。
    day = series["day"]
    if day.empty:
        title(2, 133.6, 2, "30分ごとの需要電力の推移")
        text(5, 142, "対象月に実績がないため、日別グラフは表示しません", size=6.8)
        return
    stamp = day.iloc[0].timestamp
    weekday = "月火水木金土日"[stamp.weekday()]
    title(2, 133.6, 2, f"30分ごとの需要電力の推移：{stamp:%Y年%m月%d日}（{weekday}）")
    text(
        5,
        142,
        "①における1位の日について、30分ごとの需要電力［kW］48コマをグラフ化したものです",
        size=6.8,
    )
    ax = chart_axes(11.85, 146.5, 78.5, 28.3, "電力(kW)")
    # DBの30分使用電力量(kWh)は取得時に2倍してkwへ換算済み。
    # ここでは再換算せず、No.1の1位と同じ日の48枠をそのまま描く。
    values = day.kw.to_numpy()
    peak = int(values.argmax())
    # 同じ最大値が複数ある場合も、No.1と同じく最も早い枠をピークとして強調する。
    ax.bar(
        range(48),
        values,
        width=0.82,
        color=[DAILY_RED if i == peak else DAILY_BLUE for i in range(48)],
    )
    ax.set_xlim(-0.7, 47.7)
    ax.set_ylim(0, max(1, values.max()) * 1.1)
    ax.set_xticks(range(0, 48, 2), [str(i) for i in range(24)], fontsize=5.3)
    ts = day.iloc[peak].timestamp
    note(
        91.2,
        158.1,
        46.5,
        10.6,
        [
            f"最大電力は、{ts:%H:%M}〜{ts+timedelta(minutes=30):%H:%M}に",
            "発生しています",
        ],
    )
