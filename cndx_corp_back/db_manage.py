# flake8: noqa: F405
from sqlalchemy import inspect

from . import create_app, db
from .entity import *  # noqa
from .initial_data import (  # MONTH_ENERGY_USAGE,
    INITIAL_COMPANY_MST,
    INITIAL_SYSTEM_CONTROL_MST,
)

# app = create_app()
app = create_app(config_name="testing")


def init_db():
    """
    DBを初期化する
    """
    with app.app_context():
        db.create_all()


def drop_db():
    """
    DBを削除する
    """
    with app.app_context():
        db.drop_all()


def init_mst_data():
    """マスタデータを初期化する"""
    with app.app_context():
        create_company_mst()
        create_system_control_mst()
        create_tenant_info()


def create_building_mst():
    """建物マスタテーブルをDBに作成"""
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table("building_mst"):
            BuildingMst.__table__.drop(db.engine)
        BuildingMst.__table__.create(db.engine)


def create_prefecture_mst():
    """都道府県マスタテーブルをDBに作成"""
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table("prefecture_mst"):
            PrefectureMst.__table__.drop(db.engine)
        PrefectureMst.__table__.create(db.engine)


def create_company_mst():
    """会社マスタテーブルをDBに作成"""
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table("company_mst"):
            CompanyMst.__table__.drop(db.engine)
        CompanyMst.__table__.create(db.engine)
        db.session.bulk_insert_mappings(CompanyMst, INITIAL_COMPANY_MST)
        db.session.commit()


def create_tenant_info():
    """テナント情報テーブルをDBに作成"""
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table("tenant_info"):
            TenantInfo.__table__.drop(db.engine)
        TenantInfo.__table__.create(db.engine)


def create_system_control_mst():
    """システム制御マスタテーブルをDBに作成"""
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table("system_control_mst"):
            SystemControlMst.__table__.drop(db.engine)
        SystemControlMst.__table__.create(db.engine)
        db.session.bulk_insert_mappings(SystemControlMst, INITIAL_SYSTEM_CONTROL_MST)
        db.session.commit()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        func_name = sys.argv[1]
        globals()[func_name]()
    else:
        drop_db()
        init_db()
        init_mst_data()
# python -m cndx_corp_back.db_manage
# python -m cndx_corp_back.db_manage method_name
