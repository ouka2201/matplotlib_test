"""定期削除バッチの実行確認に使うDB行とZIPファイルを作成する。"""

import argparse
import json
import os
import sys
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import Boolean, Date, DateTime, Integer, MetaData, Numeric, String, Table, create_engine

from cndx_corp_batch.domains.periodic_delete import months_before


TABLES = (
    "t_user_power_report_mng_info",
    "t_power_report_mng_info",
    "t_ep_electricity_data_30min",
    "t_30min_import_mng",
    "t_co2_summary_report_mng_info",
    "t_historical_arve_customer_info",
)


def _required_values(table, values: dict, batch_at: datetime) -> dict:
    """テーブル定義にある必須列をテスト用の値で補う。

    Args:
        table: DBから取得したテーブル定義。
        values: 削除条件と主キーに使う値。
        batch_at: テストの基準日時。

    Returns:
        INSERTに渡す列名と値の対応。

    Raises:
        ValueError: 必須列の型に対応する値を作れない場合。
    """
    row = dict(values)
    for column in table.columns:
        if column.name in row or column.nullable or column.default is not None or column.server_default is not None:
            continue
        if column.primary_key and isinstance(column.type, Integer) and column.autoincrement in (True, "auto"):
            continue
        name = column.name.lower()
        if name == "created_by" or name == "updated_by":
            row[column.name] = "periodic_delete_test"
        elif name == "created_at" or name == "updated_at":
            row[column.name] = batch_at
        elif name == "create_status":
            row[column.name] = "3"
        elif isinstance(column.type, Boolean):
            row[column.name] = False
        elif isinstance(column.type, DateTime):
            row[column.name] = batch_at
        elif isinstance(column.type, Date):
            row[column.name] = batch_at.date()
        elif isinstance(column.type, (Integer, Numeric)):
            row[column.name] = 0
        elif isinstance(column.type, String):
            row[column.name] = "0"
        else:
            raise ValueError(f"必須列のテスト値を作れません: {table.name}.{column.name}")
    return row


def prepare(engine, output_dir: Path, batch_at: datetime, schema: str | None = "db_corp") -> Path:
    """期限切れと境界値の行をDBに登録し、対応するZIPを作る。

    Args:
        engine: テスト用DBへのSQLAlchemyエンジン。
        output_dir: ZIPとマニフェストを格納する親ディレクトリ。
        batch_at: 定期削除バッチに渡す基準日時。
        schema: テスト対象のスキーマ名。SQLiteの単体テストでは省略する。

    Returns:
        作成したマニフェストの絶対パス。

    Raises:
        ValueError: 必要なテーブルや列がない場合。
    """
    if batch_at.tzinfo is not None:
        raise ValueError("--batch-date にはタイムゾーンを含めないでください")
    metadata = MetaData()
    tables = {name: Table(name, metadata, autoload_with=engine, schema=schema) for name in TABLES}
    run_id = uuid.uuid4().hex[:12]
    folder = output_dir.resolve() / f"periodic_delete_{run_id}"
    folder.mkdir(parents=True, exist_ok=False)
    two_years = months_before(batch_at, 24)
    five_years = months_before(batch_at, 60)
    six_months = months_before(batch_at, 6)
    old_month_2 = months_before(two_years, 1).strftime("%Y%m")
    old_month_5 = months_before(five_years, 1).strftime("%Y%m")
    old_month_6 = months_before(six_months, 1).strftime("%Y%m")
    cutoff_24h = batch_at - timedelta(hours=24)
    point_token = str(int(run_id, 16)).zfill(15)
    cases = []
    created_files = []
    try:
        with engine.begin() as connection:
            for status in ("expired", "retained"):
                expired = status == "expired"
                point = ("99" + point_token + ("1" if expired else "2")).ljust(22, "0")
                zip_user = folder / f"user_{status}.zip"
                zip_co2 = folder / f"co2_{status}.zip"
                month_2 = old_month_2 if expired else two_years.strftime("%Y%m")
                month_5 = old_month_5 if expired else five_years.strftime("%Y%m")
                month_6 = old_month_6 if expired else six_months.strftime("%Y%m")
                day_5 = (five_years - timedelta(days=1) if expired else five_years).strftime("%Y%m%d")
                hour_24 = cutoff_24h - timedelta(seconds=1) if expired else cutoff_24h
                values_by_table = {
                    "t_user_power_report_mng_info": {
                        "file_name": zip_user.name, "file_path": str(zip_user),
                        "target_year_month": month_2, "org_id": f"PD{run_id[:8]}",
                    },
                    "t_power_report_mng_info": {
                        "supply_point_number": point, "target_year_month": month_2,
                    },
                    "t_ep_electricity_data_30min": {
                        "t01_kyo_ctn_tok_no": point, "t01_get_ymd": day_5,
                    },
                    "t_30min_import_mng": {
                        "supply_point_number": point, "target_year_month": month_5,
                    },
                    "t_co2_summary_report_mng_info": {
                        "creation_id": f"PD{run_id}{status[0]}", "org_id": f"PD{run_id[:8]}",
                        "file_name": zip_co2.name, "file_path": str(zip_co2),
                        "file_created_at": hour_24,
                    },
                    "t_historical_arve_customer_info": {
                        "cmn_supplypointspecificnum__c": point,
                        "acquisition_year_month": month_6,
                    },
                }
                for name, values in values_by_table.items():
                    table = tables[name]
                    unknown = set(values) - set(table.columns.keys())
                    if unknown:
                        raise ValueError(f"{name} に列がありません: {', '.join(sorted(unknown))}")
                    row = _required_values(table, values, batch_at)
                    result = connection.execute(table.insert().values(**row))
                    key = {col.name: row[col.name] if col.name in row else result.inserted_primary_key[index]
                           for index, col in enumerate(table.primary_key.columns)}
                    cases.append({"table": name, "status": status, "key": key, "cutoff_value": values.get(
                            "target_year_month", values.get("t01_get_ymd", values.get(
                                "file_created_at", values.get("acquisition_year_month"))))})
                for path in (zip_user, zip_co2):
                    created_files.append(path)
                    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                        archive.writestr("test.txt", f"periodic delete test: {status}\n")
            manifest = folder / "manifest.json"
            manifest.write_text(json.dumps({
                "batch_date": batch_at.isoformat(), "cases": cases,
                "zip_files": [str(path) for path in created_files],
            }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return manifest
    except Exception:
        for path in created_files:
            path.unlink(missing_ok=True)
        (folder / "manifest.json").unlink(missing_ok=True)
        folder.rmdir()
        raise


def main(argv=None) -> int:
    """コマンドライン引数を読み取り、テストデータを作成する。

    Args:
        argv: コマンドライン引数。省略時は実行時の引数を使う。

    Returns:
        正常終了時は0、作成に失敗した場合は1。
    """
    parser = argparse.ArgumentParser(description="定期削除バッチのテストデータ作成")
    parser.add_argument("--batch-date", type=datetime.fromisoformat, required=True,
                        help="バッチに渡す実行日時 (YYYY-MM-DDTHH:MM:SS)")
    parser.add_argument("--output-dir", type=Path, default=Path("output/periodic_delete_seed"),
                        help="ZIPを作成する親ディレクトリ")
    args = parser.parse_args(argv)
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        parser.error("DATABASE_URL を設定してください")
    engine = create_engine(db_url)
    try:
        manifest = prepare(engine, args.output_dir, args.batch_date)
        print(f"テストデータを作成しました: {manifest}")
        print(f"削除バッチ: python -m cndx_corp_batch.entrypoints.periodic_delete --batch-date {args.batch_date.isoformat()}")
        return 0
    except Exception as exc:
        print(f"テストデータの作成に失敗しました: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
