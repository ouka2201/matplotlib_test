"""既存SQLの取得結果を、PDF用の設定と30分平均電力へ変換する。"""

from collections.abc import Mapping
import math

from services.database_source import DATE, POINT, SLOTS, expand_daily_rows


def row_to_dict(row):
    """辞書・RowMapping・SQLAlchemy Rowを通常の辞書へ変換する。

    Args:
        row (Mapping | sqlalchemy.Row): 列名を持つ取得行。

    Returns:
        dict: セッションやカーソルを含まない通常の辞書。

    Raises:
        TypeError: 列名のないタプル等が渡された場合。
    """
    if isinstance(row, Mapping):
        return dict(row)
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return dict(mapping)
    raise TypeError(
        "取得行は辞書かSQLAlchemy Rowで渡してください。mappings().all()を使用できます"
    )


def _upper_row(row):
    """取得列名を大文字へ揃え、曖昧な列名はエラーにする。

    Args:
        row (Mapping | sqlalchemy.Row): 列名を持つ取得行。

    Returns:
        dict: 大文字の列名で参照できる取得行。
    """
    source = row_to_dict(row)
    normalized = {str(name).upper(): value for name, value in source.items()}
    if len(normalized) != len(source):
        raise ValueError(
            "大小文字だけが異なる取得列があります。SQLのASで一意にしてください"
        )
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
    """取得済みの契約情報1行と日別48枠を、DBへ再接続せずに変換する。

    Args:
        customer_row (Mapping | sqlalchemy.Row): 名義・住所・お客さま番号・契約電力の1行。
        daily_rows (Iterable[Mapping]): 取得年月日と48枠を持つ全日分の行。値はkWh。
        supply_point (str): 検索した供給地点。先頭ゼロを保った文字列。
        report_month (str): 指定月を含む直近12か月の最終月。YYYY-MM形式。
        customer_columns (dict | None): 帳票項目からSQL取得列への対応。
            省略時はcustomer_name、address、customer_number、contract_kwを参照。
        date_column (str): SQLの取得年月日列。既定はT01_GET_YMD。
        slot_columns (Sequence[str] | None): 枠1〜48の順の取得列名。
            省略時はT01_30T_SYR01〜48。列の大小文字は区別しない。
        quality_columns (Sequence[str]): 0件を要求する取得済み品質件数列。
        config (dict | None): 注記・休日等の共通設定。契約値と対象年月で上書きする。

    Returns:
        tuple[pandas.DataFrame, dict]: timestamp・kwのデータと帳票設定。

    Raises:
        ValueError: 契約情報の不足、48列の不足、実績の不正・欠測がある場合。
        TypeError: 列名のない取得行が渡された場合。
    """
    # 取得順には依存しない。ASで決めた列名、または明示的な対応表で参照する。
    fields = ("customer_name", "address", "customer_number", "contract_kw")
    columns = {field: field for field in fields}
    if customer_columns is not None:
        if not isinstance(customer_columns, dict) or set(customer_columns) - set(
            fields
        ):
            raise ValueError(
                "customer_columnsには名義・住所・番号・契約電力の対応を指定してください"
            )
        columns.update(customer_columns)
    customer = _upper_row(customer_row)
    values = {}
    for field, name in columns.items():
        if not isinstance(name, str) or name.upper() not in customer:
            raise ValueError(f"契約情報の取得列がありません: {field} -> {name}")
        values[field] = customer[name.upper()]
    for field in fields[:3]:
        if not isinstance(values[field], str) or not values[field].strip():
            raise ValueError(f"契約情報の{field}は空欄でない文字列が必要です")
    # 契約電力はkW。日別48枠のkWhだけを2倍し、契約電力を2倍しない。
    contract = float(values["contract_kw"])
    if not math.isfinite(contract) or contract <= 0:
        raise ValueError("契約電力は正の有限数(kW)が必要です")
    values["contract_kw"] = contract

    slots = list(SLOTS if slot_columns is None else slot_columns)
    if (
        len(slots) != 48
        or any(not isinstance(name, str) or not name for name in slots)
        or len({name.upper() for name in slots}) != 48
    ):
        raise ValueError(
            "slot_columnsには枠1〜48の一意な48列を時刻順に指定してください"
        )
    if not isinstance(date_column, str) or not date_column:
        raise ValueError("date_columnには取得年月日の列名を指定してください")
    rows = []
    for source_row in daily_rows:
        row = _upper_row(source_row)
        required = [date_column.upper(), *[name.upper() for name in slots]]
        missing = [name for name in required if name not in row]
        if missing:
            raise ValueError(f"30分値の取得列がありません: {missing}")
        # 提示のSQLは日付+48枠だけでもよい。検索済みの供給地点を補う。
        # 供給地点列がある場合はその値を維持し、既存の検証で混入を検出する。
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
