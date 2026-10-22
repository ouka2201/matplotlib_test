from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, SmallInteger, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class HeatSupplierMenuMst(Base):
    __tablename__ = 'heat_supplier_menu_mst'
    __table_args__ = (
        PrimaryKeyConstraint('heat_supplier_cd', 'report_year', 'publication_count', name='heat_supplier_menu_mst_pkey'),
        {'comment': '熱供給事業者メニュー別マスタ', 'schema': 'db_common'}
    )

    heat_supplier_cd = mapped_column(String(5), nullable=False, comment='熱供給事業者コード')
    report_year = mapped_column(String(4), nullable=False, comment='報告年度')
    publication_count = mapped_column(SmallInteger, nullable=False, comment='公表回数')
    heat_supplier_name = mapped_column(String(100), comment='熱供給事業者名')
    menu_no = mapped_column(String(100), comment='メニュー番号')
    menu_name = mapped_column(String(100), comment='メニュー名称')
    base_emission_coef = mapped_column(Numeric(10, 6), comment='基礎排出係数')
    adjusted_emission_factor = mapped_column(Numeric(10, 6), comment='調整後排出係数')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
