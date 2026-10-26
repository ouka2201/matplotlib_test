"""担当者引継ぎの単体テストケース1～78の初期データを準備する。"""

import argparse
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import DateTime, MetaData, String, Table, create_engine, select
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError

from cndx_corp_batch.domains.sales_user_handover.constants import (
    HANDOVER_STATUS_CANCELLED,
    HANDOVER_STATUS_DONE,
    HANDOVER_STATUS_ERROR,
    HANDOVER_STATUS_PLANNED,
    HANDOVER_TYPE_BULK,
    HANDOVER_TYPE_INDIVIDUAL,
)

from .insert_link_customer_30min_data import _column_map, _require_columns, _row

CATALOG = Path(__file__).with_name("sales_user_handover_cases.json")
BASE_DATE = date(2026, 10, 26)
TABLE_NAMES = {
    "corporate": "m_corporate_basic",
    "staff": "m_staff_info",
    "F": "m_building",
    "A": "t_monthly_building_energy_aggregation",
    "B": "t_annual_building_energy_aggregation",
    "C": "t_monthly_corporate_energy_aggregation",
    "D": "t_annual_corporate_energy_aggregation",
    "E": "t_report_storage_info",
    "G": "t_cn_application_info",
    "H": "t_building_info",
    "handover": "t_sales_user_handover_info",
}
HISTORY = "ABCDEFGH"
RANGE_CASES = {33: "A", 35: "B", 37: "C", 39: "D", 41: "E", 43: "F", 44: "G", 46: "H"}
MISSING_CASES = {34: "A", 36: "B", 38: "C", 40: "D", 42: "E", 45: "G", 47: "H"}
SPLIT_CASES = {
    56: ("HANDOVER_TO_ORG_ID", "O3"),
    57: ("HANDOVER_STATUS", HANDOVER_STATUS_DONE),
    58: ("HANDOVER_SCHEDULE_DATE", "20261027"),
}
FAULTS = {
    67: "実行日取得：get_current_timeに例外を注入（ジョブ生成前）。",
    68: "対象取得：select_sales_user_handover_targets.sqlの実行に例外を注入。",
    69: "担当者存在確認：select_handover_source_staff.sqlの実行に例外を注入。",
    70: "担当者更新：update_handover_staff.sqlの実行に例外を注入。",
    71: "引継情報削除：delete_invalid_sales_user_handover.sqlの実行に例外を注入。",
    72: "過去データ存在確認：check_handover_data.sqlの実行に例外を注入。",
    73: "過去データ更新：update_handover_cn_application.sqlの実行に例外を注入。",
    74: "完了更新：update_sales_user_handover_status.sqlの状態0更新に例外を注入。",
    75: "エラー更新：同SQLの状態3更新に例外を注入。再試行側も含むかを記録する。",
    76: "COMMIT：先頭法人のトランザクション確定に例外を注入。現在の実装は法人単位で確定する。",
}


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _audit():
    return {
        "CREATED_BY": "handover_test_seed",
        "CREATED_AT": datetime(2026, 1, 1),
        "UPDATED_BY": None,
        "UPDATED_AT": None,
    }


def build_plan(
    case_id,
    start_id=None,
    *,
    variant=None,
    handover_type=None,
    identifiers=None,
    agreement_category="01",
    energy_code="ELECTRICITY",
):
    """DBに接続せず投入行と、データだけでは再現できない操作を返す。"""
    catalog = load_catalog()
    case = next((c for c in catalog["cases"] if c["case_id"] == str(case_id)), None)
    if case is None:
        raise ValueError("ケースIDは1～78を指定してください。")
    number = case["number"]
    if number in SPLIT_CASES:
        if variant not in ("target", "comparison"):
            raise ValueError(
                "ケース56～58は主キーが重複するため--variant target/comparisonが必要です。"
            )
    elif variant is not None:
        raise ValueError("--variantはケース56～58だけに指定できます。")
    first = number * 1000 + 1 if start_id is None else start_id
    if (
        not isinstance(first, int)
        or isinstance(first, bool)
        or not 1 <= first <= 999700
    ):
        raise ValueError("start-idは1～999700の整数を指定してください。")
    ids = {
        f"{prefix}{i}": f"{prefix}{first:06d}{i}"
        for prefix in ("O", "U")
        for i in (1, 2, 3)
    }
    if identifiers:
        if set(identifiers) - set(ids):
            raise ValueError("identifiersのキーはO1/O2/O3/U1/U2/U3です。")
        ids.update(identifiers)
    for name, value in ids.items():
        limit = 8 if name.startswith("U") else 20
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(
                f"{name}は空白でない{limit}文字以内の文字列を指定してください。"
            )
    if (
        len({ids[k] for k in ("U1", "U2", "U3")}) != 3
        or len({ids[k] for k in ("O1", "O2", "O3")}) != 3
    ):
        raise ValueError(
            "元・先・比較用のユーザーIDと組織IDはそれぞれ異なる値が必要です。"
        )
    if handover_type is None:
        handover_type = (
            HANDOVER_TYPE_BULK if number in (61, 62) else HANDOVER_TYPE_INDIVIDUAL
        )
    if handover_type not in (HANDOVER_TYPE_INDIVIDUAL, HANDOVER_TYPE_BULK):
        raise ValueError(
            'handover-typeは"0"（個別）または"1"（一括）を指定してください。'
        )
    for name, value, limit in (
        ("agreement_category", agreement_category, 2),
        ("energy_code", energy_code, 20),
    ):
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(
                f"{name}は空白でない{limit}文字以内の文字列を指定してください。"
            )
    batch_date = {
        2: BASE_DATE - timedelta(days=1),
        4: date(2026, 10, 31),
        5: date(2027, 1, 1),
        6: date(2028, 2, 29),
        53: BASE_DATE - timedelta(days=1),
    }.get(number, BASE_DATE)
    rows = {key: [] for key in TABLE_NAMES}
    notes = []
    actions = []
    corporations = {}

    def corp(index=1):
        value = str(9900000000000 + first + index - 1)
        corporations[f"C{index}"] = value
        return value

    def staff(index=1, user="U1", org="O1"):
        rows["staff"].append(
            {
                "CORPORATE_NUMBER": corp(index),
                "AGREEMENT_CATEGORY": agreement_category,
                "ORG_ID": ids[org],
                "USER_ID": ids[user],
                "CONSENT_RECEIPT_DATE": "20260101",
                "DELETE_FLG": False,
                **_audit(),
            }
        )

    def target(index=1, **changes):
        row = {
            "CORPORATE_NUMBER": corp(index),
            "HANDOVERED_AT": None,
            "HANDOVER_SCHEDULE_DATE": batch_date.strftime("%Y%m%d"),
            "REPORT_DATA_FLG": False,
            "HANDOVER_FROM_ORG_ID": ids["O1"],
            "HANDOVER_FROM_USER_ID": ids["U1"],
            "HANDOVER_TO_ORG_ID": ids["O2"],
            "HANDOVER_TO_USER_ID": ids["U2"],
            "HANDOVER_STATUS": HANDOVER_STATUS_PLANNED,
            "HANDOVER_TYPE": handover_type,
            "CREATOR_ID": ids["U1"],
            "CREATOR_ORG_ID": ids["O1"],
            "INSERT_DATETIME": datetime(2026, 10, 26, 0, 30),
            **_audit(),
        }
        row["UPDATED_AT"] = datetime(2026, 10, 26, 0, 30)
        row.update(changes)
        rows["handover"].append(row)
        return row

    def history(key, index=1, org="O1", detail=1):
        corporate = corp(index)
        row = {
            "CORPORATE_NUMBER": corporate,
            "AGREEMENT_CATEGORY": agreement_category,
            "ORG_ID": ids[org],
            "DELETE_FLG": False,
            **_audit(),
        }
        if key in "ABEFH":
            row["BUILDING_ID"] = corporate + f"HT{detail:03d}"
        if key in "ABCDGH":
            row.update(FISCAL_YEAR="2025", REGISTRATION_SEQ=detail)
        if key in "ABCD":
            row.update(ENERGY_CODE=energy_code, ENERGY_QUANTITY=100 + detail)
            row["TARGET_YEAR_MONTH" if key in "AC" else "TARGET_YEAR"] = (
                "202509" if key in "AC" else "2025"
            )
        if key in "AB":
            row.update(SUPPLIER_REG_NO="0", BUILDING_NAME=f"引継テスト建物{detail}")
        if key == "A":
            row["SUPPLY_MENU"] = "引継テストメニュー"
        if key == "E":
            row.update(
                CREATION_ID=f"HT_{corporate}_{detail}",
                REPORT_CLASSIFY="6",
                FISCAL_YEAR="2025",
                REGISTRATION_SEQ=detail,
                REPORT_SAVE_PATH=f"test/handover/{corporate}/{detail}.pdf",
            )
        if key == "F":
            row.update(AGREEMENT_ORG=ids[org], BUILDING_NAME=f"引継テスト建物{detail}")
        if key == "G":
            row["COMPANY_NAME"] = f"引継テスト企業{index}"
        if key == "H":
            row["LOCATION_IDENTIFIER_NAME"] = f"引継テスト拠点{detail}"
        rows[key].append(row)
        return row

    def all_history(index=1, exclude=""):
        for key in HISTORY:
            if key not in exclude:
                history(key, index)

    # 基準データは1法人。各分岐でケース表の差分だけを適用する。
    staff()
    main = target()
    if number == 3:
        rows["handover"].clear()
    elif number == 2:
        staff(2)
        target(2, HANDOVER_SCHEDULE_DATE=BASE_DATE.strftime("%Y%m%d"))
    elif number in (4, 5, 6):
        main["INSERT_DATETIME"] = datetime.combine(
            batch_date, datetime.min.time()
        ).replace(minute=30)
        main["UPDATED_AT"] = main["INSERT_DATETIME"]
        for i, offset in enumerate((-1, 1), 2):
            staff(i)
            target(
                i,
                HANDOVER_SCHEDULE_DATE=(batch_date + timedelta(days=offset)).strftime(
                    "%Y%m%d"
                ),
                INSERT_DATETIME=main["INSERT_DATETIME"],
                UPDATED_AT=main["UPDATED_AT"],
            )
    elif number in (8, 9, 64):
        main["HANDOVER_STATUS"] = (
            HANDOVER_STATUS_DONE if number == 8 else HANDOVER_STATUS_ERROR
        )
        main["HANDOVERED_AT"] = datetime(2026, 10, 26, 0, 45)
    elif number in (10, 11):
        main["HANDOVER_SCHEDULE_DATE"] = (
            BASE_DATE + timedelta(days=-1 if number == 10 else 1)
        ).strftime("%Y%m%d")
    elif number == 12:
        for i, (status, offset) in enumerate(
            (
                (HANDOVER_STATUS_DONE, 0),
                (HANDOVER_STATUS_ERROR, 0),
                (HANDOVER_STATUS_PLANNED, -1),
                (HANDOVER_STATUS_PLANNED, 1),
                (HANDOVER_STATUS_CANCELLED, 0),
            ),
            2,
        ):
            staff(i)
            target(
                i,
                HANDOVER_STATUS=status,
                HANDOVER_SCHEDULE_DATE=(BASE_DATE + timedelta(days=offset)).strftime(
                    "%Y%m%d"
                ),
            )
    elif number in (13, 14, 15):
        for i in (2, 3):
            staff(i)
            target(i)
        for i, row in enumerate(rows["handover"]):
            row["INSERT_DATETIME"] = datetime(
                2026, 10, 26, 0, (20, 10, 30)[i] if number == 13 else 5
            )
            row["UPDATED_AT"] = datetime(
                2026,
                10,
                26,
                0,
                (30, 20, 10)[i]
                if number == 13
                else (20, 10, 30)[i]
                if number == 14
                else 30,
            )
    elif 16 <= number <= 19:
        main["INSERT_DATETIME"] = datetime.fromisoformat(
            "2026-10-26T"
            + ("00:58:59", "00:59:00", "00:59:59", "01:00:00")[number - 16]
        )
        notes.append(
            "現在の対象取得SQLには登録締切条件がない。Q01の期待結果を確認する。"
        )
    elif number in (21, 60):
        staff(2)
        if number == 60:
            all_history(1)
            all_history(2)
    elif number == 22:
        staff(user="U3")
    elif number == 24:
        staff(user="U2", org="O2")
    elif number in (25, 26, 27, 65):
        rows["staff"].clear()
        if number == 26:
            staff(2, user="U3")
            target(2, HANDOVER_FROM_USER_ID=ids["U3"])
        if number == 27:
            staff(2)
    elif number == 28:
        all_history()
    elif number == 30:
        main["REPORT_DATA_FLG"] = True
        all_history()
    elif number == 31:
        main["REPORT_DATA_FLG"] = True
        history("F")
    elif number == 32:
        main["REPORT_DATA_FLG"] = None
        all_history()
    elif number in RANGE_CASES:
        main["REPORT_DATA_FLG"] = True
        key = RANGE_CASES[number]
        if key != "F":
            history("F")
        for index, org, detail in (
            (1, "O1", 1),
            (1, "O1", 2),
            (1, "O3", 3),
            (2, "O1", 4),
            (1, "O2", 5),
        ):
            history(key, index, org, detail)
    elif number in MISSING_CASES:
        main["REPORT_DATA_FLG"] = True
        all_history(exclude=MISSING_CASES[number])
    elif number == 48:
        main["REPORT_DATA_FLG"] = True
        history("F")
        history("F", org="O3", detail=2)["ORG_ID"] = ids["O1"]
    elif number in (49, 50, 51, 78):
        main["REPORT_DATA_FLG"] = True
        if number != 51:
            all_history(exclude="F")
        if number == 50:
            history("F", org="O3")
    elif 54 <= number <= 59:
        if number == 54:
            target(2)
        elif number == 55:
            target(HANDOVER_FROM_ORG_ID=ids["O3"])
        elif number in SPLIT_CASES:
            if variant == "comparison":
                field, value = SPLIT_CASES[number]
                main[field] = ids.get(value, value)
            notes.append(
                "主キー(CORPORATE_NUMBER, HANDOVER_FROM_ORG_ID, HANDOVER_FROM_USER_ID)が同じになるため2行同時投入は不可。target/comparisonを別々に初期化して実施する。"
            )
        else:
            target(HANDOVER_FROM_USER_ID=ids["U3"], HANDOVER_TO_USER_ID=ids["U1"])
        actions.append(
            "バッチ全体ではなく、C1/O1/U1→O2/U2をパラメータとして状態更新処理10・12を個別実行する。毎回データを復元する。"
        )
    elif number in (61, 62):
        for i in range(2, 301 if number == 62 else 4):
            staff(i)
            target(i)
        if number == 61:
            for i, row in enumerate(rows["handover"], 1):
                row["REPORT_DATA_FLG"] = i != 2
                all_history(i)
    elif number == 66 or number in FAULTS:
        if number != 76:
            staff(2)
            target(2, INSERT_DATETIME=datetime(2026, 10, 26, 0, 40))
        if number == 71:
            rows["staff"] = [
                r for r in rows["staff"] if r["CORPORATE_NUMBER"] != corp()
            ]
            rows["staff"][0]["USER_ID"] = ids["U3"]
            rows["handover"][1]["HANDOVER_FROM_USER_ID"] = ids["U3"]
        if number in (66, 72, 73, 75, 76):
            main["REPORT_DATA_FLG"] = True
            all_history(exclude="F" if number in (66, 75) else "")
        if number == 66:
            rows["handover"][1]["REPORT_DATA_FLG"] = True
            all_history(2)

    if number in (63, 65):
        actions.append(
            "この計画は初回実行前のデータ。バッチを1回実行し結果を保存後、データを再投入せず同日で2回目を実行する。"
        )
    if number in FAULTS:
        actions.append(FAULTS[number])
        actions.append(
            "投入PGは障害注入を実行しない。スタブ／デバッガ設定後にバッチを実行する。"
        )
    if number in (1, 67):
        actions.append("日付引数を付けず、テスト用時計の当日を2026-10-26に固定する。")
    for corporate in corporations.values():
        rows["corporate"].append(
            {
                "CORPORATE_NUMBER": corporate,
                "COMPANY_NAME": f"引継テスト{corporate}",
                "DELETE_FLG": False,
                **_audit(),
            }
        )
    notes.append(
        "利用者・組織・エネルギーの参照マスタは自動生成しない。FK制約がある環境では設定identifiers・agreement_category・energy_codeを既存テストマスタと対応させる。"
    )
    command = "python -m cndx_corp_batch.entrypoints.sales_user_handover_batch"
    if number not in (1, 67):
        command += f" --batch-date {batch_date.isoformat()}"
    return {
        "source": catalog["source"],
        "sheet": catalog["sheet"],
        **case,
        "variant": variant,
        "start_id": first,
        "batch_date": batch_date.isoformat(),
        "clock_date": BASE_DATE.isoformat(),
        "identifiers": {**corporations, **ids},
        "handover_kind": "bulk"
        if handover_type == HANDOVER_TYPE_BULK
        else "individual",
        "batch_command": command,
        "batch_environment": {"TZ": "Asia/Tokyo", "BATCH_NAME": "BLMMGMGHANDOVER"},
        "execution_scope": "status_update_only" if 54 <= number <= 59 else "batch",
        "fault_injection": FAULTS.get(number),
        "manual_actions": actions,
        "notes": notes,
        "rows": rows,
    }


def insert_plan(settings, plan):
    """既存行を変更せず、投入データ全件を1トランザクションで登録する。"""
    for row in plan["rows"]["handover"]:
        if row["HANDOVER_TYPE"] not in (HANDOVER_TYPE_INDIVIDUAL, HANDOVER_TYPE_BULK):
            raise ValueError('HANDOVER_TYPEは"0"（個別）または"1"（一括）が必要です。')
        if row["HANDOVER_STATUS"] not in (
            HANDOVER_STATUS_DONE,
            HANDOVER_STATUS_PLANNED,
            HANDOVER_STATUS_CANCELLED,
            HANDOVER_STATUS_ERROR,
        ):
            raise ValueError(
                'HANDOVER_STATUSは"0"（完了）、"1"（予定）、"2"（引継中止）、"3"（登録エラー）が必要です。'
            )
    url = settings.get("url") or os.getenv(
        settings.get("url_env", "REPORT_DATABASE_URL")
    )
    if not url:
        raise ValueError(
            "DB接続先がありません。設定urlまたはurl_envの環境変数を指定してください。"
        )
    engine = create_engine(url, hide_parameters=True)
    try:
        with engine.begin() as connection:
            metadata = MetaData()
            tables = {}
            schema = settings.get("schema", "db_corp")
            for key, default_name in TABLE_NAMES.items():
                name = settings.get("tables", {}).get(key, default_name)
                qualified_name = f"{schema}.{name}" if schema else name
                try:
                    tables[key] = Table(
                        name, metadata, schema=schema, autoload_with=connection
                    )
                except NoSuchTableError as exc:
                    # NoSuchTableErrorの引数はテーブル識別子。接続URLは出力しない。
                    missing = str(exc) or qualified_name
                    raise ValueError(
                        f"NoSuchTableError: テーブルが存在しないか、接続ユーザーから参照できません。"
                        f"\n見つからないテーブル: {missing}"
                        f"\n定義取得対象: {qualified_name}（設定キー: tables.{key}）"
                        "\n接続先DB、schema、テーブル名の大文字・小文字、参照権限を確認してください。"
                        "\n未作成の場合は検証DBに正式なDDLを適用してください。データは投入していません。"
                    ) from exc
            handover = tables["handover"]
            columns = _column_map(handover)
            _require_columns(
                handover,
                ("HANDOVER_STATUS", "HANDOVER_SCHEDULE_DATE", "HANDOVER_FROM_USER_ID"),
            )
            pending = (
                select(handover)
                .where(
                    handover.c[columns["HANDOVER_STATUS"]] == HANDOVER_STATUS_PLANNED,
                    handover.c[columns["HANDOVER_SCHEDULE_DATE"]]
                    == plan["batch_date"].replace("-", ""),
                )
                .limit(1)
            )
            if connection.execute(pending).first():
                raise ValueError(
                    "実行日の未処理予定が既に存在します。ケース専用の検証DBを初期化してください。"
                )
            corporations = [
                v for k, v in plan["identifiers"].items() if k.startswith("C")
            ]
            prepared = []
            for key, table in tables.items():
                _require_columns(table, ("CORPORATE_NUMBER",))
                column_names = _column_map(table)
                if (
                    corporations
                    and connection.execute(
                        select(table)
                        .where(
                            table.c[column_names["CORPORATE_NUMBER"]].in_(corporations)
                        )
                        .limit(1)
                    ).first()
                ):
                    raise ValueError(
                        f"{table.name}に同じ法人番号の既存行があります。再投入せず初期状態を確認してください。"
                    )
                # 他法人の同一U1も、全法人での不在判定や一括引継ぎの条件を変える。
                if key == "staff":
                    _require_columns(table, ("USER_ID",))
                    if connection.execute(
                        select(table)
                        .where(
                            table.c[column_names["USER_ID"]]
                            == plan["identifiers"]["U1"]
                        )
                        .limit(1)
                    ).first():
                        raise ValueError(
                            "引継元ユーザーIDが既存担当者情報に存在します。専用のテストIDを使用してください。"
                        )
                keys = list(table.primary_key.columns)
                if not keys:
                    raise ValueError(
                        f"{table.name}に主キーがありません。DB定義を確認してください。"
                    )
                seen = set()
                for values in plan["rows"][key]:
                    _require_columns(table, tuple(values))
                    row = _row(table, values)
                    for column in table.c:
                        value = row.get(column.name)
                        if (
                            value is None
                            and not column.nullable
                            and (
                                column.name in row
                                or (
                                    column.server_default is None
                                    and column.identity is None
                                )
                            )
                        ):
                            raise ValueError(
                                f"{table.name}.{column.name}はNOT NULLです。必要な値・DB定義を確認してください。"
                            )
                        if (
                            isinstance(value, str)
                            and isinstance(column.type, String)
                            and column.type.length
                            and len(value) > column.type.length
                        ):
                            raise ValueError(
                                f"{table.name}.{column.name}の文字数が列長を超えます。"
                            )
                        if isinstance(value, datetime) and not isinstance(
                            column.type, DateTime
                        ):
                            raise TypeError(
                                f"{table.name}.{column.name}は想定したTIMESTAMP型ではありません。"
                            )
                    if any(c.name not in row for c in keys):
                        raise ValueError(
                            f"{table.name}の主キー列が投入データにありません。"
                        )
                    identity = tuple(row[c.name] for c in keys)
                    if identity in seen:
                        raise ValueError(
                            f"{table.name}の投入計画内で主キーが重複します。"
                        )
                    seen.add(identity)
                    if connection.execute(
                        select(table).where(*(c == row[c.name] for c in keys)).limit(1)
                    ).first():
                        raise ValueError(f"{table.name}に同じ主キーが既に存在します。")
                    prepared.append((table, row))
            for table, row in prepared:
                connection.execute(table.insert(), row)
        return {key: len(rows) for key, rows in plan["rows"].items()}
    finally:
        engine.dispose()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="ケース一覧")
    parser.add_argument("--case", help="Excelの項番1～78")
    parser.add_argument(
        "--start-id", type=int, help="識別番号の開始値（既定：ケース番号×1000+1）"
    )
    parser.add_argument(
        "--variant", choices=("target", "comparison"), help="ケース56～58のデータ種別"
    )
    parser.add_argument(
        "--handover-type",
        choices=("0", "1"),
        help="引継種別：0=個別、1=一括。省略時はケースに合わせる",
    )
    parser.add_argument(
        "--db-config", type=Path, help="DB設定JSON。url/url_env、schemaは既存PGと共通"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="DB接続せず投入計画だけを作成"
    )
    parser.add_argument(
        "--output", type=Path, help="全投入行・追加操作を含む計画JSONの保存先"
    )
    args = parser.parse_args(argv)
    if args.list:
        for case in load_catalog()["cases"]:
            extra = " [--variant必須]" if case["number"] in SPLIT_CASES else ""
            print(f"{case['case_id']:>2}  {case['title']}{extra}")
        return 0
    if not args.case:
        parser.error("--caseまたは--listを指定してください。")
    if not args.dry_run and not args.db_config:
        parser.error(
            "投入時は--db-configが必要です。確認だけの場合は--dry-runを指定してください。"
        )
    try:
        settings = (
            json.loads(args.db_config.read_text(encoding="utf-8-sig"))
            if args.db_config
            else {}
        )
        kind = "bulk" if args.case in ("61", "62") else "individual"
        plan = build_plan(
            args.case,
            args.start_id,
            variant=args.variant,
            handover_type=(
                args.handover_type
                if args.handover_type is not None
                else settings.get("handover_types", {}).get(kind)
            ),
            identifiers=settings.get("identifiers"),
            agreement_category=settings.get("agreement_category", "01"),
            energy_code=settings.get("energy_code", "ELECTRICITY"),
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
        summary = {
            key: value
            for key, value in plan.items()
            if key not in ("rows", "identifiers")
        }
        summary["planned_counts"] = {
            key: len(rows) for key, rows in plan["rows"].items()
        }
        summary["mode"] = "dry-run" if args.dry_run else "insert"
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        if not args.dry_run:
            counts = insert_plan(settings, plan)
            print("投入完了: " + json.dumps(counts, ensure_ascii=False))
    except (ValueError, TypeError, OSError) as exc:
        parser.exit(1, f"準備失敗: {exc}\n")
    except SQLAlchemyError as exc:
        # 接続文字列やDBAPI例外に含まれる認証情報をコンソールに出さない。
        parser.exit(
            1,
            f"DB準備失敗（{type(exc).__name__}）。接続先・列定義・参照マスタ・制約を確認してください。投入トランザクションは確定していません。\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
