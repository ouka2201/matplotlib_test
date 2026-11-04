"""LMMBCS-API-04：HTTP応答と、企業・拠点・30分値の保存結果を検証する。"""

from datetime import datetime
from decimal import Decimal

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token
from sqlalchemy import event, text

# create_app と同じ順序で認証Blueprintを読み込む。
from cndx_corp_back.api.auth import auth_bp  # noqa: F401
from cndx_corp_back.api.MSOG_corprationMstOperation import mst_manage_bp
from cndx_corp_back.common import decorators
from cndx_corp_back.common.error_handler import register_error_handlers
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.t_electricity_data_30min_entity import TElectricityData30min
from cndx_corp_back.ext import db, jwt
from cndx_corp_back.logic.MSOG_corprationMstOperation.corpration_basic_update_component import (
    CorprationBasicUpdateComponent,
)

URL = "/api/mst_manage/corpration/info"
CORP = "1234567890123"
BID = CORP + "000001"
POINT_A = "1" * 22
POINT_B = "2" * 22
MODELS = (MCorporateBasic, MBuilding, MCorporateDetailsInfo, TElectricityData30min)


@pytest.fixture
def app(monkeypatch):
    # 既存処理の日時文字列はPostgreSQLで受理されるが、SQLiteのDateTime型は受理しない。
    monkeypatch.setattr(
        CorprationBasicUpdateComponent,
        "get_current_timestamp",
        lambda _: datetime.now(),
    )
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        JWT_SECRET_KEY="test-corporation-update-secret-key",
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_COOKIE_CSRF_PROTECT=False,
    )
    db.init_app(app)
    jwt.init_app(app)
    app.register_blueprint(mst_manage_bp)
    register_error_handlers(app)
    app.user_context = {"user_id": "ep-admin", "role": "0", "org_type_code": "01"}
    monkeypatch.setattr(decorators, "get_user_permissions", lambda _: app.user_context)
    with app.app_context():

        @event.listens_for(db.engine, "connect")
        def attach(connection, _):
            connection.execute("ATTACH DATABASE ':memory:' AS db_corp")

        @event.listens_for(db.engine, "before_cursor_execute", retval=True)
        def sqlite_date_compat(
            connection, cursor, statement, parameters, context, many
        ):
            # 日付式だけをSQLiteへ変換し、結合・登録・削除は実SQLを実行する。
            statement = statement.replace(
                "to_char(CURRENT_DATE - INTERVAL '5 years', 'YYYYMMDD')",
                "strftime('%Y%m%d', 'now', '-5 years')",
            ).replace("to_char(CURRENT_DATE, 'YYYYMMDD')", "strftime('%Y%m%d', 'now')")
            return statement, parameters

        for model in MODELS:
            model.__table__.create(db.engine)
        for column in ("arve_corp_name", "arve_customer_number", "arve_office_code"):
            db.session.execute(
                text(
                    f"ALTER TABLE db_corp.t_electricity_data_30min ADD COLUMN {column} TEXT"
                )
            )
        slots = ", ".join(f"t01_30t_syr{i:02d} TEXT" for i in range(1, 49))
        db.session.execute(
            text(f"""CREATE TABLE db_corp.t_ep_electricity_data_30min (
            t01_kyo_ctn_tok_no TEXT, t01_get_ymd TEXT, t01_kskj_ksu TEXT,
            t01_fsij_ksu TEXT, {slots})""")
        )
        db.session.execute(
            text("""CREATE TABLE db_corp.t_arve_customer_info (
            cmn_supplypointspecificnum__c TEXT PRIMARY KEY, cmn_kigyoid_fk__c TEXT,
            cmn_demandlocationfullname_ref__c TEXT, cmn_oldcustomernum__c TEXT)""")
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    client = app.test_client()
    client.set_cookie("access_token_cookie", create_access_token(identity="ep-admin"))
    return client


def payload(offices=None, **overrides):
    return {
        "corporate_number": CORP,
        "company_name": "更新後の企業",
        "company_name_kana": "キギョウ",
        "company_address_prefecture": "13",
        "company_address_city": "千代田区",
        "usage_type": "1",
        "office_info_list": [] if offices is None else offices,
        "user_id": "spoofed-user",
        **overrides,
    }


def office(building_id="", point=POINT_A, **overrides):
    return {
        "building_id": building_id,
        "org_id": "TEP",
        "agreement_category": "01",
        "agreement_org": "TEP",
        "location_identifier_name": "拠点名",
        "building_address_prefecture": "13",
        "building_address_city": "千代田区",
        "ep_office_code": "001",
        "ep_customer_number": "0000000000001",
        "supply_point_number": point,
        **overrides,
    }


def seed_company():
    db.session.add(
        MCorporateBasic(corporate_number=CORP, company_name="変更前", delete_flg=False)
    )
    db.session.commit()


def seed_building(bid=BID, point=POINT_A, category="01", org_id="TEP", deleted=False):
    db.session.add(
        MBuilding(
            corporate_number=CORP,
            org_id=org_id,
            agreement_category=category,
            building_id=bid,
            supply_point_number=point,
            delete_flg=deleted,
            location_identifier_name="変更前拠点",
            building_name="変更前建物",
            agreement_org="TEP",
            created_by="original",
            gross_floor_area=123,
            group1="既存グループ",
        )
    )
    db.session.add(
        MCorporateDetailsInfo(
            corporate_number=CORP,
            org_id=org_id,
            agreement_category=category,
            business_office_count=1,
            delete_flg=deleted,
        )
    )
    db.session.commit()


def seed_raw(
    bid=BID,
    point=POINT_A,
    category="01",
    org_id="TEP",
    corp=CORP,
    day="20260101",
):
    db.session.add(
        TElectricityData30min(
            corp_number=corp,
            org_id=org_id,
            agreement_category=category,
            building_id=bid,
            supply_point_number=point,
            acquisition_date=day,
            v30min_used_energy_1=999,
            created_by="original",
            delete_flg=False,
        )
    )
    db.session.commit()


def seed_source(point=POINT_A, day=None, arve=True):
    columns = ", ".join(f"t01_30t_syr{i:02d}" for i in range(1, 49))
    values = ", ".join(f"'{i}.125'" for i in range(1, 49))
    db.session.execute(
        text(f"""INSERT INTO db_corp.t_ep_electricity_data_30min
        (t01_kyo_ctn_tok_no, t01_get_ymd, t01_kskj_ksu, t01_fsij_ksu, {columns})
        VALUES (:point, :day, '2', '3', {values})"""),
        {
            "point": point,
            "day": day
            or db.session.execute(
                text("SELECT strftime('%Y%m%d', 'now')")
            ).scalar_one(),
        },
    )
    if arve:
        db.session.execute(
            text("""INSERT INTO db_corp.t_arve_customer_info VALUES
            (:point, 'company-id', 'ARVEのお客さま', '1230000000000123')"""),
            {"point": point},
        )
    db.session.commit()


def test_create_company_only_and_reject_duplicate(client):
    request = payload([], usage_type="0")
    response = client.post(URL, json=request)
    assert response.status_code == 200
    assert response.json == {"result": None}
    corporate = db.session.query(MCorporateBasic).one()
    assert corporate.created_by == "ep-admin"
    assert corporate.company_name == request["company_name"]
    assert not corporate.delete_flg
    assert db.session.query(MBuilding).count() == 0
    assert db.session.query(MCorporateDetailsInfo).count() == 0
    assert client.post(URL, json=request).status_code == 404
    assert db.session.query(MCorporateBasic).count() == 1


def test_requires_authentication(app):
    response = app.test_client().post(URL, json=payload(usage_type="0"))
    assert response.status_code == 401


def test_new_office_links_five_years_and_maps_all_fields(client):
    seed_company()
    seed_source(day="20000101")
    seed_source(arve=False)
    seed_source(day="29990101", arve=False)
    response = client.post(URL, json=payload([office()]))
    assert response.status_code == 200
    building = db.session.query(MBuilding).one()
    assert building.building_id == CORP + "000001"
    assert not building.building_consent_flag  # 既存の新規登録処理の既定値を維持
    raw = db.session.query(TElectricityData30min).one()
    assert raw.building_id == building.building_id
    assert raw.corp_name == "更新後の企業"
    assert raw.building_name == "拠点名"
    assert raw.ep_customer_number == "0000000000001"
    assert raw.company_id == "company-id"
    assert (raw.missing_time_range_count, raw.invalid_time_range_count) == (2, 3)
    assert raw.created_by == "ep-admin"
    for i in range(1, 49):
        assert getattr(raw, f"v30min_used_energy_{i}") == Decimal(f"{i}.125")
    arve = db.session.execute(
        text(
            "SELECT arve_corp_name, arve_customer_number, arve_office_code FROM db_corp.t_electricity_data_30min"
        )
    ).one()
    assert tuple(arve) == ("ARVEのお客さま", "0000000000123", "123")
    assert db.session.query(MCorporateDetailsInfo).one().business_office_count == 1


@pytest.mark.parametrize("source", ["none", "ep_only", "arve_only"])
def test_missing_join_source_skips_raw_registration(client, source):
    seed_company()
    if source == "ep_only":
        seed_source(arve=False)
    elif source == "arve_only":
        seed_source()
        db.session.execute(text("DELETE FROM db_corp.t_ep_electricity_data_30min"))
        db.session.commit()
    assert client.post(URL, json=payload([office()])).status_code == 200
    assert db.session.query(MBuilding).count() == 1
    assert db.session.query(TElectricityData30min).count() == 0


def test_unchanged_supply_point_preserves_raw_and_unedited_building_fields(client):
    seed_company()
    seed_building()
    seed_raw()
    seed_source()
    assert client.post(URL, json=payload([office(BID)])).status_code == 200
    raw = db.session.query(TElectricityData30min).one()
    assert raw.v30min_used_energy_1 == 999
    assert raw.created_by == "original"
    building = db.session.query(MBuilding).one()
    assert building.location_identifier_name == "拠点名"
    assert building.gross_floor_area == 123
    assert building.group1 == "既存グループ"
    assert building.updated_by == "ep-admin"


def test_changed_point_removes_old_and_new_raw_but_preserves_other_keys(client):
    seed_company()
    seed_building()
    seed_raw()
    seed_raw(point=POINT_B, day="20260102")
    seed_raw(bid="other", org_id="OTHER")
    seed_raw(corp="9999999999999")
    seed_source(POINT_B, day="20000101")
    assert client.post(URL, json=payload([office(BID, POINT_B)])).status_code == 200
    rows = db.session.query(TElectricityData30min).all()
    assert len(rows) == 3
    target = next(r for r in rows if r.corp_number == CORP and r.building_id == BID)
    assert target.supply_point_number == POINT_B
    assert target.acquisition_date == "20000101"  # 更新仕様No.11は5年制限なし
    assert target.v30min_used_energy_1 == Decimal("1.125")


def test_blank_numbers_group_counts_and_no_consent(client):
    seed_company()
    offices = [
        office(point=None, ep_customer_number=None, agreement_category="00")
        for _ in range(2)
    ]
    assert client.post(URL, json=payload(offices)).status_code == 200
    assert db.session.query(MBuilding).count() == 2
    assert all(not b.building_consent_flag for b in db.session.query(MBuilding))
    assert db.session.query(MCorporateDetailsInfo).one().business_office_count == 2


def test_cleared_point_deletes_old_data_without_reinserting(client):
    seed_company()
    seed_building()
    seed_raw()
    seed_source()
    assert client.post(URL, json=payload([office(BID, "")])).status_code == 200
    assert db.session.query(MBuilding).one().supply_point_number == ""
    assert db.session.query(TElectricityData30min).count() == 0


def test_restoring_deleted_building_recreates_raw_data(client):
    seed_company()
    seed_building(deleted=True)
    seed_source()
    assert client.post(URL, json=payload([office(BID)])).status_code == 200
    assert not db.session.query(MBuilding).one().delete_flg
    assert not db.session.query(MCorporateDetailsInfo).one().delete_flg
    assert db.session.query(TElectricityData30min).one().created_by == "ep-admin"


def test_sync_failure_rolls_back_company_buildings_details_and_raw(client, app):
    seed_company()
    seed_building()
    seed_raw()

    @event.listens_for(db.engine, "before_cursor_execute")
    def fail_raw_insert(connection, cursor, statement, parameters, context, many):
        if "INSERT INTO db_corp.t_electricity_data_30min" in statement:
            raise RuntimeError("simulated source failure")

    response = client.post(URL, json=payload([office(BID, POINT_B)]))
    assert response.status_code == 500
    assert db.session.query(MCorporateBasic).one().company_name == "変更前"
    building = db.session.query(MBuilding).one()
    assert building.supply_point_number == POINT_A and not building.delete_flg
    assert db.session.query(MCorporateDetailsInfo).one().business_office_count == 1
    assert db.session.query(TElectricityData30min).one().v30min_used_energy_1 == 999


def test_empty_office_list_keeps_base_deletion_scope_and_removes_raw(client):
    seed_company()
    seed_building()
    seed_building(org_id="OTHER")
    seed_raw()
    seed_raw(org_id="OTHER")
    assert client.post(URL, json=payload([])).status_code == 200
    assert all(b.delete_flg for b in db.session.query(MBuilding))
    assert all(d.delete_flg for d in db.session.query(MCorporateDetailsInfo))
    assert db.session.query(TElectricityData30min).count() == 0


def test_partial_deletion_follows_existing_building_updates(client):
    seed_company()
    seed_building()
    other = MBuilding(
        corporate_number=CORP,
        org_id="TEP",
        agreement_category="01",
        building_id=CORP + "000002",
        supply_point_number=POINT_B,
        delete_flg=False,
        agreement_org="TEP",
    )
    db.session.add(other)
    db.session.commit()
    seed_raw()
    seed_raw(bid=other.building_id, point=POINT_B)
    assert client.post(URL, json=payload([office(BID)])).status_code == 200
    assert (
        db.session.query(MBuilding)
        .filter_by(building_id=CORP + "000002")
        .one()
        .delete_flg
    )
    assert db.session.query(TElectricityData30min).one().building_id == BID


def test_vis_flag_preserves_building_and_raw_without_sync_sql(client):
    seed_company()
    seed_building(bid="VIS_ID")
    seed_raw(bid="VIS_ID")
    seed_source(POINT_B)
    raw_writes = []

    @event.listens_for(db.engine, "before_cursor_execute")
    def record_raw_writes(connection, cursor, statement, parameters, context, many):
        if "t_electricity_data_30min" in statement and statement.lstrip().startswith(
            ("INSERT", "DELETE", "UPDATE")
        ):
            raw_writes.append(statement)

    assert (
        client.post(URL, json=payload([office("VIS_ID", POINT_B)])).status_code == 200
    )
    assert db.session.query(MBuilding).one().supply_point_number == POINT_A
    assert db.session.query(TElectricityData30min).one().v30min_used_energy_1 == 999
    assert not raw_writes


def test_existing_duplicate_check_includes_office_scheduled_for_deletion(client):
    seed_company()
    seed_building()
    seed_raw()
    request = payload([office("", POINT_A)])
    assert client.post(URL, json=request).status_code == 400
    assert not db.session.query(MBuilding).one().delete_flg
    assert db.session.query(TElectricityData30min).one().v30min_used_energy_1 == 999


def test_insert_only_request_does_not_change_base_deletion_behavior(client):
    seed_company()
    seed_building()
    seed_raw()
    seed_source(POINT_B)
    assert (
        client.post(
            URL, json=payload([office("", POINT_B, agreement_category="02")])
        ).status_code
        == 200
    )
    # 既存処理は更新対象がない場合、旧拠点を削除しない。同期処理もそれに従う。
    assert not db.session.query(MBuilding).filter_by(building_id=BID).one().delete_flg
    assert db.session.query(MBuilding).count() == 2
    assert db.session.query(TElectricityData30min).count() == 2


def test_no_additional_role_gate_or_new_validation_is_introduced(client, app):
    app.user_context.update(org_type_code="02", role="1")
    response = client.post(
        URL, json=payload([], usage_type="0", corporate_number="123")
    )
    assert response.status_code == 200
    assert response.json == {"result": None}
    assert db.session.query(MCorporateBasic).one().corporate_number == "123"


@pytest.mark.parametrize("old_org", ["TEP", "OTHER"])
def test_sync_follows_existing_primary_key_changes(client, old_org):
    seed_company()
    seed_building(org_id=old_org)
    seed_raw(org_id=old_org)
    seed_raw(category="02", day="20260102")
    seed_source()
    request = payload([office(BID, agreement_category="02", agreement_org="BNK")])
    assert client.post(URL, json=request).status_code == 200
    building = db.session.query(MBuilding).one()
    assert (building.org_id, building.agreement_category) == ("TEP", "02")
    raw = db.session.query(TElectricityData30min).one()
    assert (raw.org_id, raw.agreement_category) == ("TEP", "02")
    assert raw.v30min_used_energy_1 == Decimal("1.125")
