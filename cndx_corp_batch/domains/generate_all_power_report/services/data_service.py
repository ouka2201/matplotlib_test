"""処理7・9～16：30分需要電力（kW）の型・期間を整え、帳票用の値を集計する。"""

import calendar
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

WEEKDAYS = "月火水木金土日"


def bounds(target_month):
    """データ項目更新仕様説明書No.6：対象月を含む1年分の取得期間を求める。

    Args:
        target_month (str): 最終対象月。YYYYMM形式（例: 202606）。

    Returns:
        tuple[pandas.Timestamp, pandas.Timestamp, pandas.Timestamp]:
            対象期間の開始日時、終了日時、対象月の月初日時。終了日時は
            翌月1日00:00で、集計には含めない。
    """
    month = pd.Timestamp(target_month + "01")
    # 指定月の翌月1日を抽出範囲に含めない終了日時とする。そこから暦に従って1年戻り、うるう年にも対応する。
    end = month + pd.DateOffset(months=1)
    return end - pd.DateOffset(years=1), end, month


def validate_data(df, target_month):
    """処理7の実装補助：30分値の型変換と対象期間の抽出・日時順ソートを行う。

    日時は日本時間に揃えたうえでタイムゾーン情報を除き、電力は換算済みのkWとして扱う。
    欠損日・重複日時・負数・実績件数の検査は行わない。

    Args:
        df (pandas.DataFrame): timestamp・kw列を持つデータ。
        target_month (str): レポート作成対象年月。YYYYMM形式。

    Returns:
        pandas.DataFrame: 対象月を含む直近12か月の取得済みデータ。日時昇順。

    Raises:
        KeyError: timestamp・kw列がない場合。
        ValueError: 日時・電力・対象年月を変換できない場合。
    """
    # 型変換や並べ替えで、呼び出し元のDataFrameを変更しない。
    df = df.copy()
    # タイムゾーンなしの日時は日本時間として扱い、タイムゾーン付きの日時は日本時間へ変換する。

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = (
            df["timestamp"].dt.tz_convert("Asia/Tokyo").dt.tz_localize(None)
        )
    # 内部の電力単位はkWに統一する。DBから取得したkWh値は、この関数に渡す前に換算している。
    df["kw"] = pd.to_numeric(df["kw"], errors="raise")

    start, end, _ = bounds(target_month)
    df = (
        df.loc[(df.timestamp >= start) & (df.timestamp < end)]
        .sort_values("timestamp")
        .reset_index(drop=True)
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
    """帳票出力項目仕様説明書_No.1：30分使用電力量を四捨五入してから2倍する。

    内部データは換算済みのkWなので、0.5時間を掛けてkWhへ戻す。
    Pythonのround（偶数丸め）ではなく四捨五入を使用する。
    例: 201kW → 100.5kWh → 101kWh → 表示202kW。

    Args:
        kw (float): 30分枠の需要電力（kW）。この関数では非負・有限値の検査を行わない。

    Returns:
        int: No.1のカレンダーとTOP3に表示する整数の電力値（kW）。
    """
    kwh = Decimal(str(kw)) / 2
    return int(kwh.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * 2


def most_common_labels(counts, names):
    """帳票出力項目仕様説明書_No.6 項番19：最多の区分を最大3件、半角空白で連結する。

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
    """帳票出力項目仕様説明書_No.7 項番2：ピークを含む週を取得済みの日付範囲に収める。

    原則として、ピーク日を含む日曜から土曜までを対象とする。取得期間の端では
    7日間を前後へ移し、取得範囲が7日未満なら、取得したすべての日を使用する。
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
    first = df.timestamp.min().normalize()
    last = df.timestamp.max().normalize()
    peak_day = pd.Timestamp(peak_timestamp).normalize()
    if (last - first).days + 1 < 7:
        return first, last + timedelta(days=1)
    sunday = peak_day - timedelta(days=(peak_day.weekday() + 1) % 7)
    start = max(first, min(sunday, last - timedelta(days=6)))
    return start, start + timedelta(days=7)


def build_context(df, config):
    """処理9～16／帳票出力項目仕様説明書_No.1～7：30分需要電力を集計する。

    電力量は平均電力×0.5時間でkWhへ換算する。電力値が同じ場合は、
    日時の早い枠を上位とする。取得期間の端では、ピークを含む7日間が
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
            daily（日別最大。kwは丸める前の値、display_kwはNo.1の表示値）、
            monthly（月別集計）、top（上位50枠）、
            week（ピークを含む最大7日間）、各区分の件数を格納する。
            対象月に実績がない場合はday・dailyが空、日別ピークはNone。

    """
    start, end, month = bounds(config["target_month"])

    df = df.sort_values("timestamp").copy()
    actual_start = df.timestamp.iloc[0].normalize()
    actual_end = df.timestamp.iloc[-1].normalize() + timedelta(days=1)
    # 日別欄は指定月を使う。別の月に置き換えず、実績がなければ空のデータとして扱う。
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
    # No.1でのみ使用する表示値。集計・順位・No.2の48枠は、丸め前のkwを使用する。
    daily["display_kw"] = daily.kw.map(calendar_power)
    # 実績のある月だけを年月順に並べる。存在しない月を0kWhとはみなさない。
    months = pd.period_range(actual_start, actual_end - timedelta(days=1), freq="M")
    monthly = (
        df.groupby(df.timestamp.dt.to_period("M"))["kw"]
        .agg(["sum", "max"])
        .reindex(months)
    )
    # 平均電力kW×0.5時間で各枠の電力量に戻す。
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
    # 日別表は十進数で合計し、15501.023000000001のような計算誤差が末尾の桁に現れることを防ぐ。
    # 表示用の桁数には丸めず、入力値の小数部を保ったkWhを求める。
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
    # seriesはグラフで使うDataFrameや件数の集計結果。用途を分けて描画処理へ渡す。
    context = {
        "customer": config,
        "target_month": month_str,
        "period": f"{actual_start:%Y年%m月}〜{actual_end - timedelta(days=1):%Y年%m月}",
        "actual_period": (
            f"{actual_start:%Y/%m/%d}〜{actual_end - timedelta(days=1):%Y/%m/%d}"
        ),
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
        "week_period": (
            f"{week_start:%Y年%m月%d日}〜{week_end - timedelta(days=1):%Y年%m月%d日}"
        ),
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
