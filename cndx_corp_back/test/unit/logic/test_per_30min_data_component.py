from contextlib import contextmanager
from datetime import datetime
from unittest.mock import Mock

from flask import Flask
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import cndx_corp_back.api.auth  # noqa: F401 - Load auth routes before decorators to avoid the package import cycle.
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.t_electricity_data_30min_entity import TElectricityData30min
from cndx_corp_back.logic.EBMV_Per30minData import per_30min_data_component as module
from cndx_corp_back.api.EBMV_Per30minData import per_30min_data_api


def test_list_aggregates_dates_and_arve_values_for_selected_organization(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def prepare_connection(dbapi_connection, _):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS db_corp")
        dbapi_connection.create_collation("C", lambda left, right: (left > right) - (left < right))

    MBuilding.__table__.create(engine)
    TElectricityData30min.__table__.create(engine)
    with Session(engine) as session:
        session.add_all([
            MBuilding(corporate_number="123", agreement_category="01", org_id="org-a", building_id="site-a", delete_flg=False),
            MBuilding(corporate_number="123", agreement_category="01", org_id="org-b", building_id="site-b", delete_flg=False),
            TElectricityData30min(corp_number="123", agreement_category="01", org_id="org-a", building_id="site-a", supply_point_number="point-a", acquisition_date="20260102", building_name="拠点A", created_at=datetime(2026, 1, 3), arve_corp_name="ARVE名", arve_office_code="012", arve_customer_number="00045", delete_flg=False),
            TElectricityData30min(corp_number="123", agreement_category="01", org_id="org-a", building_id="site-a", supply_point_number="point-a", acquisition_date="20260104", building_name="拠点A", created_at=datetime(2026, 1, 3), updated_at=datetime(2026, 1, 5), arve_corp_name="ARVE名", arve_office_code="012", arve_customer_number="00045", delete_flg=False),
            TElectricityData30min(corp_number="123", agreement_category="01", org_id="org-b", building_id="site-b", supply_point_number="point-b", acquisition_date="20260101", building_name="拠点B", created_at=datetime(2026, 1, 2), delete_flg=False),
        ])
        session.commit()

    @contextmanager
    def session_scope():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(module, "get_scoped_session", session_scope)
    result = module.Per30minDataComponent.execute.__wrapped__(
        module.Per30minDataComponent(),
        {"corp_number": "123", "building_id": "", "agreement_category": "01", "org_id": "org-a"},
        None, None, None, None, logger=Mock(),
    )

    assert result["upload_history"] == [{
        "corp_number": "123",
        "building_name": "拠点A",
        "building_id": "site-a",
        "period_from": "20260102",
        "period_to": "20260104",
        "file_update_date": "2026-01-05 00:00:00",
        "ARVE_CORP_NAME": "ARVE名",
        "ARVE_OFFICE_CODE": "012",
        "ARVE_CUSTOMER_NUMBER": "00045",
    }]


def test_list_api_rejects_other_roles_and_reports_database_errors(monkeypatch):
    api = per_30min_data_api.Per30minDataApi()
    get = api.get.__wrapped__.__wrapped__
    with Flask(__name__).app_context():
        response, status = get(
            api, {}, user_context={"org_type_code": "02", "role": "0"}, logger=Mock()
        )
        assert status == 403
        assert response.json["message"] == "利用権限がありません。"

        def fail(*_args):
            raise RuntimeError("database unavailable")

        monkeypatch.setattr(
            per_30min_data_api.Per30minDataService,
            "get_per_30min_data_list",
            fail,
        )
        response, status = get(
            api, {}, user_context={"org_type_code": "01", "role": "1"}, logger=Mock()
        )
        assert status == 500
        assert response.json["message"] == "システムエラーが発生しました。"
