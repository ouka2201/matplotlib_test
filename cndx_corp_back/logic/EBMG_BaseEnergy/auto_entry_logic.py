import os
import traceback
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
from flask import abort, current_app
from sqlalchemy import func, select

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.dto.EBMG.energy_auto_entry_in_dto import (
    EnergyAutoEntryIn,
)
from cndx_corp_back.entity.t_electricity_data_30min_entity import TElectricityData30min


@component
def monthly_sums(
    indto: EnergyAutoEntryIn, count: int = 12, logger=None
) -> tuple[list[dict], bool]:
    """
    月ごと合計を取得し、いずれか月が整数15桁小数点10桁を超えるか、
    年度合計が同範囲を超える場合は全月まとめて sum÷1000
    最終的に小数第10位まで四捨五入
    """
    monthly = []
    # 上限＝整数部15桁すべて9、小数部10桁すべて9　'999999999999999.9999999999'
    limits = Decimal("9" * 15)
    decimal_limits = limits + Decimal("0." + "9" * 10)
    # 小数第10位までの量子化値　'0.0000000001'
    q10 = Decimal("0." + "0" * 9 + "1")

    # 各月の合計を計算（Decimal保持）
    for ym in yyyymm_list(indto.start_year_month, count):
        daily = daily_sums_for_ym(indto, ym)
        total = sum(Decimal(str(item["sum"])) for item in daily)
        monthly.append({"year_month": ym, "sum": total})

    # どれかの日合計(月)が桁数超過 or 年度合計が桁数超過かチェック
    monthly_total = sum(m["sum"] for m in monthly)
    needs_scaling = (
        any(m["sum"] > decimal_limits for m in monthly)
        or monthly_total > decimal_limits
    )

    # スケーリング ＆ 小数第10位まで四捨五入
    if needs_scaling:
        for m in monthly:
            scaled = (m["sum"] / Decimal("1000")).quantize(q10, rounding=ROUND_HALF_UP)
            m["sum"] = float(scaled)
        flag = True
    else:
        for m in monthly:
            rounded = m["sum"].quantize(q10, rounding=ROUND_HALF_UP)
            m["sum"] = float(rounded)
        flag = False
    return monthly, flag


# 日次合計取得関数
def daily_sums_for_ym(indto: EnergyAutoEntryIn, year_month: str):
    start_dt, end_dt = get_month_range(year_month)
    start_str = start_dt.strftime("%Y%m%d")
    end_str = end_dt.strftime("%Y%m%d")

    with get_scoped_session() as session:
        # 年月部分を抜き出してラベル付け
        year_month_col = func.substr(
            TElectricityData30min.acquisition_date, 1, 8
        ).label("year_month")
        # 48本の energy カラムをループで合計してラベル付け
        sum_expr = sum(
            func.sum(getattr(TElectricityData30min, f"v30min_used_energy_{i}"))
            for i in range(1, 49)
        ).label("sum")
        # SQLステートメントを組み立て
        sql = (
            select(year_month_col, sum_expr)
            .where(
                TElectricityData30min.corp_number == indto.corporate_number,
                TElectricityData30min.agreement_category == indto.agreement_category,
                TElectricityData30min.supply_point_number == indto.supply_point_number,
                TElectricityData30min.acquisition_date.between(start_str, end_str),
            )
            .group_by(year_month_col)
            .order_by(year_month_col)
        )
        df = pd.read_sql(sql, session.connection())

    # 月内全日付リスト生成
    all_days = (
        pd.date_range(start=start_dt, end=end_dt, freq="D").strftime("%Y%m%d").tolist()
    )
    # 0埋め＋整形 JSON リスト
    recs = {row["year_month"]: float(row["sum"]) for row in df.to_dict("records")}
    return [{"year_month": d, "sum": recs.get(d, 0.0)} for d in all_days]


# 月初／月末取得
def get_month_range(year_month: str):
    p = pd.Period(year_month, freq="M")
    return p.start_time.date(), p.end_time.date()


# YYYYMMリスト生成
def yyyymm_list(start_yyyymm: str, count: int = 12) -> list[str]:
    year = int(start_yyyymm[:4])
    month = int(start_yyyymm[4:6])
    out = []
    for i in range(count):
        y = year + (month - 1 + i) // 12
        m = (month - 1 + i) % 12 + 1
        out.append(f"{y}{m:02d}")
    return out
