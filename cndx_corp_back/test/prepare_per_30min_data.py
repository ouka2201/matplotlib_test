"""30分値登録画面/API-02のD01・D02とDB依存の派生条件を準備する。"""

import argparse
import os
from datetime import datetime

from sqlalchemy import MetaData, Table, create_engine, select


MARKER = "UT30_PER30MIN"
CASES = (
    "base", "two-buildings", "no-data", "one-day", "year-cross", "leap-day",
    "arve-null", "arve-empty", "raw-deleted", "raw-null-delete",
    "building-deleted", "building-null-delete", "no-building", "no-timestamps",
)
CREATED_1 = datetime(2026, 1, 3, 4, 5, 6)
CREATED_2 = datetime(2026, 1, 4, 4, 5, 6)
UPDATED_2 = datetime(2026, 1, 5, 10, 20, 30)
FILE_DATE = datetime(2025, 12, 1)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, default="base")
    parser.add_argument("--corp-number", required=True, help="C1: 13桁法人番号")
    parser.add_argument("--org-id", required=True, help="O1: 組織ID")
    parser.add_argument("--other-org-id", required=True, help="O2: O1とは異なる組織ID")
    parser.add_argument("--create-masters", action="store_true", help="企業基本・企業詳細・O1/O2も新規作成")
    parser.add_argument("--template-building-id", help="既存マスタを使う場合の複製元拠点ID")
    parser.add_argument("--prefecture-code", default="13", help="新規マスタの都道府県コード")
    parser.add_argument("--supply-point-1", required=True, help="P1: D01の供給地点特定番号")
    parser.add_argument("--supply-point-2", required=True, help="P2: D02の供給地点特定番号")
    parser.add_argument("--building-id-1", default="UT30-B20", help="B20: D01の拠点ID")
    parser.add_argument("--building-id-2", default="UT30-B10", help="B10: D02の拠点ID")
    parser.add_argument("--database-url-env", default="TEST_DATABASE_URL")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="トランザクションで準備")
    action.add_argument("--cleanup", action="store_true", help="このPGが作成した行を削除")
    args = parser.parse_args(argv)
    if len(args.corp_number) != 13 or not args.corp_number.isdigit():
        parser.error("--corp-number は13桁の数字を指定してください")
    if args.org_id == args.other_org_id:
        parser.error("O1とO2は別の組織IDにしてください")
    if args.building_id_1 == args.building_id_2 or not args.building_id_2 < args.building_id_1:
        parser.error("B10とB20は異なるIDとし、B10 < B20にしてください")
    if not args.create_masters and not args.template_building_id and not args.cleanup:
        parser.error("既存マスタを使う場合は --template-building-id が必要です")
    if args.template_building_id in (args.building_id_1, args.building_id_2):
        parser.error("複製元と試験用拠点IDは分けてください")
    if any(len(value) > 20 for value in (args.org_id, args.other_org_id)):
        parser.error("組織IDは20文字以内にしてください")
    if args.supply_point_1 == args.supply_point_2:
        parser.error("P1とP2は異なる番号にしてください")
    if any(len(value) > 22 for value in (args.supply_point_1, args.supply_point_2)):
        parser.error("供給地点特定番号は22文字以内にしてください")
    if any(len(value) > 113 for value in (args.building_id_1, args.building_id_2)):
        parser.error("拠点IDは113文字以内にしてください")
    return args


def _tables(connection):
    metadata = MetaData()
    return {
        name: Table(name, metadata, schema="db_corp", autoload_with=connection)
        for name in (
            "m_corporate_basic", "m_corporate_details_info", "m_user_organization_info",
            "m_building", "t_electricity_data_30min",
        )
    }


def _one(connection, table, **key):
    return connection.execute(
        select(table).where(*(table.c[name] == value for name, value in key.items()))
    ).mappings().first()


def _target_rows(connection, table, args):
    number_column = "corp_number" if table.name.startswith("t_") else "corporate_number"
    return connection.execute(
        select(table).where(
            table.c[number_column] == args.corp_number,
            table.c.agreement_category == "01",
            table.c.org_id == args.org_id,
            table.c.building_id.in_((args.building_id_1, args.building_id_2)),
        )
    ).mappings().all()


def _check_ownership(connection, tables, args):
    for name in ("m_building", "t_electricity_data_30min"):
        for row in _target_rows(connection, tables[name], args):
            if row["created_by"] != MARKER:
                raise ValueError(
                    f"{name} の拠点 {row['building_id']} に既存データがあります。"
                    "別の --building-id-1/2 を指定してください。"
                )
    if args.create_masters:
        for name, keys in _master_keys(args):
            row = _one(connection, tables[name], **keys)
            if row is not None and row["created_by"] != MARKER:
                raise ValueError(f"{name} の {keys} に既存データがあります。別のIDを指定してください。")


def _master_keys(args):
    return (
        ("m_user_organization_info", {"org_id": args.org_id}),
        ("m_user_organization_info", {"org_id": args.other_org_id}),
        ("m_corporate_basic", {"corporate_number": args.corp_number}),
        ("m_corporate_details_info", {
            "corporate_number": args.corp_number,
            "agreement_category": "01", "org_id": args.org_id,
        }),
    )


def _delete_owned(connection, tables, args):
    for name in ("t_electricity_data_30min", "m_building"):
        table = tables[name]
        number_column = "corp_number" if name.startswith("t_") else "corporate_number"
        connection.execute(
            table.delete().where(
                table.c[number_column] == args.corp_number,
                table.c.agreement_category == "01",
                table.c.org_id == args.org_id,
                table.c.building_id.in_((args.building_id_1, args.building_id_2)),
                table.c.created_by == MARKER,
            )
        )
    if args.create_masters:
        for name, keys in reversed(_master_keys(args)):
            table = tables[name]
            connection.execute(table.delete().where(
                *(table.c[column] == value for column, value in keys.items()),
                table.c.created_by == MARKER,
            ))


def _new_masters(args):
    """新規マスタ行と、拠点作成に使う最低限の選択値を返す。"""
    audit = {"delete_flg": False, "created_by": MARKER, "created_at": CREATED_1}
    orgs = [
        {"org_id": org_id, "org_name": name, "org_type_code": "01",
         "org_type": "EP", "company_name": "30分値試験用組織", **audit}
        for org_id, name in ((args.org_id, "30分値試験組織O1"),
                             (args.other_org_id, "30分値試験組織O2"))
    ]
    basic = {
        "corporate_number": args.corp_number, "company_name": "30分値試験企業",
        "company_name_kana": "サンジュップンチシケンキギョウ",
        "company_address_prefecture": args.prefecture_code,
        "company_address_city": "千代田区千代田1-1", **audit,
    }
    detail = {"corporate_number": args.corp_number,
              "agreement_category": "01", "org_id": args.org_id, **audit}
    template = {
        "corporate_number": args.corp_number, "agreement_category": "01",
        "org_id": args.org_id, "building_address_prefecture": args.prefecture_code,
        "building_address_city": "千代田区千代田1-1",
        "ep_office_code": "001", "ep_customer_number": "0000000000001",
    }
    return (("m_user_organization_info", orgs),
            ("m_corporate_basic", [basic]),
            ("m_corporate_details_info", [detail])), basic, template


def _validate_sources(connection, tables, args):
    basic = _one(connection, tables["m_corporate_basic"], corporate_number=args.corp_number)
    detail = _one(
        connection, tables["m_corporate_details_info"], corporate_number=args.corp_number,
        agreement_category="01", org_id=args.org_id,
    )
    org1 = _one(connection, tables["m_user_organization_info"], org_id=args.org_id)
    org2 = _one(connection, tables["m_user_organization_info"], org_id=args.other_org_id)
    template = _one(
        connection, tables["m_building"], corporate_number=args.corp_number,
        agreement_category="01", org_id=args.org_id,
        building_id=args.template_building_id,
    )
    if not all((basic, detail, org1, org2, template)):
        raise ValueError("C1/O1/O2、区分01の企業詳細、複製元拠点を既存マスタから確認できません")
    if any(row["delete_flg"] is True for row in (basic, detail, org1, org2, template)):
        raise ValueError("既存マスタまたは複製元拠点が削除扱いです")
    return basic, template


def build_rows(args, basic, template):
    """既存マスタの拠点を複製し、D01/D02の試験値だけ差し替える。"""
    buildings = []
    data = []
    include_second = args.case == "two-buildings"
    for index in (1, 2) if include_second else (1,):
        building_id = args.building_id_1 if index == 1 else args.building_id_2
        supply = args.supply_point_1 if index == 1 else args.supply_point_2
        name = "A拠点" if index == 1 else "B拠点"
        building = dict(template)
        building.update(
            building_id=building_id, location_identifier_code=building_id,
            location_identifier_name=name, building_name=name,
            supply_point_number=supply, agreement_org=args.other_org_id if index == 1 else args.org_id,
            delete_flg=False, created_by=MARKER, created_at=CREATED_1,
            updated_by=None, updated_at=None,
        )
        if args.case == "building-deleted":
            building["delete_flg"] = True
        elif args.case == "building-null-delete":
            building["delete_flg"] = None
        if args.case != "no-building":
            buildings.append(building)

        if args.case == "no-data":
            continue
        if index == 2:
            dates = [("20260103", CREATED_1, None)]
        elif args.case == "one-day":
            dates = [("20260102", CREATED_1, None)]
        elif args.case == "year-cross":
            dates = [("20261231", CREATED_1, None), ("20270101", CREATED_2, UPDATED_2)]
        elif args.case == "leap-day":
            dates = [("20240229", CREATED_1, None)]
        else:
            dates = [("20260102", CREATED_1, None), ("20260104", CREATED_2, UPDATED_2)]
        if args.case == "raw-deleted":
            dates.append(("20260131", CREATED_2, UPDATED_2))
        for date, created, updated in dates:
            row = {
                "corp_number": args.corp_number, "agreement_category": "01",
                "org_id": args.org_id, "building_id": building_id,
                "supply_point_number": supply, "acquisition_date": date,
                "corp_name": basic["company_name"], "building_name": name,
                "arve_corp_name": "ARVE試験会社", "arve_office_code": "012",
                "arve_customer_number": "0000000000045",
                "ep_customer_number": template["ep_customer_number"],
                "file_update_date": FILE_DATE, "delete_flg": False,
                "created_by": MARKER, "created_at": created,
                "updated_by": None, "updated_at": updated,
            }
            row.update({f"v30min_used_energy_{i}": 1 for i in range(1, 49)})
            if args.case in ("arve-null", "arve-empty"):
                value = None if args.case == "arve-null" else ""
                row.update(arve_corp_name=value, arve_office_code=value, arve_customer_number=value)
            if args.case == "raw-null-delete":
                row["delete_flg"] = None
            if args.case == "raw-deleted" and date == "20260131":
                row["delete_flg"] = True
            if args.case == "no-timestamps":
                row.update(created_at=None, updated_at=None)
            data.append(row)
    return buildings, data


def run(args, engine):
    with engine.begin() as connection:
        tables = _tables(connection)
        _check_ownership(connection, tables, args)
        if args.cleanup:
            _delete_owned(connection, tables, args)
            return "PG作成行を削除しました"
        if args.create_masters:
            masters, basic, template = _new_masters(args)
        else:
            masters = ()
            basic, template = _validate_sources(connection, tables, args)
        buildings, data = build_rows(args, basic, template)
        summary = (
            f"{args.case}: マスタ {sum(len(rows) for _, rows in masters) + len(buildings)} 行、"
            f"30分値 {len(data)} 行、"
            f"C1={args.corp_number}, O1={args.org_id}, O2={args.other_org_id}, "
            f"B20={args.building_id_1}, B10={args.building_id_2}"
        )
        if not args.apply:
            return "確認のみ（DB変更なし）: " + summary
        _delete_owned(connection, tables, args)
        for table_name, rows in (*masters, ("m_building", buildings),
                                 ("t_electricity_data_30min", data)):
            table = tables[table_name]
            if rows:
                required = set(rows[0])
                missing = required - set(table.c.keys())
                if missing:
                    raise ValueError(f"{table_name} に列がありません: {sorted(missing)}")
                connection.execute(table.insert(), rows)
        return "準備完了: " + summary


def main(argv=None):
    args = parse_args(argv)
    url = os.getenv(args.database_url_env)
    if not url:
        raise SystemExit(f"環境変数 {args.database_url_env} に検証DBのURLを設定してください")
    engine = create_engine(url)
    try:
        print(run(args, engine))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
