"""No.5：④最大電力の推移の描画。"""

from rendering.styles import BLACK, POWER_BLUE, POWER_RED, format_number


def draw_no5(page, series, config):
    """No.5のグラフ・見出し・結果欄・助言欄を描画する。

    配置・色・説明文を変更するときは、この関数を編集する。

    Args:
        page (FirstPageCanvas): 1ページ目の描画用ページ。
        series (dict): build_contextの月別集計。値は換算済み。
        config (dict): 契約電力contract_kwを含む設定。
    """
    text, title, note, chart_axes = page.text, page.title, page.note, page.chart_axes
    month = series["monthly"]
    period = f"{month.index[0].year}年{month.index[0].month:02d}月〜{month.index[-1].year}年{month.index[-1].month:02d}月"
    dates = [f"{p.year}/{p.month:02d}" for p in month.index]
    title(142.0, 97.0, 4, f"最大電力の推移（{period}）")
    text(147, 105, "月ごとの最大電力［kW］の推移をグラフ化したものです", size=7)
    if series.get("partial_period"):
        text(147, 110, f'集計対象：{series["actual_period"]}', size=5.5)
    ax = chart_axes(153.5, 115.1, 126.5, 52.4, "電力(kW)")
    count = len(month)
    values = month["max"].to_numpy()
    peak = int(values.argmax())
    bars = ax.bar(
        range(count),
        values,
        width=0.53,
        color=[POWER_RED if i == peak else POWER_BLUE for i in range(count)],
    )
    ax.set_xlim(-0.6, count - 0.4)
    ax.set_xticks(range(count), dates, rotation=90, fontsize=6)
    # 換算済みの最大kWと、元からkWの契約値をそのまま使う。
    contract = float(config["contract_kw"])
    ax.set_ylim(0, max(1, values.max(), contract) * 1.1)
    labels = ax.bar_label(
        bars,
        labels=[format_number(v) for v in values],
        padding=3,
        fontsize=6.4,
        color=BLACK,
    )
    # 小数を省略せず、1か月分の幅へ文字サイズを合わせる。
    renderer = page.fig.canvas.get_renderer()
    available = ax.get_window_extent(renderer).width / count * 0.88
    for label in labels:
        width = renderer.get_text_width_height_descent(
            label.get_text(), label.get_fontproperties(), False
        )[0]
        if width > available:
            label.set_fontsize(label.get_fontsize() * available / width)
    ax.axhline(contract, color=POWER_RED, ls="--", lw=0.8, label="契約電力")
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.15), frameon=False, fontsize=6.8
    )
    note(
        173.8,
        184.6,
        32.1,
        7.0,
        [f"ピークは{month.index[peak].month:02d}月でした"],
        centered=True,
    )
    note(
        218.1,
        182.4,
        48.3,
        10.6,
        [
            f"次の{month.index[peak].month:02d}月に契約電力を",
            "超過しないよう気を付けましょう",
        ],
        advice=True,
    )
