# バッチ共通の日付計算。電力見える化レポートの対象年月は【補足】バッチ年月仕様を参照。
from datetime import date, datetime, time, timedelta

import pytz
from dateutil.relativedelta import relativedelta

JST = pytz.timezone("Asia/Tokyo")


def today():
    return date.today()


def yesterday():
    return today() - timedelta(days=1)


def month_start(d: date):
    return d.replace(day=1)


def month_end(d: date):
    return d + relativedelta(months=1, day=1) - relativedelta(days=1)


def check_batch_ym(d: date, batch_days: int = 0):
    """バッチ実行年月日判定

    Args:
        d (date): システム日時
        batch_days (int, optional): 対象月を切り替える日。電力見える化の既定設定は15日。

    Returns:
        bool: 実行日が切替日より前ならTrue。切替日当日以降はFalse。
    """
    return d.day < batch_days


def calc_offset_month(
    d: date, batch_days: int = 0, prev_month: int = 0, after_month: int = 0
):
    """データ項目更新仕様説明書No.2：実行日の区分に応じてレポート作成対象年月を求める

    Args:
        d (date): システム日時
        batch_days (int, optional): 対象月を切り替える日. Defaults to 0.
        prev_month (int, optional): 切替日前のOFFSET値. Defaults to 0.
        after_month (int, optional): 切替日以降のOFFSET値. Defaults to 0.

    Returns:
        date: 指定月分ずらした年月
    """
    if check_batch_ym(d, batch_days):
        return d - relativedelta(months=prev_month)
    else:
        return d - relativedelta(months=after_month)


def get_current_time():
    """システム日時取得

    Returns:
        datetime: システム日時
    """
    return datetime.now(JST)


def is_batch_executable(
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
) -> bool:
    """API実行可能時間判定

    Args:
        start_hour (int): 実行可能開始時
        start_minute (int): 実行可能開始分
        end_hour (int): 実行可能終了時
        end_minute (int): 実行可能終了分

    Returns:
        bool: 実行可能
    """

    current_time = get_current_time().time()
    start_range = time(start_hour, start_minute)
    end_range = time(end_hour, end_minute)
    return current_time >= start_range or current_time <= end_range
