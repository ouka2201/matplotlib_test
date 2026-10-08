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
    title(143.1, 100, 4, f"最大電力の推移（{period}）")
    text(147, 107, "月ごとの最大電力［kW］の推移をグラフ化したものです", size=7)
    ax = chart_axes(155.5, 120, 123.5, 47, "電力(kW)")
    values = month["max"].to_numpy()
    peak = int(values.argmax())
    bars = ax.bar(
        range(12),
        values,
        width=0.53,
        color=[POWER_RED if i == peak else POWER_BLUE for i in range(12)],
    )
    ax.set_xlim(-0.6, 11.6)
    ax.set_xticks(range(12), dates, rotation=90, fontsize=6)
    # 換算済みの最大kWと、元からkWの契約値をそのまま使う。
    contract = float(config["contract_kw"])
    ax.set_ylim(0, max(1, values.max(), contract) * 1.22)
    ax.bar_label(
        bars,
        labels=[format_number(v) for v in values],
        padding=3,
        fontsize=6.4,
        color=BLACK,
    )
    ax.axhline(contract, color=POWER_RED, ls=":", lw=0.8, label="契約電力")
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.15), frameon=False, fontsize=6.8
    )
    note(
        175.5,
        185,
        31.5,
        7.5,
        [f"ピークは{month.index[peak].month:02d}月でした"],
        centered=True,
    )
    note(
        218.5,
        182,
        47.5,
        10.8,
        [
            f"次の{month.index[peak].month:02d}月に契約電力を",
            "超過しないよう気を付けましょう",
        ],
        advice=True,
    )
