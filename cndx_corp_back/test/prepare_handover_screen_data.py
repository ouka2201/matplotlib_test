"""担当者検索から引継確認モーダルまでの操作用データを準備する。"""

import argparse
import os
import re
import secrets
from datetime import date, datetime, timedelta

from sqlalchemy import Connection, Engine, MetaData, Table, create_engine, select
from sqlalchemy.exc import SQLAlchemyError

MARKER = "handover_screen_seed"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login-user-id", required=True, help="既存の検証用管理者ID")
    parser.add_argument("--from-org-id", required=True, help="既存の引継元組織ID")
    parser.add_argument("--to-org-id", required=True, help="既存の引継先組織ID")
    parser.add_argument("--from-user-id", default="99009001")
    parser.add_argument("--to-user-id", default="99009002")
    parser.add_argument("--database-url-env", default="TEST_DATABASE_URL")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="データを投入する")
    action.add_argument("--cleanup", action="store_true", help="作成した担当者のみ削除")
    args = parser.parse_args(argv)
    for name in ("login_user_id", "from_user_id", "to_user_id"):
        if not re.fullmatch(r"[0-9A-Z]{1,8}", getattr(args, name)):
            parser.error(f"{name}は半角大文字英数字1～8文字で指定してください。")
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
) -> None:
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
    for org_id in {args.from_org_id, args.to_org_id}:
        org = connection.execute(
            select(orgs).where(
                orgs.c.org_id == org_id,
                orgs.c.delete_flg.is_(False),
            )
        ).first()
        if org is None:
            raise ValueError(f"有効な既存組織がありません: {org_id}")
        if login["org_type_code"] == "02" and (
            not re.match(r"BNK[0-9]{4}", login["org_id"])
            or not org_id.startswith(login["org_id"][:7])
        ):
            raise ValueError(
                "本店管理者が検索できる同一金融機関配下を指定してください。"
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
        _validate_organizations(connection, users, orgs, args)
        existing_ids = _check_existing(connection, users, rows)
        if args.cleanup:
            ids = [row["user_id"] for row in rows]
            _check_unused(connection, metadata, ids)
            connection.execute(
                users.delete().where(
                    users.c.user_id.in_(ids), users.c.created_by == MARKER
                )
            )
            return "作成したテスト担当者を削除しました。"
        if args.apply:
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
    mode = (
        "投入完了（既存の同一データは保持）" if args.apply else "確認のみ（DB変更なし）"
    )
    emails = "\n".join(row["email_address"] for row in rows)
    schedule = (date.today() + timedelta(days=7)).strftime("%Y/%m/%d")
    return f"{mode}\n引継元／先の検索メール:\n{emails}\n実施日の例: {schedule}"


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
