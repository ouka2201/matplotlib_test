"""定期削除の投入PGが削除対象と残存対象を作れることを確認する。"""

import json
import zipfile
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, select

from cndx_corp_batch.domains.periodic_delete.jobs.prepare_periodic_delete_data_job import prepare


def test_prepare_creates_expired_and_retained_rows_and_zip_files(tmp_path):
    """六つのテーブルと四つのZIPに境界値の両側を用意する。

    Args:
        tmp_path: SQLite DBとZIPを置く一時ディレクトリ。
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'seed.db'}")
    metadata = MetaData()
    tables = {
        "t_user_power_report_mng_info": Table("t_user_power_report_mng_info", metadata,
            Column("file_id", Integer, primary_key=True), Column("file_name", String),
            Column("file_path", String), Column("target_year_month", String), Column("org_id", String)),
        "t_power_report_mng_info": Table("t_power_report_mng_info", metadata,
            Column("supply_point_number", String, primary_key=True),
            Column("target_year_month", String, primary_key=True)),
        "t_ep_electricity_data_30min": Table("t_ep_electricity_data_30min", metadata,
            Column("t01_kyo_ctn_tok_no", String, primary_key=True),
            Column("t01_get_ymd", String, primary_key=True),
            Column("t01_30t_syr01", String, nullable=False)),
        "t_30min_import_mng": Table("t_30min_import_mng", metadata,
            Column("supply_point_number", String, primary_key=True),
            Column("target_year_month", String, primary_key=True)),
        "t_co2_summary_report_mng_info": Table("t_co2_summary_report_mng_info", metadata,
            Column("creation_id", String, primary_key=True), Column("org_id", String, primary_key=True),
            Column("file_name", String), Column("file_path", String),
            Column("file_created_at", DateTime)),
        "t_historical_arve_customer_info": Table("t_historical_arve_customer_info", metadata,
            Column("cmn_supplypointspecificnum__c", String, primary_key=True),
            Column("acquisition_year_month", String, primary_key=True)),
    }
    metadata.create_all(engine)
    try:
        manifest_path = prepare(engine, tmp_path / "files", datetime(2026, 11, 17, 2), schema=None)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(manifest["cases"]) == 12
        assert {case["status"] for case in manifest["cases"]} == {"expired", "retained"}
        by_table = {(case["table"], case["status"]): case for case in manifest["cases"]}
        assert by_table["t_user_power_report_mng_info", "expired"]["cutoff_value"] == "202410"
        assert by_table["t_user_power_report_mng_info", "retained"]["cutoff_value"] == "202411"
        assert by_table["t_ep_electricity_data_30min", "expired"]["cutoff_value"] == "20211116"
        assert by_table["t_ep_electricity_data_30min", "retained"]["cutoff_value"] == "20211117"
        with engine.connect() as connection:
            for table in tables.values():
                assert len(connection.execute(select(table)).all()) == 2
        for filename in manifest["zip_files"]:
            with zipfile.ZipFile(filename) as archive:
                assert archive.read("test.txt").startswith(b"periodic delete test:")
        assert len(manifest["zip_files"]) == 4
    finally:
        engine.dispose()
