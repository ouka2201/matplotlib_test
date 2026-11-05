"""画面からAPI-04へ渡す前のマスタ・EP・ARVEデータを確認する。"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import (
    Boolean, Column, DateTime, Integer, MetaData, Numeric, String,
    Table, create_engine, select, text,
)

from cndx_corp_back.query.corporation_30min_query import INSERT_CORPORATION_30MIN
from cndx_corp_back.test.prepare_corporation_30min_screen_data import MARKER, parse_args, run


DAY = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")


@pytest.fixture
def database():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS db_corp")
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS db_common")
        meta = MetaData(schema="db_corp")
        Table("m_corporate_basic", meta,
              Column("corporate_number", String, primary_key=True), Column("company_name", String),
              Column("company_name_kana", String), Column("company_address_prefecture", String),
              Column("company_address_city", String), Column("delete_flg", Boolean),
              Column("created_by", String), Column("created_at", DateTime))
        Table("m_corporate_details_info", meta,
              Column("corporate_number", String, primary_key=True),
              Column("agreement_category", String, primary_key=True),
              Column("org_id", String, primary_key=True), Column("business_office_count", Integer),
              Column("delete_flg", Boolean), Column("created_by", String), Column("created_at", DateTime))
        Table("m_user_organization_info", meta,
              Column("org_id", String, primary_key=True), Column("org_name", String),
              Column("org_type_code", String), Column("org_type", String),
              Column("business_type", String), Column("delete_flg", Boolean),
              Column("created_by", String), Column("created_at", DateTime))
        Table("m_building", meta,
              Column("corporate_number", String, primary_key=True),
              Column("agreement_category", String, primary_key=True),
              Column("org_id", String, primary_key=True), Column("building_id", String, primary_key=True),
              Column("location_identifier_name", String), Column("building_name", String),
              Column("building_address_prefecture", String), Column("building_address_city", String),
              Column("agreement_org", String), Column("ep_office_code", String),
              Column("ep_customer_number", String), Column("supply_point_number", String),
              Column("delete_flg", Boolean), Column("created_by", String), Column("created_at", DateTime))
        ep_columns = [Column("t01_kyo_ctn_tok_no", String), Column("t01_get_ymd", String),
                      Column("t01_kskj_ksu", String), Column("t01_fsij_ksu", String)]
        ep_columns += [Column(f"t01_30t_syr{i:02d}", String) for i in range(1, 49)]
        Table("t_ep_electricity_data_30min", meta, *ep_columns)
        Table("t_arve_customer_info", meta,
              Column("cmn_supplypointspecificnum__c", String, primary_key=True),
              Column("cmn_kigyoid_fk__c", String),
              Column("cmn_demandlocationfullname_ref__c", String),
              Column("cmn_oldcustomernum__c", String))
        raw_columns = [Column("corp_number", String), Column("agreement_category", String),
                       Column("org_id", String), Column("building_id", String),
                       Column("corp_name", String), Column("building_name", String),
                       Column("ep_customer_number", String), Column("supply_point_number", String),
                       Column("company_id", String), Column("missing_time_range_count", Integer),
                       Column("invalid_time_range_count", Integer), Column("acquisition_date", String)]
        raw_columns += [Column(f"v30min_used_energy_{i}", Numeric) for i in range(1, 49)]
        raw_columns += [Column("delete_flg", Boolean), Column("created_by", String),
                        Column("created_at", DateTime), Column("updated_by", String),
                        Column("updated_at", DateTime), Column("file_update_date", DateTime),
                        Column("arve_corp_name", String), Column("arve_customer_number", String),
                        Column("arve_office_code", String)]
        Table("t_electricity_data_30min", meta, *raw_columns)
        meta.create_all(connection)
        common = MetaData(schema="db_common")
        prefecture = Table("prefecture_mst", common, Column("pref_cd", String, primary_key=True))
        common.create_all(connection)
        connection.execute(prefecture.insert(), {"pref_cd": "13"})
    yield engine
    engine.dispose()


def options(*extra):
    return parse_args([
        "--corp-number", "9999999999001",
        "--supply-point", "9999999999999999999001",
        "--consent-org-id", "UT30-BANK01",
        "--acquisition-date", DAY, *extra,
    ])


def table(connection, name):
    return Table(name, MetaData(), schema="db_corp", autoload_with=connection)


def test_prepare_then_screen_update_can_insert_30min(database):
    assert "企業が見つかりません" in run(options("--verify"), database)
    assert "DB変更なし" in run(options(), database)
    with database.connect() as connection:
        assert connection.execute(select(table(connection, "m_corporate_basic"))).first() is None
    assert "準備完了" in run(options("--apply"), database)
    assert "供給地点特定番号が未設定" in run(options("--verify"), database)
    with database.begin() as connection:
        basic = table(connection, "m_corporate_basic")
        building = table(connection, "m_building")
        org = table(connection, "m_user_organization_info")
        ep = table(connection, "t_ep_electricity_data_30min")
        arve = table(connection, "t_arve_customer_info")
        row = connection.execute(select(building)).mappings().one()
        assert row["supply_point_number"] is None
        assert row["agreement_org"] == "UT30-BANK01"
        assert connection.execute(select(basic.c.created_by)).scalar_one() == MARKER
        bank_type = connection.execute(
            select(org.c.business_type).where(org.c.org_id == "UT30-BANK01")
        ).scalar_one()
        assert bank_type == "金融機関"
        assert connection.execute(select(ep.c.t01_30t_syr48)).scalar_one() == "48.125"
        assert connection.execute(select(arve.c.cmn_oldcustomernum__c)).scalar_one() == "1230000000000123"
        connection.execute(building.update().values(supply_point_number="9999999999999999999001"))
    status = run(options("--verify"), database)
    assert "登録対象の結合結果=1行、30分値=0行" in status
    with database.begin() as connection:
        raw = table(connection, "t_electricity_data_30min")
        connection.execute(text(INSERT_CORPORATION_30MIN), {
            "corporate_number": "9999999999001", "agreement_category": "01",
            "org_id": "TEP", "building_id": "9999999999001000001",
            "user_id": "test-user", "current_time": datetime(2026, 11, 4),
        })
        result = connection.execute(select(raw)).mappings().one()
        assert result["acquisition_date"] == DAY
        assert result["supply_point_number"] == "9999999999999999999001"
        assert result["v30min_used_energy_1"] == Decimal("1.125")
        assert result["v30min_used_energy_48"] == Decimal("48.125")
        assert (result["arve_office_code"], result["arve_customer_number"]) == ("123", "0000000000123")
    assert "30分値が登録されています" in run(options("--verify"), database)
    assert "削除しました" in run(options("--cleanup"), database)
    with database.connect() as connection:
        for name in ("m_corporate_basic", "m_building", "m_corporate_details_info",
                     "m_user_organization_info", "t_ep_electricity_data_30min",
                     "t_arve_customer_info", "t_electricity_data_30min"):
            assert connection.execute(select(table(connection, name))).first() is None


def test_new_office_and_collision_do_not_overwrite(database):
    run(options("--new-office", "--apply"), database)
    with database.connect() as connection:
        assert connection.execute(select(table(connection, "m_building"))).first() is None
    with pytest.raises(ValueError, match="登録済み"):
        run(options("--new-office", "--apply"), database)
    with database.connect() as connection:
        assert len(connection.execute(select(table(connection, "t_ep_electricity_data_30min"))).all()) == 1


def test_cleanup_preserves_existing_organizations(database):
    with database.begin() as connection:
        org = table(connection, "m_user_organization_info")
        connection.execute(org.insert(), [
            {"org_id": "TEP", "business_type": "EP", "delete_flg": False,
             "created_by": "original"},
            {"org_id": "UT30-BANK01", "business_type": "金融機関",
             "delete_flg": False, "created_by": "original"},
        ])
    run(options("--apply"), database)
    run(options("--cleanup"), database)
    with database.connect() as connection:
        org = table(connection, "m_user_organization_info")
        rows = connection.execute(select(org.c.org_id, org.c.created_by)).all()
        assert set(rows) == {("TEP", "original"), ("UT30-BANK01", "original")}


def test_verify_reports_missing_join_source(database):
    run(options("--apply"), database)
    with database.begin() as connection:
        building = table(connection, "m_building")
        arve = table(connection, "t_arve_customer_info")
        connection.execute(building.update().values(supply_point_number="9999999999999999999001"))
        connection.execute(arve.delete())
    status = run(options("--verify"), database)
    assert "EP=1行、ARVE=0行" in status
    assert "登録SQLで結合できる行がありません" in status
