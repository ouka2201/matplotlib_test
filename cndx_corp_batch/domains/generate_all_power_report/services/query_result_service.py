"""処理6・7・13：契約情報と30分値の取得結果を、帳票設定と需要電力に変換する。"""

import math
from collections.abc import Mapping

from .database_source import DATE, POINT, SLOTS, NumericConversionError, expand_daily_rows


def row_to_dict(row):
    """取得結果を辞書型へ変換する。

    Args:
        row (Mapping | sqlalchemy.Row): 列名を持つ取得行。

    Returns:
        dict: セッションやカーソルを含まない通常の辞書。
    """
    if isinstance(row, Mapping):
        return dict(row)
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return dict(mapping)


def _upper_row(row):
    """取得した列名を大文字に揃える。

    Args:
        row (Mapping | sqlalchemy.Row): 列名を持つ取得行。

    Returns:
        dict: 大文字の列名で参照できる取得行。
    """
    source = row_to_dict(row)
    normalized = {str(name).upper(): value for name, value in source.items()}
    return normalized


def prepare_query_results(
    customer_row,
    daily_rows,
    supply_point,
    report_month,
    *,
    customer_columns=None,
    date_column=DATE,
    slot_columns=None,
    quality_columns=(),
    config=None,
):
    """データ項目更新仕様説明書No.5・6の取得値を、帳票No.0～7の共通入力に変換する。

    Args:
        customer_row (Mapping | sqlalchemy.Row):お客さま情報。
        daily_rows (Iterable[Mapping]): 取得年月日と48枠を持つ全日分の行。値はkWh。
        supply_point (str): 供給地点特定番号。
        report_month (str): 指定月を含む直近12か月の最終月。YYYYMM形式。
        customer_columns (dict | None): 帳票項目からSQL取得列への対応。
            省略時はcustomer_name、address、customer_number、contract_kwを参照。
        date_column (str): SQLの取得年月日列。既定はT01_GET_YMD。
        slot_columns (Sequence[str] | None): 枠1〜48の順の取得列名。
            省略時はT01_30T_SYR01〜48。列の大小文字は区別しない。
        quality_columns (Sequence[str]): 取得済みの品質件数を持つ列。件数が0であることを検査する。
        config (dict | None): 注記・休日等の共通設定。契約値と対象年月で上書きする。

    Returns:
        tuple[pandas.DataFrame, dict]: timestamp・kwのデータと帳票設定。
    """
    fields = ("customer_name", "address", "customer_number", "contract_kw")
    columns = {field: field for field in fields}
    if customer_columns is not None:
        columns.update(customer_columns)
    customer = _upper_row(customer_row)
    values = {}
    for field, name in columns.items():
        values[field] = customer[name.upper()]

    # 処理13(2)／入力項目チェックNo.49：高圧契約電力を数値に変換する。単位はkWのまま扱う。
    try:
        contract = float(values["contract_kw"])
    except (ValueError, TypeError) as exc:
        # 契約電力テーブルの主キーは供給地点のみなので、DBに記録するメッセージには重複して記載しない。
        raise NumericConversionError("", columns["contract_kw"]) from exc
    if not math.isfinite(contract) or contract <= 0:
        raise ValueError("契約電力は正の有限数(kW)が必要です")
    values["contract_kw"] = contract

    slots = list(SLOTS if slot_columns is None else slot_columns)

    rows = []
    for source_row in daily_rows:
        row = _upper_row(source_row)

        normalized = {
            **row,
            POINT: row.get(POINT, supply_point),
            DATE: row[date_column.upper()],
        }
        normalized.update({dest: row[name.upper()] for dest, name in zip(SLOTS, slots)})
        rows.append(normalized)
    frame = expand_daily_rows(
        rows,
        report_month,
        supply_point,
        value_unit="kWh",
        quality_columns=quality_columns,
    )
    return frame, {**(config or {}), **values, "target_month": report_month}
