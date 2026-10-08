"""No.4：③月ごとの使用電力量の推移の描画。"""

from rendering.styles import BLACK, ENERGY_BLUE, ENERGY_RED


def draw_no4(page, series):
    """No.4のグラフ・見出し・結果欄・助言欄を描画する。

    配置・色・説明文を変更するときは、この関数を編集する。

    Args:
        page (FirstPageCanvas): 1ページ目の描画用ページ。
        series (dict): build_contextの月別集計。値は換算済み。
    """
    text, title, note, chart_axes = page.text, page.title, page.note, page.chart_axes
    month = series["monthly"]
    period = f"{month.index[0].year}年{month.index[0].month:02d}月〜{month.index[-1].year}年{month.index[-1].month:02d}月"
    dates = [f"{p.year}/{p.month:02d}" for p in month.index]
    title(143.1, 2, 3, f"月ごとの使用電力量の推移（{period}）")
    text(147, 9, "月ごとの使用電力量［kWh］の推移をグラフ化したものです", size=7)
    if series.get("partial_period"):
        text(147, 15, f'集計対象：{series["actual_period"]}', size=5.5)
    ax = chart_axes(155.5, 19.5, 123.5, 40, "電力量(kWh)")
    count = len(month)
    values = month["kwh"].to_numpy()
    peak = int(values.argmax())
    ax.bar(
        range(count),
        values,
        width=0.53,
        color=[ENERGY_RED if i == peak else ENERGY_BLUE for i in range(count)],
    )
    ax.set_xlim(-0.6, count - 0.4)
    ax.set_xticks(range(count), dates, rotation=90, fontsize=6)
    ax.set_ylim(0, max(1, values.max()) * 1.15)
    for rank, i in enumerate(
        sorted(range(count), key=lambda j: (-values[j], j))[:3], 1
    ):
        ax.text(
            i,
            values[i] + values.max() * 0.035,
            f"第{rank}位",
            ha="center",
            fontsize=6.4,
            color=BLACK,
        )
    # 仕様書No.4の点線は、月間使用電力量の最小値に引く。
    # 最小値が同じ月が複数ある場合は、年月の早い月をコメントに採用する。
    minimum = int(values.argmin())
    ax.axhline(values[minimum], color=ENERGY_BLUE, ls=":", lw=0.8)
    note(
        171,
        77,
        35.5,
        11,
        ["使用電力量が最も多かったのは", f"{month.index[peak].month:02d}月でした。"],
        centered=True,
    )
    note(
        217,
        72.5,
        49.5,
        21.5,
        [
            f"{month.index[minimum].month:02d}月（青点線）を上回る使用電力量は",
            "空調による影響が大きいと思われます",
            "空調洗浄や高効率空調への更新が",
            "使用電力量削減につながります",
        ],
        advice=True,
    )
