"""画面登録からバッチ完了までを確認するための業務データ。"""

import argparse
from datetime import datetime

from sqlalchemy import Connection, MetaData, Table, select

from cndx_corp_batch.test.insert_link_customer_30min_data import _require_columns, _row
from cndx_corp_batch.test.prepare_sales_user_handover_cases import (
    TABLE_NAMES,
    build_plan,
)

MARKER = "handover_screen_seed"


def build_business_rows(args: argparse.Namespace) -> dict[str, list[dict]]:
    # 2法人・過去データ8表の既存ケースを再利用し、予定は画面から登録する。
    plan = build_plan(
        "42",
        start_id=args.start_id,
        agreement_category=args.agreement_category,
        energy_code=args.energy_code,
    )
    rows = plan["rows"]
    rows["handover"] = []
    for items in rows.values():
        for row in items:
            row["CREATED_BY"] = MARKER
            # 初期データは全件引継元。元・先が同じ組織のケースも許可する。
            for key in ("ORG_ID", "AGREEMENT_ORG"):
                if key in row:
                    row[key] = args.from_org_id
            if "USER_ID" in row:
                row["USER_ID"] = args.from_user_id
    for row in rows["corporate"]:
        row.update(COMPANY_ADDRESS_PREFECTURE="13", COMPANY_ADDRESS_CITY="千代田区1-1")
    rows["details"] = [
        {
            "CORPORATE_NUMBER": row["CORPORATE_NUMBER"],
            "AGREEMENT_CATEGORY": args.agreement_category,
            "ORG_ID": args.from_org_id,
            "DELETE_FLG": False,
            "CREATED_BY": MARKER,
            "CREATED_AT": datetime.now(),
        }
        for row in rows["corporate"]
    ]
    return rows


def _tables(connection: Connection) -> dict[str, Table]:
    names = {**TABLE_NAMES, "details": "m_corporate_details_info"}
    return {
        key: Table(name, MetaData(), schema="db_corp", autoload_with=connection)
        for key, name in names.items()
    }


def _existing(connection: Connection, tables: dict, numbers: list[str]) -> dict:
    return {
        key: connection.execute(
            select(table).where(table.c.corporate_number.in_(numbers))
        )
        .mappings()
        .all()
        for key, table in tables.items()
    }


def _validate_handover(row: dict, args: argparse.Namespace) -> None:
    if row["created_by"] == MARKER:
        if (row["handover_from_org_id"], row["handover_from_user_id"]) == (
            args.from_org_id, args.from_user_id
        ):
            return
        raise ValueError("試験用引継予定の引継元が異なります。")
    expected = {
        "handover_from_org_id": args.from_org_id,
        "handover_from_user_id": args.from_user_id,
        "handover_to_org_id": args.to_org_id,
        "handover_to_user_id": args.to_user_id,
        "creator_id": args.login_user_id,
        "handover_schedule_date": args.schedule_date.strftime("%Y%m%d"),
        "handover_type": getattr(args, "handover_type", "1"),
    }
    if any(row[key] != value for key, value in expected.items()):
        raise ValueError("対象法人に今回の画面操作以外の引継予定があります。")


def _check_ownership(existing: dict, args: argparse.Namespace) -> None:
    for key, rows in existing.items():
        for row in rows:
            if key == "handover":
                _validate_handover(row, args)
            elif row["created_by"] != MARKER:
                raise ValueError(f"{key}に準備PG以外が作成したデータがあります。")
            elif key == "staff" and (
                row["org_id"] != args.from_org_id
                or row["user_id"] not in {args.from_user_id, args.to_user_id}
            ):
                raise ValueError("今回と異なる担当者のデータがあるため停止します。")


def prepare_business(connection: Connection, args: argparse.Namespace) -> str:
    rows = build_business_rows(args)
    tables = _tables(connection)
    numbers = [row["CORPORATE_NUMBER"] for row in rows["corporate"]]
    existing = _existing(connection, tables, numbers)
    _check_ownership(existing, args)
    if args.verify_stage:
        return _verify(existing, rows, args)
    if args.cleanup:
        order = [
            "handover",
            "H",
            "G",
            "E",
            "D",
            "C",
            "B",
            "A",
            "F",
            "staff",
            "details",
            "corporate",
        ]
        for key in order:
            connection.execute(
                tables[key].delete().where(tables[key].c.corporate_number.in_(numbers))
            )
        return "業務データ削除完了"
    if any(existing.values()):
        raise ValueError(
            "対象法人のデータが既にあります。確認またはcleanup後に再投入してください。"
        )
    staff = tables["staff"]
    if connection.execute(
        select(staff)
        .where(staff.c.user_id.in_([args.from_user_id, args.to_user_id]))
        .limit(1)
    ).first():
        raise ValueError("テスト担当者が別の担当企業に使用されています。")
    _insert_rows(connection, tables, rows, args.apply)
    return f"対象法人: {', '.join(numbers)}（予定は画面から登録）"


def _insert_rows(connection: Connection, tables: dict, rows: dict, apply: bool) -> None:
    for key in [
        "corporate",
        "details",
        "staff",
        "F",
        "A",
        "B",
        "C",
        "D",
        "E",
        "G",
        "H",
    ]:
        table = tables[key]
        for values in rows[key]:
            _require_columns(table, tuple(values))
            if apply:
                connection.execute(table.insert().values(**_row(table, values)))


def _verify(existing: dict, expected: dict, args: argparse.Namespace) -> str:
    numbers = {row["CORPORATE_NUMBER"] for row in expected["corporate"]}
    targets = existing["handover"]
    if len(targets) != 2 or {r["corporate_number"] for r in targets} != numbers:
        raise ValueError("引継予定が2法人分登録されていません。")
    is_completed = args.verify_stage == "completed"
    for target in targets:
        status = "0" if is_completed else "1"
        if target["handover_status"] != status:
            raise ValueError(f"引継ステータスが期待値{status}ではありません。")
        if is_completed and target["handovered_at"] is None:
            raise ValueError("引継実施日時がありません。")
        _verify_corporation(existing, target, args, is_completed)
    return f"確認OK: {args.verify_stage} / 2法人 / 担当者 / 過去データ8表"


def _verify_corporation(
    existing: dict, target: dict, args: argparse.Namespace, is_completed: bool
) -> None:
    number = target["corporate_number"]
    staff = [row for row in existing["staff"] if row["corporate_number"] == number]
    user_id = args.to_user_id if is_completed else args.from_user_id
    if (
        len(staff) != 1
        or staff[0]["user_id"] != user_id
        or staff[0]["org_id"] != args.from_org_id
    ):
        raise ValueError("担当者IDまたは担当者情報の組織IDが期待値と異なります。")
    org_id = (
        args.to_org_id
        if is_completed and target["report_data_flg"]
        else args.from_org_id
    )
    for key in "ABCDEFGH":
        data = [row for row in existing[key] if row["corporate_number"] == number]
        column = "agreement_org" if key == "F" else "org_id"
        if len(data) != 1 or data[0][column] != org_id:
            raise ValueError(f"過去データ{key}の件数または組織IDが期待値と異なります。")
