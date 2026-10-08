"""再現可能な架空の直近12か月データを生成する。"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.data_service import bounds


def main():
    """設定した12か月について、再現可能な架空の電力CSVを生成する。

    --configと--outputを受け取り、固定乱数シード42で
    季節・時刻・曜日による変動を作る。生成値は実測値ではない。

    Raises:
        ValueError: 対象月の設定が不正な場合。
        OSError: 設定の読み込みまたはCSVの保存に失敗した場合。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("customer.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("sample.csv")
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    start, end, _ = bounds(config["target_month"])
    dates = pd.date_range(start, end, freq="30min", inclusive="left")
    # 同じ設定なら毎回同じ架空データになるよう、乱数のシードを固定する。
    rng = np.random.default_rng(42)
    hours = dates.hour.to_numpy() + dates.minute.to_numpy() / 60
    # 夕方の山、季節の変動、週末の低下を重ね、グラフの動作確認用データを作る。
    daily = 0.30 + 0.70 * np.exp(-(((hours - 17) / 5) ** 2))
    seasonal = 1 + 0.23 * np.cos((dates.month.to_numpy() - 8) / 12 * 2 * np.pi)
    weekly = np.where(dates.dayofweek.to_numpy() >= 5, 0.52, 1.0)
    kw = np.maximum(
        50, 1050 * daily * seasonal * weekly + rng.normal(0, 25, len(dates))
    )
    # 説明用に夏季の1枠を年最大値にする。
    peak = pd.Timestamp(year=start.year, month=8, day=19, hour=17)
    if peak < start:
        peak = peak + pd.DateOffset(years=1)
    kw[dates == peak] = 1386
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # サンプルCSVのkwは平均電力。DBのkWh入力とは単位が異なるので混同しない。
    pd.DataFrame(
        {"timestamp": dates.strftime("%Y-%m-%d %H:%M:%S"), "kw": np.round(kw, 3)}
    ).to_csv(args.output, index=False)
    print(f"架空のサンプル: {args.output} ({len(dates):,}枠)")


if __name__ == "__main__":
    main()
