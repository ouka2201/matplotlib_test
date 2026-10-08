"""30分平均電力（kW）を検証し、帳票用の値を作る。"""

import calendar
import math
import re
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd

WEEKDAYS = "月火水木金土日"


def bounds(target_month):
    """対象月を最終月とする直近12か月の期間を求める。

    Args:
        target_month (str): 最終対象月。YYYY-MM形式（例: 2026-06）。

    Returns:
        tuple[pandas.Timestamp, pandas.Timestamp, pandas.Timestamp]:
            対象期間の開始日時、終了日時、対象月の月初日時。終了日時は
            翌月1日00:00で、集計には含めない。

    Raises:
        ValueError: 対象月の形式または日付が不正な場合。
    """
    if not re.fullmatch(r"\d{4}-\d{2}", target_month):
        raise ValueError("target_monthはYYYY-MM形式で指定してください")
    month = pd.Timestamp(target_month + "-01")
    # 指定月の翌月1日を除外側の終端にする。そこから暦で1年戻り、うるう年にも対応する。
    end = month + pd.DateOffset(months=1)
    return end - pd.DateOffset(years=1), end, month


def load_data(path, target_month):
    """CSVの30分平均電力を読み込み、帳票に必要なデータを検証する。

    タイムゾーン付き日時は日本時間へ変換する。日時の重複や
    不正値は全入力行を検査し、その後で対象期間外の行を除外する。
    直近12か月内の実績期間を使う。期間の前後に実績がなくても受け付け、
    実績がある最初の日〜最後の日は、毎日48枠が連続することを確認する。

    Args:
        path (str | pathlib.Path): 入力CSVのパス。
        target_month (str): 最終対象月。YYYY-MM形式（例: 2026-06）。

    Returns:
        pandas.DataFrame: timestamp・kw列を含む日時昇順のデータ。
            timestampは日本時間のタイムゾーン情報なしの日時、kwは
            各30分枠の平均電力で、単位はkW。

    Raises:
        ValueError: 必須列の不足、不正な日時・電力、重複日時、
            実績期間内の欠損または30分刻みでない日時がある場合。
        OSError: CSVファイルを読み込めない場合。
    """
    df = pd.read_csv(path, dtype={"timestamp": str})
    # CSVとDBで検証条件をそろえるため、DataFrameの共通検証へ渡す。
    return validate_data(df, target_month)


def validate_data(df, target_month):
    """DataFrameの30分平均電力を検証し、対象期間の昇順データを返す。

    CSV入力とテーブル入力で同じ検証を使用する。呼び出し元のデータは変更しない。

    Args:
        df (pandas.DataFrame): timestampとkw列を持つデータ。
        target_month (str): 最終対象月。YYYY-MM形式。

    Returns:
        pandas.DataFrame: 直近12か月内の実績。期間は1日〜12か月。
            最初と最後の日を含め、毎日48枠の連続したデータ。

    Raises:
        ValueError: 必須列不足、不正値、重複、実績なし、期間途中の欠損がある場合。
    """
    # 検証中の型変換や並べ替えで、呼び出し元が持つDataFrameを変更しない。
    df = df.copy()
    if not {"timestamp", "kw"}.issubset(df.columns):
        raise ValueError("CSVにはtimestamp列とkw列が必要です")
    # タイムゾーン無しは日本時間。混在形式は黙って解釈せず拒否する。
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
        if df["timestamp"].dt.tz is not None:
            df["timestamp"] = (
                df["timestamp"].dt.tz_convert("Asia/Tokyo").dt.tz_localize(None)
            )
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            "日時は日本時間、または同一タイムゾーンのISO日時で指定してください"
        ) from exc
    # 内部の電力単位はkWに統一する。DB由来のkWhはこの関数へ来る前に換算済み。
    df["kw"] = pd.to_numeric(df["kw"], errors="raise")
    if (
        df["timestamp"].isna().any()
        or not np.isfinite(df["kw"]).all()
        or (df["kw"] < 0).any()
    ):
        raise ValueError("日時の空欄、電力の欠損・無限値・負数は利用できません")
    if df["timestamp"].duplicated().any():
        raise ValueError("同じtimestampが重複しています")
    start, end, _ = bounds(target_month)
    df = (
        df.loc[(df.timestamp >= start) & (df.timestamp < end)]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    if df.empty:
        raise ValueError("対象の直近12か月に実績データがありません")
    # 実績がある最初〜最後の日を検査する。実績の前後は0で埋めない。
    # DBは日別48列なのでCSVも1日48枠を要求し、途中の欠落日・枠を見逃さない。
    actual_start = df.timestamp.iloc[0].normalize()
    actual_end = df.timestamp.iloc[-1].normalize() + timedelta(days=1)
    expected = pd.date_range(actual_start, actual_end, freq="30min", inclusive="left")
    actual = pd.DatetimeIndex(df.timestamp)
    if not actual.equals(expected):
        missing = expected.difference(actual)
        unexpected = actual.difference(expected)
        raise ValueError(
            f"実績期間の30分データが不完全です。欠損={len(missing)}、時刻不整合={len(unexpected)}"
        )
    return df


def time_range(ts):
    """30分枠の開始時刻と終了時刻を表示用の文字列にする。

    日付をまたぐ場合は「23:30〜00:00」のように表示する。

    Args:
        ts (pandas.Timestamp): 表示対象の日時。時刻範囲では30分枠の開始日時。

    Returns:
        str: 「19:00〜19:30」形式の時刻範囲。
    """
    return f"{ts:%H:%M}〜{ts + timedelta(minutes=30):%H:%M}"


def date_label(ts):
    """日時を日本語の曜日付き日付に変換する。

    Args:
        ts (pandas.Timestamp): 表示対象の日時。時刻範囲では30分枠の開始日時。

    Returns:
        str: 「2026/06/01（月）」形式の日付。
    """
    return f"{ts:%Y/%m/%d}（{WEEKDAYS[ts.weekday()]}）"


def calendar_power(kw):
    """No.1用に、30分使用電力量を四捨五入してから2倍する。

    内部データは換算済みのkWなので、0.5時間を掛けてkWhへ戻す。
    Pythonのround（偶数丸め）ではなく四捨五入を使用する。
    例: 201kW → 100.5kWh → 101kWh → 表示202kW。

    Args:
        kw (float): 30分枠の平均電力。検証済みの非負・有限値。

    Returns:
        int: No.1のカレンダーとTOP3に表示する整数電力（kW）。
    """
    kwh = Decimal(str(kw)) / 2
    return int(kwh.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * 2


def most_common_labels(counts, names):
    """最多の区分を最大3件選び、半角スペースでつないだ文字列にする。

    同率の区分はcountsの表示順に選ぶ。仕様書No.6の月別・曜日別・
    時間帯別の特徴に共通で使用する。

    Args:
        counts (pandas.Series): 表示順に並んだ、空でない区分別の件数。
        names (dict): countsのindexをキー、表示名を値とする辞書。

    Returns:
        str: 最多の区分名を最大3件、半角スペースで結合した文字列。
    """
    leaders = counts.index[counts == counts.max()][:3]
    return " ".join(names[key] for key in leaders)


def peak_week_bounds(df, peak_timestamp):
    """No.7のピークを含む期間を、取得済みの日付範囲内で求める。

    原則はピーク日の直前の日曜から土曜まで。取得期間の端では
    7日間を前後へ移し、取得範囲自体が7日未満なら全日を使用する。
    この関数は範囲だけを求め、欠測枠の補完は行わない。

    Args:
        df (pandas.DataFrame): timestamp列を持つ取得データ。
        peak_timestamp (pandas.Timestamp): No.6の1位の30分枠の開始日時。

    Returns:
        tuple[pandas.Timestamp, pandas.Timestamp]: 開始日00:00と
            最終日の翌日00:00。後者は抽出条件に含めない。

    Raises:
        ValueError: データが空、またはピーク日が取得範囲外の場合。
    """
    if df.empty:
        raise ValueError("週の対象期間を求めるデータが空です")
    first = df.timestamp.min().normalize()
    last = df.timestamp.max().normalize()
    peak_day = pd.Timestamp(peak_timestamp).normalize()
    if not first <= peak_day <= last:
        raise ValueError("ピーク日が取得期間外です")
    if (last - first).days + 1 < 7:
        return first, last + timedelta(days=1)
    sunday = peak_day - timedelta(days=(peak_day.weekday() + 1) % 7)
    start = max(first, min(sunday, last - timedelta(days=6)))
    return start, start + timedelta(days=7)


def build_context(df, config):
    """検証済みの電力データを集計し、帳票とグラフ用の値を作る。

    電力量は平均電力×0.5時間でkWhへ換算する。同じ電力値の
    順位は日時の早い枠を優先する。期間端ではピークを含む7日間が
    対象期間内に収まるよう週の開始日を調整する。

    Args:
        df (pandas.DataFrame): timestamp（30分枠の開始日時）とkw（平均電力）を持つデータ。
        config (dict): 契約情報と対象月の設定。customer_name、address、
            customer_number、contract_kw、target_monthを用途に応じて使用する。
            issuer、holidays、is_sampleは任意設定。

    Returns:
        tuple[dict, dict]: 表示用辞書contextと集計データ辞書series。
            contextには期間、ピーク、順位表、週別表、TOP50の特徴を格納する。
            seriesにはdf（全枠）、day（対象月のピーク日の48枠）、
            daily（日別最大。kwは未丸め値、display_kwはNo.1の表示値）、
            monthly（月別集計）、top（上位50枠）、
            week（ピークを含む最大7日間）、各区分の件数を格納する。
            対象月に実績がない場合はday・dailyが空、日別ピークはNone。

    Raises:
        ValueError: 契約電力が正の有限数でない、対象月が不正、または実績がない場合。
        KeyError: 必須設定またはデータ列がない場合。
    """
    contract = float(config["contract_kw"])
    if not math.isfinite(contract) or contract <= 0:
        raise ValueError("contract_kwは正の有限数にしてください")
    start, end, month = bounds(config["target_month"])
    if df.empty:
        raise ValueError("集計対象の実績データがありません")
    df = df.sort_values("timestamp").copy()
    actual_start = df.timestamp.iloc[0].normalize()
    actual_end = df.timestamp.iloc[-1].normalize() + timedelta(days=1)
    # 日別欄は指定月を使う。別の月に置き換えず、実績がなければ空で扱う。
    last_month = df.loc[(df.timestamp >= month) & (df.timestamp < end)].copy()
    # 最大50枠。1日48枠だけの実績では48枠を使い、存在しない50位を作らない。
    top = df.sort_values(["kw", "timestamp"], ascending=[False, True]).head(50)
    peak = top.iloc[0]
    monthly_peak = (
        last_month.loc[last_month.kw.idxmax()] if not last_month.empty else None
    )
    day = (
        last_month.loc[last_month.timestamp.dt.date == monthly_peak.timestamp.date()]
        if monthly_peak is not None
        else last_month.copy()
    )
    daily_idx = last_month.groupby(last_month.timestamp.dt.date)["kw"].idxmax()
    daily = last_month.loc[daily_idx].copy()
    # No.1だけの表示値。集計・順位・No.2の48枠は、丸め前のkwを使用する。
    daily["display_kw"] = daily.kw.map(calendar_power)
    # 実績のある月だけを年月順に並べる。存在しない月を0kWhとはみなさない。
    months = pd.period_range(actual_start, actual_end - timedelta(days=1), freq="M")
    monthly = (
        df.groupby(df.timestamp.dt.to_period("M"))["kw"]
        .agg(["sum", "max"])
        .reindex(months)
    )
    # 平均電力kW×0.5時間で各枠の電力量に戻す。
    # DBの保存値がkWhなら、結果は保存されている使用電力量の月間合計と一致する。
    monthly["kwh"] = monthly["sum"] * 0.5
    # 月間値はNo.1の表示丸めを使わず、日別48枠の使用電力量をそのまま合計する。
    # 年月順のindexを使うため、最多・最少が同値なら早い月を選ぶ。
    # No.7はNo.6の1位を含む週。設定期間ではなく実際に取得した日付範囲へ収める。
    week_start, week_end = peak_week_bounds(df, peak.timestamp)
    week = (
        df.loc[(df.timestamp >= week_start) & (df.timestamp < week_end)]
        .sort_values("timestamp")
        .copy()
    )
    # 日別表は十進数で合計し、15501.023000000001のような計算誤差の桁を防ぐ。
    # 表示桁で丸めず、入力値の小数部を保ったkWhを求める。
    week_stats = week.groupby(week.timestamp.dt.date)["kw"].agg(
        kwh=lambda values: float(
            sum((Decimal(str(value)) for value in values), Decimal("0"))
            * Decimal("0.5")
        ),
        max="max",
    )
    # 同じ上位最大50枠を、月・曜日・開始時刻の時間帯ごとに数える。
    # ゼロ件の区分も埋めて、グラフの軸を毎回同じ順序にする。
    month_count = (
        top.groupby(top.timestamp.dt.to_period("M"))
        .size()
        .reindex(months, fill_value=0)
    )
    weekday_count = (
        top.groupby(top.timestamp.dt.dayofweek).size().reindex(range(7), fill_value=0)
    )
    hour_count = (
        top.groupby(top.timestamp.dt.hour).size().reindex(range(24), fill_value=0)
    )
    holidays = {pd.Timestamp(d).date() for d in config.get("holidays", [])}
    by_date = {r.timestamp.date(): r for _, r in daily.iterrows()}
    weeks = []
    for dates in calendar.Calendar(firstweekday=6).monthdayscalendar(
        month.year, month.month
    ):
        cells = []
        for number in dates:
            if not number:
                cells.append(None)
                continue
            ts = pd.Timestamp(year=month.year, month=month.month, day=number)
            r = by_date.get(ts.date())
            cells.append(
                {
                    "day": number,
                    "time": r.timestamp.strftime("%H:%M") if r is not None else None,
                    "kw": r.display_kw if r is not None else None,
                    "kind": (
                        "holiday"
                        if ts.weekday() == 6
                        else "saturday" if ts.weekday() == 5 else "weekday"
                    ),
                }
            )
        weeks.append(cells)
    daily_top = daily.sort_values(["kw", "timestamp"], ascending=[False, True]).head(3)
    month_str = f"{month:%Y年%m月}"
    # 同率の特徴は各グラフの表示順に最大3件まで、半角スペースで並べる。
    peak_month_str = most_common_labels(
        month_count, {p: f"{p.month:02d}月" for p in months}
    )
    # contextは見出し・説明文・表などに使う表示用データ。
    # seriesはグラフで使うDataFrameや件数集計。用途を分けて描画処理へ渡す。
    context = {
        "customer": config,
        "target_month": month_str,
        "period": f"{actual_start:%Y年%m月}〜{actual_end - timedelta(days=1):%Y年%m月}",
        "actual_period": f"{actual_start:%Y/%m/%d}〜{actual_end - timedelta(days=1):%Y/%m/%d}",
        "has_full_year": actual_start == start and actual_end == end,
        "weeks": weeks,
        "daily_top": [
            {
                "date": date_label(r.timestamp),
                "time": time_range(r.timestamp),
                "kw": r.display_kw,
            }
            for _, r in daily_top.iterrows()
        ],
        "day_date": (
            date_label(monthly_peak.timestamp) if monthly_peak is not None else None
        ),
        "day_peak_time": (
            time_range(monthly_peak.timestamp) if monthly_peak is not None else None
        ),
        "day_peak_kw": monthly_peak.kw if monthly_peak is not None else None,
        "energy_peak_month": monthly.kwh.idxmax().strftime("%Y年%m月"),
        "energy_min_month": monthly.kwh.idxmin().strftime("%Y年%m月"),
        "power_peak_month": monthly["max"].idxmax().strftime("%Y年%m月"),
        "peak_date": date_label(peak.timestamp),
        "peak_time": time_range(peak.timestamp),
        "peak_kw": peak.kw,
        "top_rows": [
            {
                "rank": i + 1,
                "date": date_label(r.timestamp),
                "time": r.timestamp.strftime("%H:%M"),
                "kw": r.kw,
            }
            for i, (_, r) in enumerate(top.head(10).iterrows())
        ],
        "rank50_row": (
            {
                "rank": 50,
                "date": date_label(top.iloc[49].timestamp),
                "time": top.iloc[49].timestamp.strftime("%H:%M"),
                "kw": top.iloc[49].kw,
            }
            if len(top) >= 50
            else None
        ),
        "count": len(df),
        "top_count": len(top),
        "top_label": f"TOP{len(top)}",
        "top_month": peak_month_str,
        "top_weekdays": most_common_labels(
            weekday_count, {i: WEEKDAYS[i] + "曜日" for i in range(7)}
        ),
        "top_hours": most_common_labels(
            hour_count, {i: f"{i:02d}時" for i in range(24)}
        ),
        "week_period": f"{week_start:%Y年%m月%d日}〜{week_end - timedelta(days=1):%Y年%m月%d日}",
        "week_rows": [
            {"date": date_label(pd.Timestamp(d)), "kwh": r["kwh"], "kw": r["max"]}
            for d, r in week_stats.iterrows()
        ],
        "notes": "最大電力は30分間の平均電力の最大値です。使用電力量は各枠の平均電力×0.5時間を合計しています。",
        "is_sample": bool(config.get("is_sample", False)),
    }
    series = {
        "day": day,
        "daily": daily,
        "monthly": monthly,
        "df": df,
        "top": top,
        "week": week,
        "month_count": month_count,
        "weekday_count": weekday_count,
        "hour_count": hour_count,
        "holidays": holidays,
        "partial_period": actual_start != start or actual_end != end,
        "actual_period": context["actual_period"],
    }
    return context, series
