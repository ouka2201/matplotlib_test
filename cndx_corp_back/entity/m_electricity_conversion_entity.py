from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, SmallInteger, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MElectricityConversion(Base):
    __tablename__ = 'm_electricity_conversion'
    __table_args__ = (
        PrimaryKeyConstraint('electric_company_reg_no', 'report_target_year', 'publication_count', 'menu_no', name='m_electricity_conversion_pkey'),
        {'comment': '電力会社排出係数マスタ', 'schema': 'db_corp'}
    )

    electric_company_reg_no = mapped_column(String(5), nullable=False, comment='電気事業者登録番号')
    report_target_year = mapped_column(String(4), nullable=False, comment='報告対象年度')
    publication_count = mapped_column(SmallInteger, nullable=False, comment='公表回数')
    menu_no = mapped_column(SmallInteger, nullable=False, comment='メニュー番号')
    electric_supplier_nm = mapped_column(String(100), comment='電気事業者名')
    menu_nm = mapped_column(String(100), comment='メニュー名称')
    adjusted_emission_coef = mapped_column(Numeric(7, 6), comment='調整後排出係数')
    fossil_free_cert_usage = mapped_column(Numeric(5, 2), comment='非化石証書の使用状況')
    emission_factor_base = mapped_column(Numeric(7, 6), comment='基礎排出係数')
    residual_flg = mapped_column(Boolean, comment='残差フラグ')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
