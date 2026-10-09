"""No.6：⑤デュレーションカーブ、順位表、TOP50の特徴の描画。"""

from datetime import timedelta
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator
from rendering.styles import (
    TITLE,
    DURATION_BLUE,
    BLACK,
    TOP_BLUE,
    TOP_RED,
    format_number,
)


def duration_axis(df, segments=46):
    """電力降順のデータを等分し、各区間の中央日時を目盛りにする。

    区間の件数が偶数なら中央2枠のうち左側を選ぶ。日時を
    平均・補間せず、電力値と実際の発生日時の対応を保持する。
    データ件数が分割数より少ない場合は、各データを1区間とする。

    Args:
        df (pandas.DataFrame): timestamp（30分枠の開始日時）とkw（平均電力）を持つデータ。
        segments (int): 分割数。正の整数を指定する。既定値は46。

    Returns:
        tuple[pandas.DataFrame, numpy.ndarray, list[str]]: 電力降順・
            同値時は日時昇順のデータ、1始まりの目盛り位置、
            YYYY/MM/DD HH:MM形式の日時ラベル。

    Raises:
        ValueError: segmentsが0以下など、分割数が不正な場合。
    """
    if df.empty:
        raise ValueError("デュレーションカーブの実績データがありません")
    if not isinstance(segments, (int, np.integer)) or segments <= 0:
        raise ValueError("分割数は正の整数にしてください")
    ordered = df.sort_values(["kw", "timestamp"], ascending=[False, True]).reset_index(
        drop=True
    )
    # 電力順位の並び全体を46区間へ等分する。区間の件数差は最大1件。
    groups = np.array_split(np.arange(len(ordered)), min(segments, len(ordered)))
    # 日時を平均せず、中央位置にある実データを選ぶ。偶数件なら中央2件の左側。
    centers = [group[(len(group) - 1) // 2] for group in groups]
    ticks = np.asarray(centers) + 1  # 横軸の内部位置は1始まりの順位。
    labels = [ordered.iloc[i].timestamp.strftime("%Y/%m/%d %H:%M") for i in centers]
    return ordered, ticks, labels


def draw_no6(page, s, context, duration_data=None):
    """実績期間の電力順位と上位最大50枠の特徴を描画する。

    Args:
        page (SecondPageCanvas): 2ページ目の描画用ページ。
        s (dict): build_contextの全枠とTOP50の区分別集計。
        context (dict): 期間・順位表・特徴の表示用辞書。
        duration_data (tuple | None): 46区間の日時。省略時は本モジュールで作る。
    """
    canvas = page.canvas
    text, title, note, axes, table = (
        page.text,
        page.title,
        page.note,
        page.axes,
        page.table,
    )
    if duration_data is None:
        duration_data = duration_axis(s["df"])
    title(0.9, 5, f'デュレーションカーブ（{context["period"]}）')
    frames = len(s["df"])
    days = frames // 48
    text(
        6,
        8,
        f"30分ごとの需要電力［kW］{frames:,}コマを大きい順に並べたものです（48コマ/日×{days}日={frames:,}コマ）",
        size=7,
    )
    if not context.get("has_full_year", True):
        text(6, 11, f'実績期間：{context["actual_period"]}', size=5.5)
    top_label = context.get("top_label", "TOP50")
    # 電力順位と日時ラベルの対応はduration_axisで決定済み。
    # ここでは再ソートせず、そのまま曲線と横軸を描く。
    ordered, ticks, labels = duration_data
    # 大きな電力では桁区切りの目盛りが長くなるので、縦軸用の余白を増やす。
    left = 12.0 if ordered.kw.max() >= 1000 else 9.95
    ax = axes(left, 12.0, 108.95 - left, 47.2, "電力(kW)")
    rank = range(1, len(ordered) + 1)
    ax.fill_between(rank, ordered.kw, color=DURATION_BLUE)
    ax.plot(rank, ordered.kw, color=DURATION_BLUE, lw=0.4)
    ax.set_xlim(1, len(ordered))
    ax.set_ylim(0, max(1, ordered.kw.max()) * 1.1)
    ax.set_xticks(ticks, labels, rotation=90, fontsize=3.8)
    # 上位10件と50位は同じ順位から取得し、50位がなければ実績なしを表示する。
    # kWへの換算はDB取得時に済んでいる。
    top_rows = [
        [r["rank"], r["date"], r["time"], format_number(r["kw"])]
        for r in context["top_rows"]
    ]
    widths = [0.09, 0.46, 0.18, 0.27]
    table(
        1.05,
        74.8,
        34.5,
        27,
        ["順位", "年月日", "時分", "電力(kW)"],
        top_rows,
        widths,
        4.2,
    )
    r = context["rank50_row"]
    if r is not None:
        table(
            1.05,
            101.8,
            34.5,
            2.5,
            None,
            [[r["rank"], r["date"], r["time"], format_number(r["kw"])]],
            widths,
            4.2,
        )
    else:
        text(1.05, 102, f'50位の実績なし（全{context["count"]}コマ）', size=5.5)
    peak = s["top"].iloc[0].timestamp
    note(
        40.0,
        79.0,
        68.0,
        6.0,
        [
            f"ピークは、{peak:%m月%d日%H:%M}〜{peak+timedelta(minutes=30):%H:%M}に発生しています",
        ],
    )
    note(
        35.9,
        90.7,
        77.3,
        15.1,
        [
            "ピークの発生要因と思われる設備を一斉に稼働させず15分前後",
            "ずらすことや、業務の一部を他の曜日、季節にシフトすることが",
            "可能であればピークが抑制され、基本料金の低減につながります",
        ],
        advice=True,
    )

    # 上部右側は横長の共通見出し、3グラフ、その下に結果と助言を配置。
    canvas.add_patch(
        Rectangle((110.3, 12.5), 169.5, 7.9, facecolor="white", edgecolor=TITLE, lw=0.8)
    )
    text(
        190.5,
        14.7,
        "における特徴",
        size=9.6,
        color=TITLE,
        bold=True,
        ha="left",
    )
    text(190.5, 14.7, top_label, size=9.6, color="#e03531", bold=True, ha="right")
    specs = [
        ("month_count", "月別", 116.8, 31.0, 42.0),
        ("weekday_count", "曜日別", 165.9, 30.7, 27.4),
        ("hour_count", "時間帯別", 197.3, 30.7, 83.0),
    ]
    for key, label, x, y, w in specs:
        text(
            x + w / 2,
            24.0,
            f"【{label}】",
            size=11.5,
            color=TITLE,
            bold=True,
            ha="center",
        )
        counts = s[key]
        vals = counts.to_numpy()
        ax = axes(x, y, w, 39.1, "発生回数")
        bars = ax.bar(
            range(len(vals)),
            vals,
            width=0.53,
            color=[TOP_RED if v == vals.max() else TOP_BLUE for v in vals],
        )
        ax.set_ylim(0, max(1, vals.max()) * 1.2)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
        if key == "month_count":
            xt = [f"{p.month:02d}月" for p in counts.index]
        elif key == "weekday_count":
            xt = list("月火水木金土日")
        else:
            xt = [str(i) for i in range(24)]
        ax.set_xticks(
            range(len(vals)),
            xt,
            fontsize=5.2,
            rotation=90 if key == "month_count" else 0,
        )
        for bar, value in zip(bars, vals):
            if value:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + 0.35,
                    str(value),
                    fontsize=6,
                    ha="center",
                    color=BLACK,
                )
    note(
        169.0,
        74.0,
        55.0,
        15.7,
        [
            f"{top_label}を見ると、以下の特徴があります",
            f'月別で多いのは{context["top_month"]}',
            f'曜日別で多いのは{context["top_weekdays"]}',
            f'時間帯別で多いのは{context["top_hours"]}',
        ],
    )
    note(
        141.0,
        91.0,
        114.9,
        15.1,
        [
            "月ごと、曜日ごと、時間帯ごとの特徴を把握して、ピークの抑制につなげましょう",
            "稼働している設備を把握するためには、個別機器ごとの電力使用状況の見える化がおすすめです",
            "ピークの抑制には、高効率空調への更新や照明のLED化、受変電設備の高効率化も有効です",
        ],
        advice=True,
    )
