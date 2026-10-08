"""No.7：⑥ロードカーブ、日別表、説明欄・注記の描画。"""

from datetime import timedelta
from services.data_service import date_label
from rendering.styles import DEFAULT_NOTES
from rendering.styles import BLACK, TOP_BLUE, TOP_RED, LOAD_ORANGE, format_number


def draw_no7(page, s, context):
    """No.6の1位を含む週の電力を時系列で描画する。

    Args:
        page (SecondPageCanvas): 2ページ目の描画用ページ。
        s (dict): build_contextの対象週・TOP50。値は換算済みkW。
        context (dict): 週の期間と日別のkWh・最大kWを含む辞書。
    """
    text, title, note, axes, table = (
        page.text,
        page.title,
        page.note,
        page.axes,
        page.table,
    )
    peak = s["top"].iloc[0].timestamp
    peak_text = f"{peak:%m月%d日%H:%M}〜{peak+timedelta(minutes=30):%H:%M}"
    title(116, 6, f'ロードカーブ（{context["week_period"]}）')
    week = s["week"]
    week_days = week.timestamp.dt.normalize().nunique()
    week_frames = len(week)
    week_label = "1週間" if week_days == 7 else f"{week_days}日間"
    text(
        6,
        123,
        f"⑤におけるピーク発生日を含む{week_label}について、30分ごとの需要電力［kW］{week_frames}コマを時系列に並べたものです（48コマ/日×{week_days}日={week_frames}コマ）",
        size=6.8,
    )
    # 通常は7日×48枠。期間選定側で7日未満になった場合も実データの件数で描画する。
    ax = axes(14, 137, 202, 43, "電力(kW)")
    # 昼休みの12:00・12:30も青。No.6の1位の日時だけを赤で上書きする。
    colors = [
        LOAD_ORANGE if 8 <= ts.hour < 12 or 13 <= ts.hour < 18 else TOP_BLUE
        for ts in week.timestamp
    ]
    colors[week.timestamp.tolist().index(peak)] = TOP_RED
    ax.bar(range(week_frames), week.kw, width=0.9, color=colors)
    ax.set_xlim(-0.5, week_frames - 0.5)
    ax.set_ylim(0, max(1, week.kw.max()) * 1.08)
    xt, xtlabels = [], []
    # 1日48枠を基準に日付の境界線と0・6・12・18時の目盛りを置く。
    for i in range(week_days):
        ts = week.iloc[i * 48].timestamp
        ax.axvline(i * 48 - 0.5, color="#8d969e", lw=0.5)
        ax.text(
            i * 48 + 23.5,
            1.105,
            date_label(ts),
            transform=ax.get_xaxis_transform(),
            ha="center",
            fontsize=6,
            color=BLACK,
        )
        xt.extend([i * 48, i * 48 + 12, i * 48 + 24, i * 48 + 36])
        xtlabels.extend(["0", "6", "12", "18"])
    ax.set_xticks(xt, xtlabels, fontsize=5.5)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", pad=2)
    text(151, 128, "橙：08〜12時・13〜18時 ／ 青：その他 ／ 赤：1位", size=5.5)
    # 日別kWhは元の48枠の合計、最大kWは換算済み。端数を丸めず、再度2倍しない。
    rows = [
        [r["date"], format_number(r["kwh"]), format_number(r["kw"])]
        for r in context["week_rows"]
    ]
    table(
        219,
        150,
        59,
        26,
        ["年月日", "電力量(kWh)", "最大電力(kW)"],
        rows,
        [0.45, 0.28, 0.27],
        5.7,
    )
    note(
        7,
        183,
        74,
        9,
        [
            f"ピークは、{peak_text}に発生しています",
            "当該日を含む一週間の電力の使い方に注目してください",
        ],
    )
    note(
        85,
        183,
        95,
        10,
        [
            "年間を通じて日中を中心に電気を使用しており、かつ土・日曜日も",
            "使用している場合、特に太陽光発電システムの導入が効果的です",
        ],
        advice=True,
    )
    # 仕様書の注記全文を3行で描画する。1ページ目と同じ定義を使い、文面の差を防ぐ。
    footer_lines = DEFAULT_NOTES.replace(
        "30分ごとの使用電力量", "\n30分ごとの使用電力量"
    ).replace("この対象期間は、", "\nこの対象期間は、")
    text(184, 183.5, footer_lines, size=5.5, linespacing=1.4)
    text(278, 192, "発行元：東京電力エナジーパートナー株式会社", size=5.3, ha="right")
