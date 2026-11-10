"""画面・APIのExcel項番を既存データ準備PGのDB条件に対応させる。"""

import argparse
import importlib.util
import json
import os
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError


CATALOG = Path(__file__).with_name("api_screen_case_catalog.json")
PER30 = {"api02", "data30_screen"}
CORPORATION = {"api04", "corp_screen"}
HANDOVER = {"api05", "api06", "staff_screen", "handover_screen"}


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def profile(suite, number):
    if suite == "api02":
        return "no-data" if number == 6 else "two-buildings" if number in (5, 7, 8) else "base"
    if suite == "data30_screen":
        return "no-data" if number == 5 else "two-buildings" if number in (4, 6) else "base"
    if suite == "api04":
        return "absent" if number == 5 else "two-corporations" if number == 7 else "base"
    if suite == "corp_screen":
        return "absent" if number == 5 else "two-corporations" if number == 6 else "base"
    if suite == "staff_screen":
        return "users"
    if suite == "handover_screen":
        return "users" if number == 5 else "business"
    if suite in ("api05", "api06"):
        return "existing-handover" if number == 6 else "business"
    raise ValueError(f"不明なテスト表: {suite}")


def _seed_module(suite):
    name = ("prepare_per_30min_data" if suite in PER30 else
            "prepare_corporation_30min_screen_data" if suite in CORPORATION else
            "prepare_handover_screen_data")
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(suite, argv=None):
    catalog = load_catalog()[suite]
    parser = argparse.ArgumentParser(description=f"{catalog['source']} の項番別データ準備")
    parser.add_argument("--list", action="store_true", help="項番・条件を表示")
    parser.add_argument("--case", type=int, help="Excelの項番")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="初回の準備")
    action.add_argument("--reset", action="store_true", help="ケースの初期状態へ再設定")
    action.add_argument("--cleanup", action="store_true", help="準備データを削除")
    args, seed_cli = parser.parse_known_args(argv)
    if args.list:
        for case in catalog["cases"]:
            print(f"{case['number']:>2}  {case['condition']}  [{profile(suite, case['number'])}]")
        return 0
    case = next((item for item in catalog["cases"] if item["number"] == args.case), None)
    if case is None:
        parser.error("有効なExcel項番を--caseで指定してください。--listで確認できます。")
    fixture = profile(suite, args.case)
    seed = _seed_module(suite)
    if suite in PER30:
        seed_cli += ["--case", fixture]
        if args.cleanup:
            seed_cli.append("--cleanup")
        elif args.apply or args.reset:
            seed_cli.append("--apply")
    else:
        if args.cleanup:
            seed_cli.append("--cleanup")
        elif args.reset:
            seed_cli.append("--reset")
        elif args.apply:
            seed_cli.append("--apply")
    if suite in HANDOVER:
        if fixture != "users":
            seed_cli.append("--with-business-data")
        if suite in ("api05", "api06"):
            seed_cli += ["--handover-type", "0" if suite == "api05" else "1"]
        if fixture == "existing-handover":
            seed_cli.append("--existing-handover")
    try:
        seed_args = seed.parse_args(seed_cli)
        if fixture == "two-corporations":
            seed_args.count = 2
        if fixture == "absent" and (args.apply or args.reset):
            seed_args.apply = False
            seed_args.reset = False
            seed_args.cleanup = True
        url = os.getenv(seed_args.database_url_env)
        if not url:
            raise ValueError(f"環境変数 {seed_args.database_url_env} に検証DBのURLを設定してください。")
        engine = seed.create_engine(url)
        try:
            result = seed.run(seed_args, engine)
            if fixture == "absent":
                seed_args.cleanup = False
                result += "\n" + seed.run(seed_args, engine)
        finally:
            engine.dispose()
        print(f"{suite} 項番{case['number']}: {case['condition']} / DB条件={fixture}")
        print(result)
        print(f"テスト手順: {case['procedure']}")
        return 0
    except (ValueError, OSError, SQLAlchemyError) as exc:
        parser.exit(1, f"ケース{case['number']}の準備失敗: {exc}\n")
