"""30分値取込管理・ARVE・契約電力・日別48枠へ架空データをINSERTする。

レポート管理は取込完了後の別処理で作成するため、このスクリプトでは
作成・登録しない。4テーブルへ同じ22桁の供給地点特定番号を使用する。
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
import math
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    select,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.data_service import bounds
from services.database_source import (
    DatabaseSource,
    POINT,
    DATE,
    SLOTS,
    CONTRACT_POINT,
    CONTRACT_POWER,
)
from services.report_job_source import (
    CUSTOMER_POINT,
    CUSTOMER_COLUMNS,
    customer_column_mapping,
)

TABLE_NAMES = {
    "import_management": "t_30min_import_mng",
    "customer": "t_arve_customer_info",
    "contract": "t_ep_contracted_power",
    "daily": "t_ep_electricity_data_30min",
}

# レポート管理と同名の列を持つが、投入先・状態の意味は別のテーブル。
IMPORT_POINT = "SUPPLY_POINT_NUMBER"
IMPORT_MONTH = "TARGET_YEAR_MONTH"
IMPORT_STATUS = "CREATE_STATUS"
SEED_CUSTOMER_COLUMNS = {
    "company_id": "CMN_KigyoID_Fk__c",
    "record_type_id": "RecordTypeId",
}


@dataclass(frozen=True)
class SeedOptions:
    """テストデータの件数・期間・値と、再実行時の扱い。

    Attributes:
        report_month (str): 最終対象月。YYYY-MM。
        count (int): 作成する供給地点の数。
        months (int): 対象月を含む実績月数。1〜12。
        days (int | None): 指定時は月数の代わりに月末までの日数を使う。
        start_id (int): テスト番号の開始値。同じ値は同じ供給地点になる。
        point_prefix (str): 22桁の供給地点の先頭につける数字。
        max_kw (float): 架空の30分平均電力の最大値。
        contract_kw (float): EP契約電力テーブルへ登録する値。
        seed (int): 乱数シード。供給地点・期間が同じなら同じ実績になる。
        syousapo (str): ARVEのレコードタイプを交互・加入・未加入で生成する指定。
        on_existing (str): errorなら既存キーで中止、skipなら既存行を保持。
        chunk_size (int): 日別実績をまとめてINSERTする上限行数。
        dry_run (bool): Trueなら検証と件数計算だけ行い、INSERTしない。
        init_sqlite (bool): TrueならSQLite専用の最小検証テーブルを作る。
    """

    report_month: str
    count: int = 10
    months: int = 12
    days: int | None = None
    start_id: int = 1
    point_prefix: str = "999900"
    max_kw: float = 1200
    contract_kw: float = 1600
    seed: int = 42
    syousapo: str = "alternate"
    on_existing: str = "error"
    chunk_size: int = 200
    dry_run: bool = False
    init_sqlite: bool = False

    def period(self):
        """設定を検証し、実績の開始日と終了日の翌日を返す。

        Returns:
            tuple[pandas.Timestamp, pandas.Timestamp]: 日付境界の半開区間。

        Raises:
            ValueError: 件数・年月・期間・識別番号・電力等が不正な場合。
        """
        year_start, end, _ = bounds(self.report_month)
        for name in ("count", "months", "start_id", "chunk_size"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name}は正の整数で指定してください")
        if self.months > 12:
            raise ValueError("monthsは1〜12で指定してください")
        if not isinstance(self.point_prefix, str) or not re.fullmatch(
            r"[0-9]{1,21}", self.point_prefix
        ):
            raise ValueError("point_prefixは1〜21桁の数字で指定してください")
        last_id = self.start_id + self.count - 1
        if last_id >= 10 ** (22 - len(self.point_prefix)) or last_id >= 10**10:
            raise ValueError("テスト番号が供給地点または14文字の企業IDに収まりません")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seedは0以上の整数で指定してください")
        if any(
            not math.isfinite(value) or value <= 0
            for value in (self.max_kw, self.contract_kw)
        ):
            raise ValueError("max_kw・contract_kwは正の有限数で指定してください")
        if self.max_kw < 0.001:
            raise ValueError("max_kwは0.001以上で指定してください")
        if self.syousapo not in ("alternate", "joined", "not-joined"):
            raise ValueError("syousapoの指定が不正です")
        if self.on_existing not in ("error", "skip"):
            raise ValueError("on_existingはerrorまたはskipを指定してください")
        if self.dry_run and self.init_sqlite:
            raise ValueError("dry-runとinit-sqliteは同時に指定できません")
        if self.days is not None:
            if (
                type(self.days) is not int
                or not 1 <= self.days <= (end - year_start).days
            ):
                raise ValueError("daysは直近12か月内に収まる正の日数で指定してください")
            start = end - pd.Timedelta(days=self.days)
        else:
            start = end - pd.DateOffset(months=self.months)
        return start, end


def init_sqlite_tables(engine, settings):
    """SQLiteに、テストデータ投入用の最小4テーブルを作る。

    既存テーブルは変更・削除しない。本番DBのDDLを再現するものではない。
    ARVEの名義列が未指定なら、検証用の仮列名を使用する。

    Args:
        engine (sqlalchemy.Engine): SQLiteの接続先。
        settings (dict): schema=null、テーブル名、customer_columns等。

    Raises:
        ValueError: SQLite以外、またはスキーマを指定している場合。
    """
    if engine.dialect.name != "sqlite" or settings.get("schema", "db_corp") is not None:
        raise ValueError("init-sqliteはSQLiteかつschema=nullの場合だけ使用できます")
    metadata = MetaData()
    Table(
        settings.get("import_management_table", TABLE_NAMES["import_management"]),
        metadata,
        Column(IMPORT_POINT, String(22), primary_key=True),
        Column(IMPORT_MONTH, String(6), primary_key=True),
        Column(IMPORT_STATUS, String(1), nullable=False),
        Column("ERROR_MESSAGE", String(100)),
        Column("LINKED_ERROR_MESSAGE", String(100)),
        Column("LINKED_DATE", DateTime),
        Column("CREATED_BY", String(50), nullable=False),
        Column("CREATED_AT", DateTime, nullable=False),
        Column("UPDATED_BY", String(50)),
        Column("UPDATED_AT", DateTime),
    )
    mapping = {
        **CUSTOMER_COLUMNS,
        **SEED_CUSTOMER_COLUMNS,
        "customer_name": "CMN_DemandLocationFullName_Test__c",
        **settings.get("customer_columns", {}),
    }
    point = settings.get("customer_point_column", CUSTOMER_POINT)
    names = {
        point: String(22),
        "CMN_BusinessType__c": String(4),
        mapping["customer_name"]: String(130),
        mapping["address"]: String(130),
        mapping["customer_number"]: String(16),
        mapping["company_id"]: String(1300),
        mapping["record_type_id"]: String(20),
        "CMN_PowerContract__c": String(10),
        "CREATED_BY": String(50),
        "CREATED_AT": DateTime,
        "UPDATED_BY": String(50),
        "UPDATED_AT": DateTime,
    }
    for name, value in settings.get("customer_filters", {}).items():
        if not any(existing.upper() == name.upper() for existing in names):
            names[name] = Boolean if isinstance(value, bool) else String(130)
    Table(
        settings.get("customer_table", TABLE_NAMES["customer"]),
        metadata,
        *[
            Column(
                name,
                typ,
                primary_key=name in (point, "CMN_BusinessType__c"),
                nullable=name
                not in (point, "CMN_BusinessType__c", "CREATED_BY", "CREATED_AT"),
            )
            for name, typ in names.items()
        ],
    )
    Table(
        settings.get("contract_table", TABLE_NAMES["contract"]),
        metadata,
        Column(CONTRACT_POINT, String(22), primary_key=True),
        Column(CONTRACT_POWER, String(10), nullable=False),
    )
    Table(
        settings.get("daily_table", TABLE_NAMES["daily"]),
        metadata,
        Column(POINT, String(22), primary_key=True),
        Column(DATE, String(8), primary_key=True),
        *[Column(name, String(12), nullable=False) for name in SLOTS],
        *[
            Column(name, Integer, nullable=False)
            for name in settings.get("quality_columns", [])
        ],
    )
    metadata.create_all(engine)


def prepare_row(table, values):
    """実列の型・長さ・必須列を検証し、INSERT用の1行へ変換する。

    Args:
        table (sqlalchemy.Table): 反映済みテーブル。
        values (dict): 大小文字を問わない物理列名と登録値。

    Returns:
        dict: 実テーブルの列名・型に合わせた登録値。

    Raises:
        ValueError: 存在しない列、文字数超過、型不整合、未指定の必須列がある場合。
    """
    row = {}
    for name, value in values.items():
        column = DatabaseSource._column(table, name)
        try:
            typ = column.type.python_type
        except (NotImplementedError, AttributeError):
            typ = None
        if value is not None:
            if typ is str:
                value = str(value)
                limit = getattr(column.type, "length", None)
                if limit and len(value) > limit:
                    raise ValueError(
                        f"{table.name}.{column.name}が{limit}文字を超えています"
                    )
            elif typ in (float, Decimal):
                value = typ(str(value))
            elif typ is int:
                number = Decimal(str(value))
                if number != number.to_integral_value():
                    raise ValueError(f"{table.name}.{column.name}には整数が必要です")
                value = int(number)
            elif typ is bool and not isinstance(value, bool):
                if str(value).lower() not in ("true", "false", "1", "0"):
                    raise ValueError(f"{table.name}.{column.name}には真偽値が必要です")
                value = str(value).lower() in ("true", "1")
            elif typ is datetime and not isinstance(value, datetime):
                value = datetime.fromisoformat(str(value))
        if value is None and not column.nullable:
            raise ValueError(f"{table.name}.{column.name}はNULLにできません")
        row[column.name] = value
    for column in table.c:
        automatic_id = column is table.autoincrement_column
        if (
            column.name not in row
            and not column.nullable
            and column.default is None
            and column.server_default is None
            and not automatic_id
        ):
            raise ValueError(
                f"{table.name}.{column.name}が必須です。seed_defaultsに登録値を指定してください"
            )
    return row


def make_daily_rows(point, serial, start, end, options, settings):
    """供給地点1件分の架空の48枠を、日別のINSERT行として順に返す。

    Args:
        point (str): 供給地点の22桁文字列。
        serial (int): 供給地点ごとの乱数シードに使う番号。
        start (pandas.Timestamp): 実績開始日。
        end (pandas.Timestamp): 実績終了日の翌日。
        options (SeedOptions): 最大平均電力、乱数シード。
        settings (dict): 保存値の単位と品質列。

    Yields:
        dict: 日付・48枠・品質件数0を持つ日別データ。

    Raises:
        ValueError: 保存単位の指定が不正な場合。
    """
    unit = settings.get("value_unit", "kWh")
    factors = {"kWh": Decimal("0.5"), "kW": Decimal("1"), "Wh": Decimal("500")}
    if unit not in factors:
        raise ValueError("value_unitはkWh・kW・Whのいずれかです")
    dates = pd.date_range(start, end, freq="D", inclusive="left")
    hours = np.arange(48) / 2
    rng = np.random.default_rng(options.seed + serial)
    peak_day = len(dates) // 2
    for index, date in enumerate(dates):
        profile = 0.2 + 0.7 * np.exp(-(((hours - 17) / 5) ** 2))
        seasonal = 0.85 + 0.10 * math.cos((date.month - 8) / 12 * 2 * math.pi)
        weekly = 0.6 if date.dayofweek >= 5 else 1.0
        kw = np.round(
            options.max_kw
            * np.clip(
                profile * seasonal * weekly + rng.normal(0, 0.01, 48), 0.02, 0.98
            ),
            3,
        )
        if index == peak_day:
            kw[34] = options.max_kw  # 17:00の1枠を設定した最大値にする。
        row = {POINT: point, DATE: date.strftime("%Y%m%d")}
        for slot, value in zip(SLOTS, kw):
            row[slot] = format(Decimal(str(value)) * factors[unit], "f")
        row.update({name: 0 for name in settings.get("quality_columns", [])})
        yield row


def seed_database(settings, options):
    """4テーブルへ整合した架空データを1トランザクションで登録する。

    一度に保持する実績は供給地点1件のINSERTチャンクだけ。skip指定では
    既存行を変更せず、存在しないキーだけINSERTする。例外は全INSERTを
    ロールバックする。init-sqliteで作成したテーブル自体は残る。

    Args:
        settings (dict): 通常のDB設定、取込管理のテーブル名、
            seed_record_type_ids、追加必須列のseed_defaults。
        options (SeedOptions): 登録する件数・期間・値・既存行の扱い。

    Returns:
        dict: 対象期間、件数、各テーブルのinserted・skipped件数。
            dry_run=Trueのinsertedは実登録ではなく登録予定件数。

    Raises:
        ValueError: 設定・値・既存キー・実テーブルの列定義が不正な場合。
        sqlalchemy.exc.SQLAlchemyError: 制約等でDB登録に失敗した場合。
    """
    start, end = options.period()
    defaults = settings.get("seed_defaults", {})
    if (
        not isinstance(defaults, dict)
        or set(defaults) - set(TABLE_NAMES)
        or any(not isinstance(values, dict) for values in defaults.values())
    ):
        raise ValueError(
            "seed_defaultsはimport_management・customer・contract・dailyの辞書で指定してください"
        )
    # 省エネサポートサービスの実際のレコードタイプIDは環境ごとに指定する。
    # 不明なIDを生成して全件未加入と誤判定させないよう、接続前に検証する。
    record_types = settings.get("seed_record_type_ids")
    if options.syousapo == "alternate":
        required_types = ("joined", "not_joined")
    elif options.syousapo == "joined":
        required_types = ("joined",)
    else:
        required_types = ("not_joined",)
    if not isinstance(record_types, dict) or any(
        not isinstance(record_types.get(kind), str) or not record_types[kind].strip()
        for kind in required_types
    ):
        raise ValueError(
            "seed_record_type_idsにjoined・not_joinedの実際のIDを指定してください"
        )
    if (
        options.syousapo == "alternate"
        and record_types["joined"] == record_types["not_joined"]
    ):
        raise ValueError(
            "joined・not_joinedのレコードタイプIDは別の値を指定してください"
        )
    import_name = settings.get(
        "import_management_table", TABLE_NAMES["import_management"]
    )
    if (
        import_name.casefold()
        == settings.get("management_table", "t_power_report_mng_info").casefold()
    ):
        raise ValueError(
            "import_management_tableとmanagement_tableは別のテーブルを指定してください"
        )
    source = DatabaseSource(settings)
    try:
        if options.init_sqlite:
            init_sqlite_tables(source.engine, settings)
        result = {
            "dry_run": options.dry_run,
            "count": options.count,
            "start": start.strftime("%Y-%m-%d"),
            "end": (end - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "tables": {kind: {"inserted": 0, "skipped": 0} for kind in TABLE_NAMES},
        }
        # 1つの接続・トランザクションで4テーブルを登録し、部分登録を残さない。
        with source.engine.begin() as connection:
            metadata = MetaData()
            tables = {
                kind: Table(
                    settings.get(f"{kind}_table", name),
                    metadata,
                    schema=settings.get("schema", "db_corp"),
                    autoload_with=connection,
                )
                for kind, name in TABLE_NAMES.items()
            }
            mapping = {
                **SEED_CUSTOMER_COLUMNS,
                **customer_column_mapping(tables["customer"], settings),
            }
            customer_point = settings.get("customer_point_column", CUSTOMER_POINT)
            filters = settings.get("customer_filters", {})
            if any(name.upper() == customer_point.upper() for name in filters):
                raise ValueError("customer_filtersには供給地点の固定値を指定できません")
            for name, value in filters.items():
                if name.upper() == mapping["record_type_id"].upper() and any(
                    record_types[kind] != value for kind in required_types
                ):
                    raise ValueError(
                        "customer_filtersのレコードタイプIDとsyousapoの生成指定が一致しません"
                    )
            now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)

            def prepare(kind, core):
                table = tables[kind]
                values = {
                    str(name).upper(): value
                    for name, value in defaults.get(kind, {}).items()
                }
                audit = {
                    "CREATED_BY": "test_data_seed",
                    "CREATED_AT": now,
                    "UPDATED_BY": "test_data_seed",
                    "UPDATED_AT": now,
                }
                for name, value in audit.items():
                    if any(c.name.upper() == name for c in table.c):
                        values.setdefault(name, value)
                # 主キー・契約値・48枠は生成値を使用し、追加列の設定で変更しない。
                values.update(
                    {str(name).upper(): value for name, value in core.items()}
                )
                return prepare_row(table, values)

            def insert_one(kind, core, keys):
                table = tables[kind]
                row = prepare(kind, core)
                exists = (
                    connection.execute(
                        select(next(iter(table.c)))
                        .where(
                            *[
                                DatabaseSource._column(table, key)
                                == row[DatabaseSource._column(table, key).name]
                                for key in keys
                            ]
                        )
                        .limit(1)
                    ).first()
                    is not None
                )
                if exists:
                    if options.on_existing == "error":
                        raise ValueError(f"{table.name}に既存キーがあります: {keys}")
                    result["tables"][kind]["skipped"] += 1
                else:
                    if not options.dry_run:
                        connection.execute(table.insert(), row)
                    result["tables"][kind]["inserted"] += 1

            for serial in range(options.start_id, options.start_id + options.count):
                point = options.point_prefix + str(serial).zfill(
                    22 - len(options.point_prefix)
                )
                company = f"TEST{serial:010d}"
                joined = options.syousapo == "joined" or (
                    options.syousapo == "alternate" and serial % 2 == 0
                )
                customer_core = {
                    customer_point: point,
                    mapping["customer_name"]: f"テスト事業所{serial:06d}",
                    mapping["address"]: f"東京都テスト区テスト町{serial}番地（架空）",
                    mapping["customer_number"]: f"{serial:016d}",
                    mapping["company_id"]: company,
                    mapping["record_type_id"]: record_types[
                        "joined" if joined else "not_joined"
                    ],
                }
                if any(
                    c.name.upper() == "CMN_BUSINESSTYPE__C"
                    for c in tables["customer"].c
                ):
                    customer_core["CMN_BusinessType__c"] = "2"
                if any(
                    c.name.upper() == "CMN_POWERCONTRACT__C"
                    for c in tables["customer"].c
                ):
                    customer_core["CMN_PowerContract__c"] = str(options.contract_kw)
                customer_core.update(filters)
                customer_keys = {customer_point: point, **filters}
                if "CMN_BusinessType__c" in customer_core:
                    customer_keys.setdefault(
                        "CMN_BusinessType__c", customer_core["CMN_BusinessType__c"]
                    )
                insert_one("customer", customer_core, customer_keys)
                insert_one(
                    "contract",
                    {CONTRACT_POINT: point, CONTRACT_POWER: str(options.contract_kw)},
                    {CONTRACT_POINT: point},
                )
                daily = tables["daily"]
                date_col = DatabaseSource._column(daily, DATE)
                existing = set(
                    connection.execute(
                        select(date_col).where(
                            DatabaseSource._column(daily, POINT) == point,
                            date_col >= start.strftime("%Y%m%d"),
                            date_col < end.strftime("%Y%m%d"),
                        )
                    ).scalars()
                )
                chunk = []
                for core in make_daily_rows(
                    point, serial, start, end, options, settings
                ):
                    row = prepare("daily", core)
                    if row[date_col.name] in existing:
                        if options.on_existing == "error":
                            raise ValueError(
                                f"{daily.name}に既存の日別キーがあります: {point}/{core[DATE]}"
                            )
                        result["tables"]["daily"]["skipped"] += 1
                        continue
                    chunk.append(row)
                    result["tables"]["daily"]["inserted"] += 1
                    if len(chunk) == options.chunk_size:
                        if not options.dry_run:
                            connection.execute(daily.insert(), chunk)
                        chunk.clear()
                if chunk and not options.dry_run:
                    connection.execute(daily.insert(), chunk)
                # 先にARVE・契約・実績を登録し、最後に取込完了を登録する。
                # レポート管理へのINSERTは、取込確認の別処理に委ねる。
                insert_one(
                    "import_management",
                    {
                        IMPORT_POINT: point,
                        IMPORT_MONTH: options.report_month.replace("-", ""),
                        IMPORT_STATUS: "3",
                        "ERROR_MESSAGE": None,
                        "LINKED_ERROR_MESSAGE": None,
                        "LINKED_DATE": None,
                    },
                    {
                        IMPORT_POINT: point,
                        IMPORT_MONTH: options.report_month.replace("-", ""),
                    },
                )
        return result
    finally:
        source.close()


def main():
    """CLIの件数・期間等を受け取り、テストデータを登録して件数を表示する。"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--db-config", type=Path, required=True, help="DB設定JSONのパス"
    )
    parser.add_argument("--report-month", required=True, help="対象の最終月（YYYY-MM）")
    parser.add_argument("--count", type=int, default=10, help="登録する供給地点数")
    period = parser.add_mutually_exclusive_group()
    period.add_argument(
        "--months", type=int, default=12, help="対象月を含む実績月数（1〜12）"
    )
    period.add_argument(
        "--days", type=int, help="月数の代わりに月末までの実績日数を指定"
    )
    parser.add_argument("--start-id", type=int, default=1, help="テスト番号の開始値")
    parser.add_argument(
        "--point-prefix", default="999900", help="供給地点番号の先頭の数字"
    )
    parser.add_argument(
        "--max-kw", type=float, default=1200, help="30分平均電力の最大値（kW）"
    )
    parser.add_argument(
        "--contract-kw", type=float, default=1600, help="契約電力（kW）"
    )
    parser.add_argument("--seed", type=int, default=42, help="実績生成の乱数シード")
    parser.add_argument(
        "--syousapo",
        choices=("alternate", "joined", "not-joined"),
        default="alternate",
        help="ARVEのレコードタイプ（交互・全件加入・全件未加入）",
    )
    parser.add_argument(
        "--on-existing",
        choices=("error", "skip"),
        default="error",
        help="既存キーで中止するか既存行を保持して続けるか",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=200, help="日別実績のINSERTをまとめる上限行数"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="検証と登録予定件数の計算だけ行う"
    )
    parser.add_argument(
        "--init-sqlite", action="store_true", help="SQLite用の最小4テーブルを作成する"
    )
    args = vars(parser.parse_args())
    settings = json.loads(args.pop("db_config").read_text(encoding="utf-8"))
    result = seed_database(settings, SeedOptions(**args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
