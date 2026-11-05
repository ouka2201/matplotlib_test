"""担当者検索・画面登録・引継バッチ実行のテストデータを準備する。"""

import argparse
import os
import re
import secrets
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import (
    Connection,
    Engine,
    MetaData,
    Table,
    create_engine,
    inspect,
    or_,
    select,
)
from sqlalchemy.exc import SQLAlchemyError

MARKER = "handover_screen_seed"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login-user-id", required=True, help="既存の検証用管理者ID")
    parser.add_argument("--from-org-id", required=True, help="引継元組織ID")
    parser.add_argument("--to-org-id", required=True, help="引継先組織ID")
    parser.add_argument(
        "--create-organizations", action="store_true", help="組織も新規作成"
    )
    parser.add_argument(
        "--org-type-code", choices=("01", "02", "03", "04", "05", "06"), default="03"
    )
    parser.add_argument("--from-user-id", default="99009001")
    parser.add_argument("--to-user-id", default="99009002")
    parser.add_argument("--database-url-env", default="TEST_DATABASE_URL")
    parser.add_argument(
        "--with-business-data", action="store_true", help="企業2社と過去データ8表も作成"
    )
    parser.add_argument("--start-id", type=int, default=900001)
    parser.add_argument("--agreement-category", default="01")
    parser.add_argument("--energy-code", default="ELECTRICITY")
    parser.add_argument(
        "--schedule-date",
        type=date.fromisoformat,
        default=date.today() + timedelta(days=7),
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="データを投入する")
    action.add_argument(
        "--cleanup", action="store_true", help="作成したテストデータを削除"
    )
    action.add_argument(
        "--verify-stage",
        choices=("registered", "completed"),
        help="登録後・バッチ後を確認（参照のみ）",
    )
    args = parser.parse_args(argv)
    if args.verify_stage and not args.with_business_data:
        parser.error("--verify-stageには--with-business-dataが必要です。")
    for name in ("login_user_id", "from_user_id", "to_user_id"):
        if not re.fullmatch(r"[0-9A-Za-z]{1,8}", getattr(args, name)):
            parser.error(f"{name}は半角英数字1～8文字で指定してください。")
    for value in (args.from_org_id, args.to_org_id):
        if not re.fullmatch(r"[0-9A-Z]{1,20}", value):
            parser.error("組織IDは半角大文字英数字1～20文字で指定してください。")
    if len({args.login_user_id, args.from_user_id, args.to_user_id}) != 3:
        parser.error("ログイン用・引継元・引継先のユーザーIDは分けてください。")
    return args


def build_users(args: argparse.Namespace) -> list[dict]:
    return [
        {
            "user_id": user_id,
            "org_id": org_id,
            "user_name": f"引継画面テスト{label}",
            "email_address": f"handover-{user_id.lower()}@example.invalid",
            "company_name": "引継画面テスト",
            "user_role": "1",
            "delete_flg": False,
            "created_by": MARKER,
        }
        for user_id, org_id, label in (
            (args.from_user_id, args.from_org_id, "元担当"),
            (args.to_user_id, args.to_org_id, "先担当"),
        )
    ]


def _validate_organizations(
    connection: Connection, users: Table, orgs: Table, args: argparse.Namespace
) -> list[dict]:
    login = (
        connection.execute(
            select(users.c.org_id, users.c.user_role, orgs.c.org_type_code)
            .join(orgs, orgs.c.org_id == users.c.org_id)
            .where(
                users.c.user_id == args.login_user_id,
                users.c.delete_flg.is_(False),
                orgs.c.delete_flg.is_(False),
            )
        )
        .mappings()
        .one_or_none()
    )
    if login is None or (login["org_type_code"], login["user_role"]) not in {
        ("01", "0"),
        ("02", "9"),
    }:
        raise ValueError("有効なEP管理者または本店管理者を指定してください。")
    pending = []
    for org_id in sorted({args.from_org_id, args.to_org_id}):
        if login["org_type_code"] == "02" and (
            not re.match(r"BNK[0-9]{4}", login["org_id"])
            or not org_id.startswith(login["org_id"][:7])
        ):
            raise ValueError(
                "本店管理者が検索できる同一金融機関配下を指定してください。"
            )
        row = _organization_row(args, org_id, login["org_id"])
        stored = (
            connection.execute(select(orgs).where(orgs.c.org_id == org_id))
            .mappings()
            .first()
        )
        if args.create_organizations:
            if org_id == login["org_id"]:
                raise ValueError("ログイン組織とは別の新規組織IDを指定してください。")
            if stored is not None and any(
                stored[key] != value for key, value in row.items()
            ):
                raise ValueError(f"既存組織と衝突しています: {org_id}")
            if stored is None:
                pending.append(row)
        elif stored is None or stored["delete_flg"] is not False:
            raise ValueError(f"有効な既存組織がありません: {org_id}")
    return pending


def _organization_row(args: argparse.Namespace, org_id: str, login_org: str) -> dict:
    if args.create_organizations and args.org_type_code in {"02", "03"}:
        if not re.fullmatch(r"BNK[0-9]{4}[0-9A-Z]{1,13}", org_id):
            raise ValueError(
                "金融機関の新規組織IDはBNK＋銀行コード4桁＋支店識別子にしてください。"
            )
    return {
        "org_id": org_id,
        "org_name": f"引継画面テスト組織{org_id}",
        "company_name": "引継画面テスト",
        "org_type_code": args.org_type_code,
        "parent_org_id": login_org,
        "delete_flg": False,
        "created_by": MARKER,
    }


def _delete_organizations(
    connection: Connection, orgs: Table, args: argparse.Namespace
) -> None:
    ids = sorted({args.from_org_id, args.to_org_id})
    # FKが定義されていない業務テーブルもあるため、組織ID列の参照を検査する。
    inspector = inspect(connection)
    for name in inspector.get_table_names(schema="db_corp"):
        columns = [
            c["name"]
            for c in inspector.get_columns(name, schema="db_corp")
            if c["name"] == "org_id" or c["name"].endswith("_org_id")
        ]
        if name == orgs.name:
            columns.remove("org_id")
        if not columns:
            continue
        table = Table(name, MetaData(), schema="db_corp", autoload_with=connection)
        if connection.execute(
            select(table)
            .where(or_(*(table.c[column].in_(ids) for column in columns)))
            .limit(1)
        ).first():
            raise ValueError(f"組織が{name}で使用中です。削除せず終了します。")
    connection.execute(
        orgs.delete().where(orgs.c.org_id.in_(ids), orgs.c.created_by == MARKER)
    )


def _check_existing(connection: Connection, users: Table, rows: list[dict]) -> set[str]:
    existing_ids = set()
    for row in rows:
        existing = (
            connection.execute(
                select(users).where(
                    (users.c.user_id == row["user_id"])
                    | (users.c.email_address == row["email_address"])
                )
            )
            .mappings()
            .all()
        )
        for stored in existing:
            if any(stored[key] != value for key, value in row.items()):
                raise ValueError(f"既存データと衝突しています: {row['user_id']}")
            existing_ids.add(stored["user_id"])
    return existing_ids


def _check_unused(connection: Connection, metadata: MetaData, ids: list[str]) -> None:
    staff = Table("m_staff_info", metadata, schema="db_corp", autoload_with=connection)
    handover = Table(
        "t_sales_user_handover_info",
        metadata,
        schema="db_corp",
        autoload_with=connection,
    )
    assigned = connection.execute(
        select(staff.c.user_id).where(staff.c.user_id.in_(ids))
    ).first()
    planned = connection.execute(
        select(handover.c.handover_from_user_id).where(
            handover.c.handover_from_user_id.in_(ids)
            | handover.c.handover_to_user_id.in_(ids)
        )
    ).first()
    if assigned or planned:
        raise ValueError("担当者設定または引継予定で使用中です。削除せず終了します。")


def run(args: argparse.Namespace, engine: Engine) -> str:
    rows = build_users(args)
    with engine.begin() as connection:
        metadata = MetaData()
        users = Table("m_user", metadata, schema="db_corp", autoload_with=connection)
        orgs = Table(
            "m_user_organization_info",
            metadata,
            schema="db_corp",
            autoload_with=connection,
        )
        pending_orgs = _validate_organizations(connection, users, orgs, args)
        existing_ids = _check_existing(connection, users, rows)
        if args.verify_stage:
            return _business_data(connection, args)
        if args.cleanup:
            if args.with_business_data:
                _business_data(connection, args)
            ids = [row["user_id"] for row in rows]
            _check_unused(connection, metadata, ids)
            connection.execute(
                users.delete().where(
                    users.c.user_id.in_(ids), users.c.created_by == MARKER
                )
            )
            if args.create_organizations:
                _delete_organizations(connection, orgs, args)
            return "作成したテストデータを削除しました。"
        if args.apply:
            for row in pending_orgs:
                connection.execute(
                    orgs.insert().values(**row, created_at=datetime.now())
                )
            for row in rows:
                if row["user_id"] not in existing_ids:
                    connection.execute(
                        users.insert().values(
                            **row,
                            created_at=datetime.now(),
                            # 検索専用。ログイン用の既知パスワードは発行しない。
                            user_password=secrets.token_hex(32),
                        )
                    )
        business_summary = (
            _business_data(connection, args) if args.with_business_data else ""
        )
    mode = (
        "投入完了（既存の同一データは保持）" if args.apply else "確認のみ（DB変更なし）"
    )
    emails = "\n".join(row["email_address"] for row in rows)
    schedule = args.schedule_date.strftime("%Y/%m/%d")
    return f"{mode}\n引継元／先の検索メール:\n{emails}\n実施日: {schedule}\n{business_summary}"


def _business_data(connection: Connection, args: argparse.Namespace) -> str:
    # ファイル直接実行でもFlaskを起動せず既存バッチ用PGを再利用する。
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from cndx_corp_batch.test.handover_screen_business_data import prepare_business

    return prepare_business(connection, args)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    url = os.getenv(args.database_url_env)
    if not url:
        raise SystemExit(
            f"環境変数 {args.database_url_env} に検証DBのURLを設定してください。"
        )
    engine = create_engine(url, hide_parameters=True)
    try:
        print(run(args, engine))  # noqa: T201 - CLIの実行結果
    except ValueError as error:
        raise SystemExit(str(error)) from None
    except SQLAlchemyError:
        raise SystemExit(
            "DB処理に失敗しました。接続先・定義・制約を確認してください。"
        ) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
