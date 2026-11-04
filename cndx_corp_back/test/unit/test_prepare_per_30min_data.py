"""30分値テストデータPGの投入・再実行・削除の確認。"""

from types import SimpleNamespace

import pytest
from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, create_engine, select

from cndx_corp_back.test.prepare_per_30min_data import MARKER, parse_args, run


@pytest.fixture
def database():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS db_corp")
        metadata = MetaData(schema="db_corp")
        basic = Table("m_corporate_basic", metadata,
                      Column("corporate_number", String, primary_key=True),
                      Column("company_name", String), Column("company_name_kana", String),
                      Column("company_address_prefecture", String),
                      Column("company_address_city", String), Column("delete_flg", Boolean),
                      Column("created_by", String), Column("created_at", DateTime))
        detail = Table("m_corporate_details_info", metadata,
                       Column("corporate_number", String, primary_key=True),
                       Column("agreement_category", String, primary_key=True),
                       Column("org_id", String, primary_key=True), Column("delete_flg", Boolean),
                       Column("created_by", String), Column("created_at", DateTime))
        org = Table("m_user_organization_info", metadata,
                    Column("org_id", String, primary_key=True), Column("org_name", String),
                    Column("org_type_code", String), Column("org_type", String),
                    Column("company_name", String), Column("delete_flg", Boolean),
                    Column("created_by", String), Column("created_at", DateTime))
        building = Table("m_building", metadata,
                         Column("corporate_number", String, primary_key=True),
                         Column("agreement_category", String, primary_key=True),
                         Column("org_id", String, primary_key=True),
                         Column("building_id", String, primary_key=True),
                         Column("location_identifier_code", String),
                         Column("location_identifier_name", String),
                         Column("building_name", String), Column("agreement_org", String),
                         Column("building_address_prefecture", String),
                         Column("building_address_city", String),
                         Column("supply_point_number", String),
                         Column("ep_office_code", String),
                         Column("ep_customer_number", String), Column("delete_flg", Boolean),
                         Column("created_by", String), Column("created_at", DateTime),
                         Column("updated_by", String), Column("updated_at", DateTime))
        raw_columns = [Column("corp_number", String, primary_key=True),
                       Column("agreement_category", String, primary_key=True),
                       Column("org_id", String, primary_key=True),
                       Column("building_id", String, primary_key=True),
                       Column("acquisition_date", String, primary_key=True),
                       Column("supply_point_number", String), Column("corp_name", String),
                       Column("building_name", String), Column("arve_corp_name", String),
                       Column("arve_office_code", String), Column("arve_customer_number", String),
                       Column("ep_customer_number", String), Column("file_update_date", DateTime),
                       Column("delete_flg", Boolean), Column("created_by", String),
                       Column("created_at", DateTime), Column("updated_by", String),
                       Column("updated_at", DateTime)]
        raw_columns += [Column(f"v30min_used_energy_{i}", Integer) for i in range(1, 49)]
        raw = Table("t_electricity_data_30min", metadata, *raw_columns)
        metadata.create_all(connection)
        connection.execute(basic.insert(), {"corporate_number": "1234567890123", "company_name": "試験企業", "delete_flg": False})
        connection.execute(detail.insert(), {"corporate_number": "1234567890123", "agreement_category": "01", "org_id": "O1", "delete_flg": False})
        connection.execute(org.insert(), [{"org_id": "O1", "delete_flg": False}, {"org_id": "O2", "delete_flg": False}])
        connection.execute(building.insert(), {
            "corporate_number": "1234567890123", "agreement_category": "01", "org_id": "O1",
            "building_id": "SOURCE", "supply_point_number": "9876543210987654321000",
            "ep_customer_number": "0012345678901", "delete_flg": False,
            "created_by": "original", "building_name": "元拠点",
        })
    yield engine, building, raw
    engine.dispose()


def args(case="base", apply=True, cleanup=False):
    return SimpleNamespace(
        case=case, corp_number="1234567890123", org_id="O1", other_org_id="O2",
        template_building_id="SOURCE", supply_point_1="9876543210987654321001",
        supply_point_2="9876543210987654321002", building_id_1="UT30-B20",
        building_id_2="UT30-B10", apply=apply, cleanup=cleanup,
        create_masters=False, prefecture_code="13",
    )


def test_base_is_repeatable_and_cleanup_preserves_source(database):
    engine, building, raw = database
    assert "DB変更なし" in run(args(apply=False), engine)
    with engine.connect() as connection:
        assert connection.execute(select(raw)).all() == []
    run(args(), engine)
    run(args(), engine)
    with engine.connect() as connection:
        data = connection.execute(select(raw).order_by(raw.c.acquisition_date)).mappings().all()
        assert [row["acquisition_date"] for row in data] == ["20260102", "20260104"]
        assert data[0]["arve_office_code"] == "012"
        assert data[0]["arve_customer_number"] == "0000000000045"
        assert data[0]["updated_at"] is None
        assert str(data[1]["updated_at"]) == "2026-01-05 10:20:30"
        assert data[0]["created_by"] == MARKER
    run(args(cleanup=True), engine)
    with engine.connect() as connection:
        assert connection.execute(select(raw)).all() == []
        assert [row[0] for row in connection.execute(select(building.c.building_id))] == ["SOURCE"]


def test_two_buildings_and_collision(database):
    engine, building, raw = database
    run(args(case="two-buildings"), engine)
    with engine.connect() as connection:
        rows = connection.execute(select(raw.c.building_id, raw.c.acquisition_date)).all()
        assert len(rows) == 3
        assert ("UT30-B10", "20260103") in rows
    with engine.begin() as connection:
        connection.execute(building.update().where(building.c.building_id == "UT30-B20").values(created_by="someone_else"))
    with pytest.raises(ValueError, match="既存データ"):
        run(args(), engine)


def test_create_all_masters_without_template_and_cleanup(database):
    engine, building, raw = database
    setup = args(case="two-buildings")
    setup.corp_number = "9999999999001"
    setup.org_id = "UT30-O1"
    setup.other_org_id = "UT30-O2"
    setup.template_building_id = None
    setup.create_masters = True
    assert "DB変更なし" in run(args_for(setup, apply=False), engine)
    run(setup, engine)
    run(setup, engine)
    with engine.connect() as connection:
        metadata = MetaData()
        basic = Table("m_corporate_basic", metadata, schema="db_corp", autoload_with=connection)
        detail = Table("m_corporate_details_info", metadata, schema="db_corp", autoload_with=connection)
        org = Table("m_user_organization_info", metadata, schema="db_corp", autoload_with=connection)
        assert connection.execute(select(basic).where(basic.c.corporate_number == setup.corp_number)).mappings().one()["created_by"] == MARKER
        assert connection.execute(select(detail).where(detail.c.corporate_number == setup.corp_number)).mappings().one()["org_id"] == setup.org_id
        assert len(connection.execute(select(org).where(org.c.org_id.in_((setup.org_id, setup.other_org_id)))).all()) == 2
        assert len(connection.execute(select(building).where(building.c.corporate_number == setup.corp_number)).all()) == 2
        assert len(connection.execute(select(raw).where(raw.c.corp_number == setup.corp_number)).all()) == 3
    run(args_for(setup, cleanup=True), engine)
    with engine.connect() as connection:
        assert connection.execute(select(basic).where(basic.c.corporate_number == setup.corp_number)).first() is None
        assert connection.execute(select(org).where(org.c.org_id == setup.org_id)).first() is None
        assert connection.execute(select(building).where(building.c.building_id == "SOURCE")).first() is not None


def test_create_masters_rejects_existing_unowned_master(database):
    engine, _, raw = database
    setup = args()
    setup.create_masters = True
    setup.template_building_id = None
    with pytest.raises(ValueError, match="既存データ"):
        run(setup, engine)
    with engine.connect() as connection:
        assert connection.execute(select(raw)).all() == []


def test_create_masters_cli_does_not_require_template():
    options = parse_args([
        "--create-masters", "--corp-number", "9999999999001",
        "--org-id", "UT30-O1", "--other-org-id", "UT30-O2",
        "--supply-point-1", "9999999999999999999001",
        "--supply-point-2", "9999999999999999999002",
    ])
    assert options.template_building_id is None


def args_for(source, **changes):
    return SimpleNamespace(**(vars(source) | changes))


@pytest.mark.parametrize("case,dates", [
    ("no-data", []), ("one-day", ["20260102"]),
    ("year-cross", ["20261231", "20270101"]), ("leap-day", ["20240229"]),
])
def test_date_variants(database, case, dates):
    engine, _, raw = database
    run(args(case=case), engine)
    with engine.connect() as connection:
        actual = connection.execute(select(raw.c.acquisition_date).order_by(raw.c.acquisition_date)).scalars().all()
    assert actual == dates
