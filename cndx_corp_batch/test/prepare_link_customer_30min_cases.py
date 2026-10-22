"""PG2-1-01のケース単位で連携バッチの入力・更新前データを準備する。"""

import argparse
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path

from sqlalchemy import DateTime, create_engine, select

from . import insert_link_customer_30min_data as seed


CATALOG = Path(__file__).with_name("link_customer_30min_cases.json")
FIXED_TIME = datetime(2026, 1, 1)
OLD_TIME = datetime(2000, 1, 1)
KEYS = {
    "corporate": ("CORPORATE_NUMBER",),
    "building": ("CORPORATE_NUMBER", "AGREEMENT_CATEGORY", "ORG_ID", "BUILDING_ID"),
    "customer": ("CMN_SupplyPointSpecificNum__c",),
    "daily": ("T01_KYO_CTN_TOK_NO", "T01_GET_YMD"),
    "management": ("SUPPLY_POINT_NUMBER", "TARGET_YEAR_MONTH"),
    "linked": (
        "CORP_NUMBER", "AGREEMENT_CATEGORY", "ORG_ID", "BUILDING_ID",
        "SUPPLY_POINT_NUMBER", "ACQUISITION_DATE",
    ),
}
BATCH_DATES = {
    3: "2026-08-01", 4: "2026-08-15", 5: "2026-08-16", 6: "2026-08-31",
    7: "2026-01-15", 8: "2026-01-16", 9: "2028-02-29",
}
NOTES = {
    13: "手順どおり対象年月も不一致にするため、紐付け日時単独の除外条件の検証にはならない。",
    45: "現行SQLのINTEGERへのCASTは-1を許容する。非負制約等がないDBでは仕様書のエラー期待を満たさない。",
    50: "現行SQLのINTEGERへのCASTは-1を許容する。非負制約等がないDBでは仕様書のエラー期待を満たさない。",
    52: "手順の列名は不正値件数だが、テスト内容に従い電力量1（T01_30T_SYR01）に設定する。",
    53: "手順の列名は不正値件数だが、テスト内容に従い電力量1（T01_30T_SYR01）に設定する。",
    54: "手順の列名は不正値件数だが、テスト内容に従い電力量1（T01_30T_SYR01）に設定する。",
    55: "手順の列名は不正値件数だが、テスト内容に従い電力量1（T01_30T_SYR01）に設定する。",
    65: "FILE_UPDATE_DATEはTIMESTAMP。現行SQLはNULLを登録するため、仕様書の空文字期待とは異なる。",
    70: "準備後に同じバッチコマンドを2回実行し、2回目の処理件数が0であることを確認する。",
    71: "電力量1にABを設定し、PostgreSQLの数値変換エラーを発生させる。",
    72: "15地点を昇順に配置。先頭10地点は正常、後半5地点は電力量1がAB。batch-size=10で先頭10件が確定し、後半5件はロールバックされる。",
}


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _target_month(batch_date):
    offset = 3 if batch_date.day <= 15 else 2
    year, month = divmod(batch_date.year * 12 + batch_date.month - 1 - offset, 12)
    return date(year, month + 1, 1)


def _existing_linked(values, daily):
    building = values["building"]
    return {
        "CORP_NUMBER": building["CORPORATE_NUMBER"],
        **{key: building[key] for key in KEYS["building"] if key != "CORPORATE_NUMBER"},
        "SUPPLY_POINT_NUMBER": building["SUPPLY_POINT_NUMBER"],
        "ACQUISITION_DATE": daily["T01_GET_YMD"],
        "CORP_NAME": "更新前企業名", "BUILDING_NAME": "更新前建物名",
        "EP_CUSTOMER_NUMBER": "0000000000000", "COMPANY_ID": "00000000000000",
        "MISSING_TIME_RANGE_COUNT": 9, "INVALID_TIME_RANGE_COUNT": 8,
        **{f"V30MIN_USED_ENERGY_{i}": 999 for i in range(1, 49)},
        "DELETE_FLG": True, "CREATED_BY": "pg2_original", "CREATED_AT": OLD_TIME,
        "UPDATED_BY": "pg2_old_updater", "UPDATED_AT": OLD_TIME,
        "FILE_UPDATE_DATE": OLD_TIME, "ARVE_CORP_NAME": "更新前ARVE名",
        "ARVE_CUSTOMER_NUMBER": "0000000000000", "ARVE_OFFICE_CODE": "999",
    }


def build_plan(case_id: str, start_id: int | None = None):
    """DB接続なしで、仕様書の行情報と投入する全レコードを組み立てる。"""
    catalog = load_catalog()
    case = next((c for c in catalog["cases"] if c["case_id"] == case_id), None)
    if case is None:
        raise ValueError("ケースIDが不正です。新版仕様書の項番1～72を--listで確認してください。")
    number = case["number"]
    batch_date = date.fromisoformat(BATCH_DATES.get(number, "2026-08-19"))
    month = _target_month(batch_date)
    count = {2: 0, 19: 0, 21: 9, 22: 10, 23: 11, 24: 21, 72: 15}.get(number, 1)
    first_id = start_id if start_id is not None else case["source_row"] * 100 + 1
    if not 1 <= first_id <= 999999999 - max(count - 1, 0):
        raise ValueError("start-idは1以上で、最終番号が9桁以内になる値を指定してください。")
    options = seed.SeedOptions(
        target_month=month.strftime("%Y-%m"), count=max(1, count), days=1,
        start_id=first_id, point_prefix="999901",
    )
    start, end = options.period()
    rows = {key: [] for key in KEYS}
    points = []
    for index, (serial, point) in enumerate(seed._points(options)):
        if index >= count:
            break
        points.append(point)
        values = seed._source_values(serial, point, options, FIXED_TIME)
        values["customer"]["CMN_DemandLocationFullName_Ref__c"] = f"ARVEテスト名{serial}"
        values["management"]["ERROR_MESSAGE"] = "元の取込メッセージ（保持確認）"
        daily = next(seed._daily_rows(point, serial, start, end, options, FIXED_TIME))
        daily.update({column: str(i) for i, column in enumerate(seed.SLOT_COLUMNS, 1)})
        if number == 11:
            values["management"]["CREATE_STATUS"] = "4"
        if number in (12, 13):
            values["management"]["TARGET_YEAR_MONTH"] = (month - timedelta(days=1)).strftime("%Y%m")
        if number == 13:
            values["management"]["LINKED_DATE"] = FIXED_TIME
        if number == 16:
            values["building"]["DELETE_FLG"] = True
        if number == 18:
            values["building"]["SUPPLY_POINT_NUMBER"] = "999902" + point[6:]
        if number in (35, 36, 38, 39):
            values["customer"]["CMN_OldCustomerNum__c"] = {
                35: "012", 36: "0123", 38: "012", 39: "01",
            }[number]
        if 41 <= number <= 50:
            column = "T01_KSKJ_KSU" if number <= 45 else "T01_FSIJ_KSU"
            daily[column] = ("12", "0", "", "AB", "-1")[(number - 41) % 5]
        if 52 <= number <= 55:
            daily["T01_30T_SYR01"] = ("0.12", "0", "", "AB")[number - 52]
        if number == 71 or (number == 72 and index >= 10):
            daily["T01_30T_SYR01"] = "AB"
        if number == 69:
            values["management"]["LINKED_ERROR_MESSAGE"] = "前回の紐付けエラー"
        for key, value in values.items():
            if key != "building" or number != 15:
                rows[key].append(value)
        rows["daily"].append(daily)
        if number in (61, 62, 63, 64, 67):
            rows["linked"].append(_existing_linked(values, daily))
    notes = [NOTES[number]] if number in NOTES else []
    if case["kind"] == "異常系":
        notes.append("SQLiteでは不正文字列のCASTがエラーにならないため、異常系の結果確認はPostgreSQLで行う。")
    return {
        "source": catalog["source"], "sheet": catalog["sheet"], **case,
        "batch_date": batch_date.isoformat(), "target_month": month.strftime("%Y-%m"),
        "batch_size": 10, "points": points, "notes": notes,
        "batch_environment": {
            "CUT_OFF_DAY": "16",
            "REPORT_MONTH_OFFSET_BEFORE": "3",
            "REPORT_MONTH_OFFSET_AFTER": "2",
        },
        "batch_command": "python -m cndx_corp_batch.entrypoints.link_customer_30min "
                         f"--batch-date {batch_date.isoformat()} --batch-size 10",
        "rows": rows,
    }


def insert_plan(settings, plan, *, init_sqlite=False):
    """事前検証後、全投入を1トランザクションで行う。既存行は変更しない。"""
    url = settings.get("url") or os.getenv(settings.get("url_env", "DATABASE_URL"))
    if not url:
        raise ValueError("DB接続先がありません。設定JSONのurlまたはurl_envを指定してください。")
    engine = create_engine(url)
    try:
        if init_sqlite:
            if engine.dialect.name != "sqlite":
                raise ValueError("--init-sqliteはSQLiteでのみ使用できます。")
            seed.init_sqlite_tables(engine, settings)
        with engine.begin() as connection:
            tables = seed._reflect_tables(connection, settings)
            prepared = []
            for key, input_rows in plan["rows"].items():
                table = tables[key]
                for values in input_rows:
                    # テスト条件の列が欠けていても黙って捨てない。
                    seed._require_columns(table, tuple(values))
                    row = seed._row(table, values)
                    for name, value in row.items():
                        column = table.c[name]
                        if value is None and not column.nullable:
                            raise ValueError(f"{table.name}.{name}はNOT NULLです。ケース{plan['case_id']}のNULL条件は投入できません。")
                        if value == "" and isinstance(column.type, DateTime):
                            raise ValueError(f"{table.name}.{name}は日時型です。空文字条件は投入できません。")
                    keys = seed._row(table, {name: values[name] for name in KEYS[key]})
                    exists = connection.execute(select(table).where(
                        *(table.c[name] == value for name, value in keys.items())
                    ).limit(1)).first()
                    if exists:
                        raise ValueError(f"{table.name}に既存キーがあります: {keys}。別の検証DBまたは--start-idを使用してください。")
                    prepared.append((table, row))
            linked = tables["linked"]
            point_column = linked.c[seed._column_map(linked)["SUPPLY_POINT_NUMBER"]]
            if plan["points"] and connection.execute(select(linked).where(
                point_column.in_(plan["points"])
            ).limit(1)).first():
                raise ValueError("生成する供給地点に連携先の既存行があります。初期状態を確認してください。")
            for table, row in prepared:
                connection.execute(table.insert(), row)
        return {key: len(rows) for key, rows in plan["rows"].items()}
    finally:
        engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="ケースID・仕様書の行番号・名称を表示")
    parser.add_argument("--case", help="新版仕様書の項番（1～72）")
    parser.add_argument("--db-config", type=Path, help="既存投入PGと共通のDB設定JSON")
    parser.add_argument("--start-id", type=int, help="テスト番号の開始値。省略時はケースごとに固定")
    parser.add_argument("--dry-run", action="store_true", help="DB接続せず投入計画を確認")
    parser.add_argument("--output", type=Path, help="投入データ全件を含む計画JSONの保存先")
    parser.add_argument("--init-sqlite", action="store_true", help="SQLite用の最小検証テーブルを作成")
    args = parser.parse_args(argv)
    if args.list:
        for case in load_catalog()["cases"]:
            print(f"{case['case_id']:>4}  Excel行{case['source_row']:>2}  {case['title']}")
        return 0
    if not args.case:
        parser.error("--caseまたは--listを指定してください。")
    if not args.dry_run and not args.db_config:
        parser.error("投入時は--db-configが必要です。計画のみの場合は--dry-runを指定してください。")
    try:
        plan = build_plan(args.case, args.start_id)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        summary = {key: value for key, value in plan.items() if key != "rows"}
        summary["planned_counts"] = {key: len(rows) for key, rows in plan["rows"].items()}
        summary["mode"] = "dry-run" if args.dry_run else "insert"
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not args.dry_run:
            settings = json.loads(args.db_config.read_text(encoding="utf-8-sig"))
            counts = insert_plan(settings, plan, init_sqlite=args.init_sqlite)
            print("投入完了: " + json.dumps(counts, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"準備失敗: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
