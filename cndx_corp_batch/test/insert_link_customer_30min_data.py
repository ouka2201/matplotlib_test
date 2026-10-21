"""顧客情報と30分値データ連携バッチ用のテストデータを登録する。"""

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, Numeric, String
from sqlalchemy import Table, create_engine, select


TABLE_NAMES = {
    "management": "t_30min_import_mng",
    "building": "m_building",
    "corporate": "m_corporate_basic",
    "customer": "t_arve_customer_info",
    "daily": "t_ep_electricity_data_30min",
    "linked": "t_electricity_data_30min",
}
SLOT_COLUMNS = [f"T01_30T_SYR{i:02d}" for i in range(1, 49)]


@dataclass(frozen=True)
class SeedOptions:
    """テストデータの件数、対象月、値、既存行の扱い。"""

    target_month: str
    count: int = 3
    start_id: int = 1
    point_prefix: str = "999900"
    days: int | None = None
    value: Decimal = Decimal("1.25")
    missing_count: int = 0
    invalid_count: int = 0
    on_existing: str = "error"
    dry_run: bool = False
    init_sqlite: bool = False

    def period(self) -> tuple[date, date]:
        """対象月の開始日と翌月初を返し、オプションを検証する。"""
        try:
            first = datetime.strptime(self.target_month, "%Y-%m").date().replace(day=1)
        except ValueError as exc:
            raise ValueError("target_monthはYYYY-MM形式で指定してください") from exc
        if self.count < 1 or self.start_id < 1:
            raise ValueError("countとstart_idは1以上で指定してください")
        if (
            not isinstance(self.point_prefix, str)
            or not self.point_prefix.isdigit()
            or not 1 <= len(self.point_prefix) <= 21
        ):
            raise ValueError("point_prefixは1〜21桁の数字で指定してください")
        last_id = self.start_id + self.count - 1
        if last_id >= 10 ** (22 - len(self.point_prefix)):
            raise ValueError("供給地点特定番号が22桁に収まりません")
        if self.days is not None and self.days < 1:
            raise ValueError("daysは1以上で指定してください")
        next_month = (
            date(first.year + 1, 1, 1)
            if first.month == 12
            else date(first.year, first.month + 1, 1)
        )
        month_days = (next_month - first).days
        if self.days is not None and self.days > month_days:
            raise ValueError("daysは対象月の日数以下で指定してください")
        if self.value < 0 or not self.value.is_finite():
            raise ValueError("valueは0以上の有限数で指定してください")
        if not 0 <= self.missing_count <= 99 or not 0 <= self.invalid_count <= 99:
            raise ValueError("missing_countとinvalid_countは0〜99で指定してください")
        if self.on_existing not in ("error", "skip"):
            raise ValueError("on_existingはerrorまたはskipを指定してください")
        # 月の日数を超えないよう、日数指定時は単純な日付加算を使う。
        end = first + timedelta(days=self.days or month_days)
        return first, end


def _table_name(settings: dict[str, Any], key: str) -> str:
    return settings.get(f"{key}_table", TABLE_NAMES[key])


def _schema(settings: dict[str, Any]) -> str | None:
    return settings.get("schema", "db_corp")


def _column_map(table: Table) -> dict[str, str]:
    return {column.name.upper(): column.name for column in table.c}


def _row(table: Table, values: dict[str, Any]) -> dict[str, Any]:
    columns = _column_map(table)
    return {
        columns[name.upper()]: value
        for name, value in values.items()
        if name.upper() in columns
    }


def _require_columns(table: Table, required: tuple[str, ...]) -> None:
    columns = _column_map(table)
    missing = [name for name in required if name.upper() not in columns]
    if missing:
        raise ValueError(f"{table.name}に必須列がありません: {', '.join(missing)}")


def _insert_or_skip(
    connection: Any,
    table: Table,
    values: dict[str, Any],
    keys: dict[str, Any],
    result: dict[str, int],
    options: SeedOptions,
) -> None:
    row = _row(table, values)
    key_row = _row(table, keys)
    key_columns = _column_map(table)
    condition = [
        table.c[key_columns[name.upper()]] == value
        for name, value in key_row.items()
    ]
    exists = connection.execute(
        select(next(iter(table.c))).where(*condition).limit(1)
    ).first() is not None
    if exists:
        if options.on_existing == "error":
            raise ValueError(f"{table.name}に既存キーがあります: {keys}")
        result["skipped"] += 1
        return
    if not options.dry_run:
        connection.execute(table.insert(), row)
    result["inserted"] += 1


def _points(options: SeedOptions) -> Iterator[tuple[int, str]]:
    for serial in range(options.start_id, options.start_id + options.count):
        point = options.point_prefix + str(serial).zfill(22 - len(options.point_prefix))
        yield serial, point


def _daily_rows(
    point: str,
    serial: int,
    start: date,
    end: date,
    options: SeedOptions,
    now: datetime,
) -> Iterator[dict[str, Any]]:
    current = start
    while current < end:
        row = {
            "T01_KYO_CTN_TOK_NO": point,
            "T01_GET_YMD": current.strftime("%Y%m%d"),
            "T01_KSKJ_KSU": str(options.missing_count),
            "T01_FSIJ_KSU": str(options.invalid_count),
            **_audit(now),
        }
        for index, column in enumerate(SLOT_COLUMNS, start=1):
            value = options.value + Decimal(serial) / 1000 + Decimal(index) / 10000
            row[column] = format(value, "f")
        yield row
        current = date.fromordinal(current.toordinal() + 1)


def _audit(now: datetime) -> dict[str, datetime | str]:
    return {
        "CREATED_BY": "customer_30min_test_seed",
        "CREATED_AT": now,
        "UPDATED_BY": "customer_30min_test_seed",
        "UPDATED_AT": now,
    }


def _source_values(
    serial: int, point: str, options: SeedOptions, now: datetime
) -> dict[str, dict[str, Any]]:
    corporate_number = f"TEST{serial:09d}"
    company_id = f"{serial:014d}"
    org_id = f"ORG{serial:017d}"
    building_id = f"{corporate_number}01"
    ep_customer_number = f"{serial:013d}"
    old_customer_number = f"001{serial:013d}"
    name = f"テスト事業所{serial:06d}"
    return {
        "management": {
            "SUPPLY_POINT_NUMBER": point,
            "TARGET_YEAR_MONTH": options.target_month.replace("-", ""),
            "CREATE_STATUS": "3",
            "ERROR_MESSAGE": None,
            "LINKED_ERROR_MESSAGE": None,
            "LINKED_DATE": None,
            **_audit(now),
        },
        "corporate": {
            "CORPORATE_NUMBER": corporate_number,
            "COMPANY_NAME": f"テスト企業{serial:06d}",
            "COMPANY_NAME_KANA": f"テストキギョウ{serial:06d}",
            "DELETE_FLG": False,
            **_audit(now),
        },
        "building": {
            "CORPORATE_NUMBER": corporate_number,
            "AGREEMENT_CATEGORY": "01",
            "ORG_ID": org_id,
            "BUILDING_ID": building_id,
            "LOCATION_IDENTIFIER_CODE": f"LOC{serial:010d}",
            "LOCATION_IDENTIFIER_NAME": name,
            "BUILDING_NAME": name,
            "EP_CUSTOMER_NUMBER": ep_customer_number,
            "SUPPLY_POINT_NUMBER": point,
            "DELETE_FLG": False,
            **_audit(now),
        },
        "customer": {
            "CMN_SupplyPointSpecificNum__c": point,
            "CMN_BusinessType__c": "2",
            "CMN_OldCustomerNum__c": old_customer_number,
            "CMN_PowerContract__c": "1000",
            "CMN_DemandLocationAddress__c": f"東京都テスト区{serial}番地（架空）",
            "CMN_DemandLocationFullName_Ref__c": name,
            "CMN_KigyoID_Fk__c": company_id,
            "RecordTypeId": "TEST_RECORD_TYPE",
            **_audit(now),
        },
    }


def _table_definitions(metadata: MetaData, settings: dict[str, Any]) -> None:
    schema = _schema(settings)
    if schema is not None:
        raise ValueError("init-sqliteはschema=nullで指定してください")
    management = Table(
        _table_name(settings, "management"),
        metadata,
        Column("SUPPLY_POINT_NUMBER", String(22), primary_key=True),
        Column("TARGET_YEAR_MONTH", String(6), primary_key=True),
        Column("CREATE_STATUS", String(1), nullable=False),
        Column("ERROR_MESSAGE", String(100)),
        Column("LINKED_ERROR_MESSAGE", String(100)),
        Column("LINKED_DATE", DateTime),
        Column("CREATED_BY", String(50)),
        Column("CREATED_AT", DateTime),
        Column("UPDATED_BY", String(50)),
        Column("UPDATED_AT", DateTime),
    )
    Table(
        _table_name(settings, "corporate"),
        metadata,
        Column("CORPORATE_NUMBER", String(13), primary_key=True),
        Column("COMPANY_NAME", String(100)),
        Column("COMPANY_NAME_KANA", String(100)),
        Column("DELETE_FLG", Boolean, nullable=False),
        Column("CREATED_BY", String(50)),
        Column("CREATED_AT", DateTime),
        Column("UPDATED_BY", String(50)),
        Column("UPDATED_AT", DateTime),
    )
    Table(
        _table_name(settings, "building"),
        metadata,
        Column("CORPORATE_NUMBER", String(13), primary_key=True),
        Column("AGREEMENT_CATEGORY", String(2), primary_key=True),
        Column("ORG_ID", String(20), primary_key=True),
        Column("BUILDING_ID", String(113), primary_key=True),
        Column("LOCATION_IDENTIFIER_CODE", String(100)),
        Column("LOCATION_IDENTIFIER_NAME", String(50)),
        Column("BUILDING_NAME", String(100)),
        Column("EP_CUSTOMER_NUMBER", String(13)),
        Column("SUPPLY_POINT_NUMBER", String(22)),
        Column("DELETE_FLG", Boolean, nullable=False),
        Column("CREATED_BY", String(50)),
        Column("CREATED_AT", DateTime),
        Column("UPDATED_BY", String(50)),
        Column("UPDATED_AT", DateTime),
    )
    Table(
        _table_name(settings, "customer"),
        metadata,
        Column("CMN_SupplyPointSpecificNum__c", String(22), primary_key=True),
        Column("CMN_BusinessType__c", String(4)),
        Column("CMN_OldCustomerNum__c", String(16)),
        Column("CMN_PowerContract__c", String(10)),
        Column("CMN_DemandLocationAddress__c", String(1300)),
        Column("CMN_DemandLocationFullName_Ref__c", String(1300)),
        Column("CMN_KigyoID_Fk__c", String(1300)),
        Column("RecordTypeId", String(20)),
        Column("CREATED_BY", String(50)),
        Column("CREATED_AT", DateTime),
        Column("UPDATED_BY", String(50)),
        Column("UPDATED_AT", DateTime),
    )
    Table(
        _table_name(settings, "daily"),
        metadata,
        Column("T01_KYO_CTN_TOK_NO", String(22), primary_key=True),
        Column("T01_GET_YMD", String(8), primary_key=True),
        Column("T01_KSKJ_KSU", String(2), nullable=False),
        Column("T01_FSIJ_KSU", String(2), nullable=False),
        *[Column(name, String(9), nullable=False) for name in SLOT_COLUMNS],
        Column("CREATED_BY", String(50), nullable=False),
        Column("CREATED_AT", DateTime, nullable=False),
        Column("UPDATED_BY", String(50)),
        Column("UPDATED_AT", DateTime),
    )
    Table(
        _table_name(settings, "linked"),
        metadata,
        Column("CORP_NUMBER", String(13), primary_key=True),
        Column("AGREEMENT_CATEGORY", String(2), primary_key=True),
        Column("ORG_ID", String(20), primary_key=True),
        Column("BUILDING_ID", String(113), primary_key=True),
        Column("ACQUISITION_DATE", String(8), primary_key=True),
        Column("SUPPLY_POINT_NUMBER", String(22), primary_key=True),
        Column("CORP_NAME", String(100)),
        Column("BUILDING_NAME", String(100)),
        Column("EP_CUSTOMER_NUMBER", String(16)),
        Column("COMPANY_ID", String(14)),
        Column("MISSING_TIME_RANGE_COUNT", Integer),
        Column("INVALID_TIME_RANGE_COUNT", Integer),
        *[Column(f"V30MIN_USED_ENERGY_{i}", Numeric) for i in range(1, 49)],
        Column("DELETE_FLG", Boolean),
        Column("CREATED_BY", String(50)),
        Column("CREATED_AT", DateTime),
        Column("UPDATED_BY", String(50)),
        Column("UPDATED_AT", DateTime),
        Column("FILE_UPDATE_DATE", DateTime),
        Column("ARVE_CORP_NAME", String(1300)),
        Column("ARVE_CUSTOMER_NUMBER", String(16)),
        Column("ARVE_OFFICE_CODE", String(3)),
    )


def init_sqlite_tables(engine: Any, settings: dict[str, Any]) -> None:
    """SQLiteに連携元・連携先の最小テーブルを作る。"""
    metadata = MetaData()
    _table_definitions(metadata, settings)
    metadata.create_all(engine)


def _reflect_tables(connection: Any, settings: dict[str, Any]) -> dict[str, Table]:
    metadata = MetaData()
    schema = _schema(settings)
    return {
        key: Table(
            _table_name(settings, key),
            metadata,
            schema=schema,
            autoload_with=connection,
        )
        for key in TABLE_NAMES
    }


def seed_database(settings: dict[str, Any], options: SeedOptions) -> dict[str, Any]:
    """連携バッチが読む元データを1トランザクションで登録する。"""
    start, end = options.period()
    url = settings.get("url") or os.getenv(settings.get("url_env", "DATABASE_URL"))
    if not url:
        raise RuntimeError("DB接続先が設定されていません。urlまたはurl_envを指定してください")
    engine = create_engine(url)
    try:
        if options.init_sqlite:
            init_sqlite_tables(engine, settings)
        result = {
            "target_month": options.target_month,
            "count": options.count,
            "start": start.isoformat(),
            "end": (end - timedelta(days=1)).isoformat(),
            "tables": {
                key: {"inserted": 0, "skipped": 0}
                for key in TABLE_NAMES
                if key != "linked"
            },
        }
        with engine.begin() as connection:
            tables = _reflect_tables(connection, settings)
            _require_columns(
                tables["management"],
                ("SUPPLY_POINT_NUMBER", "TARGET_YEAR_MONTH", "CREATE_STATUS"),
            )
            _require_columns(
                tables["building"],
                ("CORPORATE_NUMBER", "AGREEMENT_CATEGORY", "ORG_ID", "BUILDING_ID"),
            )
            _require_columns(tables["corporate"], ("CORPORATE_NUMBER", "COMPANY_NAME"))
            _require_columns(tables["customer"], ("CMN_SupplyPointSpecificNum__c",))
            _require_columns(
                tables["daily"],
                (
                    "T01_KYO_CTN_TOK_NO",
                    "T01_GET_YMD",
                    *SLOT_COLUMNS,
                    "CREATED_BY",
                    "CREATED_AT",
                ),
            )
            now = datetime.now()
            for serial, point in _points(options):
                values = _source_values(serial, point, options, now)
                _insert_or_skip(
                    connection,
                    tables["corporate"],
                    values["corporate"],
                    {"CORPORATE_NUMBER": values["corporate"]["CORPORATE_NUMBER"]},
                    result["tables"]["corporate"],
                    options,
                )
                building_keys = {
                    key: values["building"][key]
                    for key in (
                        "CORPORATE_NUMBER",
                        "AGREEMENT_CATEGORY",
                        "ORG_ID",
                        "BUILDING_ID",
                    )
                }
                _insert_or_skip(
                    connection,
                    tables["building"],
                    values["building"],
                    building_keys,
                    result["tables"]["building"],
                    options,
                )
                _insert_or_skip(
                    connection,
                    tables["customer"],
                    values["customer"],
                    {"CMN_SupplyPointSpecificNum__c": point},
                    result["tables"]["customer"],
                    options,
                )
                for row in _daily_rows(point, serial, start, end, options, now):
                    _insert_or_skip(
                        connection,
                        tables["daily"],
                        row,
                        {
                            "T01_KYO_CTN_TOK_NO": point,
                            "T01_GET_YMD": row["T01_GET_YMD"],
                        },
                        result["tables"]["daily"],
                        options,
                    )
                _insert_or_skip(
                    connection,
                    tables["management"],
                    values["management"],
                    {
                        "SUPPLY_POINT_NUMBER": point,
                        "TARGET_YEAR_MONTH": values["management"]["TARGET_YEAR_MONTH"],
                    },
                    result["tables"]["management"],
                    options,
                )
        return result
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="顧客情報と30分値データ連携バッチのテストデータを登録します。"
    )
    parser.add_argument("--db-config", type=Path, required=True, help="DB設定JSONのパス")
    parser.add_argument("--target-month", required=True, help="対象年月（YYYY-MM）")
    parser.add_argument("--count", type=int, default=3, help="供給地点数")
    parser.add_argument("--start-id", type=int, default=1, help="テスト番号の開始値")
    parser.add_argument("--point-prefix", default="999900", help="供給地点番号の先頭")
    parser.add_argument("--days", type=int, help="対象月の先頭から生成する日数")
    parser.add_argument(
        "--value", type=Decimal, default=Decimal("1.25"), help="30分値の基準値"
    )
    parser.add_argument("--missing-count", type=int, default=0, help="欠測件数")
    parser.add_argument("--invalid-count", type=int, default=0, help="不正値件数")
    parser.add_argument(
        "--on-existing", choices=("error", "skip"), default="error", help="既存キーの扱い"
    )
    parser.add_argument("--dry-run", action="store_true", help="登録せず件数だけ確認")
    parser.add_argument("--init-sqlite", action="store_true", help="SQLiteの最小テーブルを作成")
    args = vars(parser.parse_args(argv))
    config_path = args.pop("db_config")
    settings = json.loads(config_path.read_text(encoding="utf-8"))
    result = seed_database(settings, SeedOptions(**args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
