"""No.6のデュレーションカーブだけを作成する単独プログラム。

必要なライブラリ: numpy、matplotlib（Python 3.12で実行可能）。
例: python duration_curve.py --max-kw 1600 --month 2026-06
メイリオはWindowsで自動検出する。他の環境では--fontで指定する。
"""

import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 画面のない環境でも画像を生成する。
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np


def make_sample_data(max_kw, month="2026-06", seed=42):
    """指定月を含む12か月の30分データを自動生成する。

    架空データを乱数で作り、最大値がmax_kwになるよう全体を調整する。
    seedが同じなら同じデータになる。うるう年も期間から件数を計算する。

    Args:
        max_kw (float): 生成するデータの最大電力（kW）。有限の正数。
        month (str): レポート対象月。YYYY-MM形式。
        seed (int): 乱数のシード。0以上の整数。

    Returns:
        tuple[list[datetime], numpy.ndarray]: 時系列順の開始日時と電力（kW）。

    Raises:
        ValueError: 最大電力、対象月、シードが不正な場合。
    """
    if not np.isfinite(max_kw) or max_kw <= 0:
        raise ValueError("最大電力は0より大きい有限の数値にしてください")
    target = datetime.strptime(month, "%Y-%m")
    # 翌月1日を終端にし、そこから12か月前を始端にする。終端は含めない。
    end = datetime(target.year + target.month // 12, target.month % 12 + 1, 1)
    start = end.replace(year=end.year - 1)
    count = (end - start).days * 48
    timestamps = [start + timedelta(minutes=30 * i) for i in range(count)]
    samples = np.random.default_rng(seed).weibull(1.7, count) + 0.2
    power = samples / samples.max() * max_kw
    return timestamps, power


def draw_duration_curve(timestamps, power, font=None):
    """縦軸・横軸を含むデュレーションカーブだけを描画する。

    電力降順、同値なら日時昇順に並べる。全順位を46区間に等分し、
    各区間の中央の実データの日時を横軸に表示する。偶数件なら中央2件の
    左側を採用する。日時は時系列順ではなく、その電力順位の発生日時。

    Args:
        timestamps (list[datetime]): 30分枠の開始日時。
        power (numpy.ndarray): 日時と対応する平均電力（kW）。
        font (str | Path | None): メイリオのフォントファイル。
            省略時はWindowsの標準配置または登録済みのメイリオを使用する。

    Returns:
        matplotlib.figure.Figure: グラフだけのFigure。保存とcloseは呼び出し側で行う。

    Raises:
        ValueError: 電力に欠損・負数がある、または件数が不正な場合。
        FileNotFoundError: 指定したフォントファイルが存在しない場合。
        RuntimeError: メイリオが見つからない場合。
    """
    power = np.asarray(power, dtype=float)
    if power.ndim != 1 or len(power) < 2 or len(timestamps) != len(power):
        raise ValueError("日時と電力は同じ件数で、2件以上にしてください")
    if not np.isfinite(power).all() or (power < 0).any():
        raise ValueError("電力は欠損のない、0以上の有限の数値にしてください")

    if font is None:
        candidate = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/meiryo.ttc"
        if candidate.is_file():
            font = candidate
        else:
            try:
                font = font_manager.findfont("Meiryo", fallback_to_default=False)
            except ValueError as error:
                raise RuntimeError(
                    "メイリオがありません。--fontでフォントを指定してください"
                ) from error
    if not Path(font).is_file():
        raise FileNotFoundError(font)
    font_props = font_manager.FontProperties(fname=str(font))

    # 電力と日時を一緒に並べ替え、両者の対応を保持する。
    dates = np.asarray(timestamps, dtype="datetime64[us]")
    order = np.lexsort((dates, -power))
    ordered_power = power[order]
    groups = np.array_split(np.arange(len(power)), min(46, len(power)))
    centers = np.array([group[(len(group) - 1) // 2] for group in groups])
    labels = [timestamps[order[i]].strftime("%Y/%m/%d %H:%M") for i in centers]
    ranks = np.arange(1, len(power) + 1)

    # 帳票と同じ配色。見出し・順位表・助言枠は描かず、グラフだけを作る。
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    ax.fill_between(ranks, ordered_power, color="#5684ad")
    ax.plot(ranks, ordered_power, color="#5684ad", linewidth=0.4)
    ax.set_xlim(1, len(power))
    ax.set_ylim(0, max(1, ordered_power.max()) * 1.1)
    ax.set_ylabel("電力(kW)", fontproperties=font_props, fontsize=10)
    ax.set_xticks(centers + 1, labels, rotation=90, fontsize=6.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.tick_params(length=0, labelsize=6.5, colors="#202020")
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(font_props)
        label.set_fontsize(6.5)
    ax.spines[["top", "right"]].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#999999")
        ax.spines[side].set_linewidth(0.4)
    return fig


def main():
    """最大電力・対象月を受け取り、グラフをPNG画像として保存する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-kw", type=float, default=1600, help="最大電力（kW）")
    parser.add_argument("--month", default="2026-06", help="対象月（YYYY-MM）")
    parser.add_argument("--seed", type=int, default=42, help="乱数のシード")
    parser.add_argument("--font", type=Path, help="例: C:/Windows/Fonts/meiryo.ttc")
    parser.add_argument("--output", type=Path, default=Path("duration_curve.png"))
    args = parser.parse_args()
    timestamps, power = make_sample_data(args.max_kw, args.month, args.seed)
    fig = draw_duration_curve(timestamps, power, args.font)
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, format="png", dpi=190, facecolor="white")
    finally:
        plt.close(fig)
    print(
        f"画像: {args.output.resolve()} / {len(power):,}コマ / 最大電力: {power.max():g}kW"
    )


if __name__ == "__main__":
    main()
