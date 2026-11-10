"""Docs/テストケース/30分値連携.xlsx の UT-001～112 をケース単位で準備する。"""

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path

from . import insert_link_customer_30min_data as seed
from . import prepare_link_customer_30min_cases as legacy


CATALOG = Path(__file__).with_name("link_customer_30min_ut_catalog.json")
FIXED_TIME = datetime(2026, 10, 18, 12, 34, 56)
INJECTION = {
    61: "エラーメッセージ列の長さを超える例外をモックで注入する。",
    62: "UPSERT後の取込管理UPDATEだけを失敗させるモックが必要。",
    63: "同一地点の後続日だけを失敗させるモックが必要。",
    64: "バッチ内部の任意の処理でExceptionを注入する。",
    71: "WARNINGを出す業務条件が確定してからモックを設定する。",
}
DB_LIMITS = {
    11: "CREATE_STATUSがNOT NULLならTD-11は投入できない。",
    14: "LINKED_DATEが日時型なら空文字は投入できない。",
    33: "現行ARVE表は姓・名の別列を持たないため、結合名の空値を準備する。",
    39: "件数列がNOT NULLならTD-39は投入できない。",
    46: "電力量列がNOT NULLならTD-46は投入できない。",
    55: "同一キーの元データ2行は一意制約があるDBでは投入できない。",
}


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _target_month(batch_date):
    offset = 3 if batch_date.day <= 18 else 2
    year, month = divmod(batch_date.year * 12 + batch_date.month - 1 - offset, 12)
    return date(year, month + 1, 1)


def _month_end(month):
    year, next_month = divmod(month.year * 12 + month.month, 12)
    return date(year, next_month + 1, 1) - timedelta(days=1)


def build_plan(case_id):
    catalog = load_catalog()
    case = next((item for item in catalog["cases"] if item["case_id"] == case_id), None)
    if case is None:
        raise ValueError("UTケースIDが不正です。--listで確認してください。")
    td = int(case["test_data_id"].split("-")[1])
    number = int(case_id.split("-")[1])
    batch_date = {
        2: date(2026, 10, 1), 3: date(2026, 10, 18),
        4: date(2026, 10, 19), 5: date(2026, 10, 31),
        6: date(2026, 1, 18), 7: date(2026, 1, 19),
        8: date(2028, 2, 29),
    }.get(td, date(2026, 10, 18))
    month = _target_month(batch_date)
    count = {9: 0, 18: 999, 19: 1000, 20: 1001, 21: 2001,
             52: 2, 53: 2, 54: 2, 57: 2, 60: 2, 66: 4, 67: 3,
             68: 4, 72: 3}.get(td, 1)
    options = seed.SeedOptions(target_month=month.strftime("%Y-%m"),
                               count=max(1, count), days=1,
                               start_id=number * 10000 + 1, point_prefix="999901")
    options.period()
    rows = {key: [] for key in legacy.KEYS}
    points = []
    for index, (serial, point) in enumerate(seed._points(options)):
        if index >= count:
            break
        values = seed._source_values(serial, point, options, FIXED_TIME)
        values["management"]["ERROR_MESSAGE"] = "元の取込メッセージ（保持確認）"
        day = month
        if td == 26:
            day = _month_end(month)
        elif td == 27:
            day = month - timedelta(days=1)
        elif td == 28:
            day = _month_end(month) + timedelta(days=1)
        daily = next(seed._daily_rows(point, serial, day, day + timedelta(days=1),
                                      options, FIXED_TIME))
        daily.update({column: str(slot) for slot, column in enumerate(seed.SLOT_COLUMNS, 1)})
        if td == 10:
            values["management"]["CREATE_STATUS"] = "2"
        elif td == 11:
            values["management"]["CREATE_STATUS"] = None
        elif td == 12:
            values["management"]["TARGET_YEAR_MONTH"] = (
                month - timedelta(days=1)).strftime("%Y%m")
        elif td == 13:
            values["management"]["LINKED_DATE"] = datetime(2020, 1, 1)
        elif td == 14:
            values["management"]["LINKED_DATE"] = ""
        elif td == 16:
            values["building"]["DELETE_FLG"] = True
        elif td == 17:
            values["building"]["SUPPLY_POINT_NUMBER"] = "999902" + point[6:]
        elif td == 23:
            values["corporate"]["COMPANY_NAME"] = "更新前企業名"
        elif td == 32:
            values["customer"]["CMN_DemandLocationFullName_Ref__c"] = "山田太郎"
        elif td == 33:
            values["customer"]["CMN_DemandLocationFullName_Ref__c"] = ""
        elif td in (34, 35, 36):
            values["customer"]["CMN_OldCustomerNum__c"] = {
                34: "ABC123456", 35: "ABC", 36: "AB"}[td]
        elif td == 56 or td == 65:
            values["management"]["LINKED_ERROR_MESSAGE"] = "前回の紐付けエラー"
        if td == 54 and index == 1:
            values["management"]["CREATE_STATUS"] = "2"
        if td == 66 and index >= 2:
            values["management"]["TARGET_YEAR_MONTH"] = (
                month - timedelta(days=1)).strftime("%Y%m")
        if td == 72 and index == 2:
            values["management"]["CREATE_STATUS"] = "2"
        if td == 24:
            daily["T01_KYO_CTN_TOK_NO"] = "999902" + point[6:]
        if td == 37:
            daily["T01_KSKJ_KSU"] = "12"
        elif td == 38:
            daily["T01_FSIJ_KSU"] = "0"
        elif td == 39:
            daily["T01_KSKJ_KSU"] = daily["T01_FSIJ_KSU"] = None
        elif td == 40:
            daily["T01_KSKJ_KSU"] = "AB"
        elif td == 41:
            daily["T01_KSKJ_KSU"] = "-1"
        elif td == 42:
            daily.update({column: f"{slot}.125" for slot, column in
                          enumerate(seed.SLOT_COLUMNS, 1)})
        elif td == 43:
            daily.update({f"T01_30T_SYR{slot:02d}": str(slot * 1000)
                          for slot in (1, 24, 25, 48)})
        elif td == 44:
            daily["T01_30T_SYR01"] = "1.2345"
        elif td == 45:
            daily["T01_30T_SYR01"] = "0"
        elif td == 46:
            daily["T01_30T_SYR01"] = None
            daily["T01_30T_SYR02"] = ""
        elif td == 47:
            daily["T01_30T_SYR01"] = "-0.12"
        elif td in (48, 58, 59) or (td in (60, 72) and index == 1):
            daily["T01_30T_SYR01"] = "AB"
        if td in (50, 51, 52, 59, 68) and (td not in (52, 68) or index < (1 if td == 52 else 2)):
            linked = legacy._existing_linked(values, daily)
            if td == 51:
                linked["CORP_NAME"] = "上書き前名称"
            rows["linked"].append(linked)
        if td == 54 and index == 1:
            rows["linked"].append(legacy._existing_linked(values, daily))
        points.append(point)
        for key, value in values.items():
            if (key == "building" and td == 15) or (key == "corporate" and td == 22) \
                    or (key == "customer" and td == 31):
                continue
            rows[key].append(value)
        if td != 30:
            rows["daily"].append(daily)
        if td in (29, 53, 63, 69, 70):
            days = (15, _month_end(month).day) if td in (29, 53, 63) else \
                   tuple(range(2, 32)) if td == 69 else (0, 32)
            for day_number in days:
                extra_day = month + timedelta(days=day_number - 1)
                if td == 70 and day_number == 0:
                    extra_day = month - timedelta(days=1)
                if td == 70 and day_number == 32:
                    extra_day = _month_end(month) + timedelta(days=1)
                extra = next(seed._daily_rows(point, serial, extra_day,
                                             extra_day + timedelta(days=1), options, FIXED_TIME))
                rows["daily"].append(extra)
    notes = []
    if td in INJECTION:
        notes.append(INJECTION[td])
    if td in DB_LIMITS:
        notes.append(DB_LIMITS[td])
    if td in (23, 54, 55, 57, 61, 62, 63, 64, 71):
        notes.append("二段階操作・既存の対象外行・モック条件はテスト手順側で設定する。")
    return {
        **case, "source": catalog["source"], "test_data_description": catalog["test_data"][case["test_data_id"]],
        "batch_date": batch_date.isoformat(), "target_month": month.strftime("%Y-%m"),
        "batch_size": 1000, "points": points, "rows": rows, "notes": notes,
        "batch_environment": {"CUT_OFF_DAY": "19", "REPORT_MONTH_OFFSET_BEFORE": "3",
                              "REPORT_MONTH_OFFSET_AFTER": "2"},
        "batch_command": "python -m cndx_corp_batch.entrypoints.link_customer_30min "
                         f"--batch-date {batch_date.isoformat()} --batch-size 1000",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--case", help="UT-001～UT-112")
    parser.add_argument("--db-config", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--init-sqlite", action="store_true")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--reset", action="store_true")
    action.add_argument("--cleanup", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        for case in load_catalog()["cases"]:
            print(case["case_id"], case["test_data_id"], case["title"])
        return 0
    if not args.case:
        parser.error("--caseまたは--listを指定してください。")
    if not args.dry_run and not args.db_config:
        parser.error("投入時は--db-configが必要です。")
    try:
        plan = build_plan(args.case)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        summary = {key: value for key, value in plan.items() if key != "rows"}
        summary["planned_counts"] = {key: len(value) for key, value in plan["rows"].items()}
        summary["mode"] = "dry-run" if args.dry_run else "reset" if args.reset else "cleanup" if args.cleanup else "insert"
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        if not args.dry_run:
            settings = json.loads(args.db_config.read_text(encoding="utf-8-sig"))
            counts = legacy.insert_plan(settings, plan, init_sqlite=args.init_sqlite,
                                        reset=args.reset, cleanup=args.cleanup)
            print("処理完了: " + json.dumps(counts, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"準備失敗: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
