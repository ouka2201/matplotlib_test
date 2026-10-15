"""処理7／データ項目更新仕様説明書No.6：EPデータ参照基盤30分値を帳票用に変換する。"""

import numpy as np
import pandas as pd

from .data_service import bounds, validate_data

# DBの物理列名をここに集約する。
# 供給地点特定番号はお客さま番号とは別項目で、先頭の0を保持する。
POINT = "T01_KYO_CTN_TOK_NO"
DATE = "T01_GET_YMD"
# 01〜48を数値順に並べる。この列順と時刻の順番を対応させる。
SLOTS = [f"T01_30T_SYR{i:02d}" for i in range(1, 49)]
CONTRACT_POINT = "QSQB_DCIS2_SPL_PT_SPC_NO"
CONTRACT_POWER = "QSQB_DCIS2_HVPW_CTRT"


class NumericConversionError(ValueError):
    """入力項目チェックNo.1～49の数値変換不可。処理22・23の更新文言とログに使う。"""

    def __init__(self, primary_key, column):
        self.primary_key = str(primary_key)
        self.column = column
        super().__init__(f"数値変換エラー：{self.primary_key}")


def expand_daily_rows(
    rows, report_month, supply_point, value_unit="kWh", quality_columns=()
):
    """処理7(2)・(3)：V30分_使用_電力量_1～48を数値・時刻へ変換する。

    1→00:00、2→00:30、48→23:30。既定の保存値はkWhなので2倍して30分平均電力kWに変換する。
    月間電力量は平均電力×0.5時間を合計するため、元のkWh合計と一致する。

    Args:
        rows (Iterable[Mapping]): 日別レコード。物理列名は大文字・小文字どちらでもよい。
        report_month (str): レポート作成対象年月。YYYYMM形式。指定月を含む12か月を対象とする。
        supply_point (str): 供給地点特定番号。先頭の0を保持する。
        value_unit (str): 保存値の単位。kW、kWh、Whのいずれか。
        quality_columns (Iterable[str]): 0件を要求する欠測・不正値件数列。指定時だけ検査する。

    Returns:
        pandas.DataFrame: 直近12か月内で実績のある期間のtimestamp・kw列。
            各取得行の48列を展開する。実績が1年未満の場合も取得した期間を返す。

    Raises:
        NumericConversionError: 48枠に数値変換できない値がある場合。
        ValueError: 取得年月日・単位・任意指定の品質件数が不正な場合。
        KeyError: 取得年月日または48枠の列が不足している場合。
    """
    # 保存値はkWh。30分=0.5時間なので、平均電力kWはkWh÷0.5で求める。
    # kW・Whは別の入力データ源を扱う場合の換算方法。今回の既定値はkWh。
    factors = {"kW": 1.0, "kWh": 2.0, "Wh": 0.002}
    if value_unit not in factors:
        raise ValueError("value_unitはkW、kWh、Whのいずれかです")
    # DBドライバーによる列名の大小文字の違いを吸収する。
    # 欠けている枠列を0で補わず、48列すべての存在を確認する。
    records = pd.DataFrame(
        [{str(k).upper(): v for k, v in row.items()} for row in rows]
    )

    # 日付列はVARCHARのYYYYMMDD。8桁の形式と実在する日付の両方を検査する。
    date_strings = records[DATE].astype("string")
    dates = pd.to_datetime(date_strings, format="%Y%m%d", errors="raise")
    start, end, _ = bounds(report_month)
    # 指定月を含む12か月へ絞る。終了は翌月1日で、この日付自体は含めない。
    selected = (dates >= start) & (dates < end)
    records = records.loc[selected].copy()
    dates = dates.loc[selected]

    # 欠測・不正値の件数があれば、値が0に見えても正常なデータとして集計しない。
    for column in quality_columns:
        counts = pd.to_numeric(records[column.upper()], errors="raise")
        if counts.isna().any() or not (counts == 0).all():
            raise ValueError(f"数値変換エラー： {column}")
    # 日別の横持ち48列を数値にする。空欄や数値以外はエラーとして扱う。
    try:
        values = records[SLOTS].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    except (ValueError, TypeError):
        # 正常時は一括変換し、失敗した場合だけ原因の行・列を特定する。
        for row in records.to_dict("records"):
            for column in SLOTS:
                try:
                    pd.to_numeric(row[column], errors="raise")
                except (ValueError, TypeError) as exc:
                    raise NumericConversionError(row[DATE], column) from exc
        raise
    # 日付×48枠の行列を作り、行ごとに00:00〜23:30を並べる。
    # 0〜47に30分を掛けるので、枠1は0分、枠48は1410分になる。
    timestamps = (
        dates.to_numpy()[:, None] + np.arange(48)[None, :] * np.timedelta64(30, "m")
    ).reshape(-1)
    # 日時と電力を同じ行順で平坦化する。日付や枠の対応がずれないようにする。
    # 実装補足：共通処理で型変換・期間抽出・日時順ソートを行う。欠損日・重複・負数の検査は行わない。
    frame = pd.DataFrame(
        {"timestamp": timestamps, "kw": values.reshape(-1) * factors[value_unit]}
    )
    return validate_data(frame, report_month)
