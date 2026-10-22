from sqlalchemy import Boolean, Column, Numeric, PrimaryKeyConstraint, String,  func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MElectricityConversionFactor(Base):
    __tablename__ = 'm_electricity_conversion_factor'
    __table_args__ = (
        PrimaryKeyConstraint('registration_number', 'fiscal_year', name='m_electricity_conversion_factor_pkey'),
        {'comment': '電力会社換算係数マスタ', 'schema': 'db_corp'}
    )

    registration_number = mapped_column(String(5), nullable=False, comment='登録番号')
    electricity_supplier_name = mapped_column(String(300), nullable=False, comment='電気事業者名')
    fiscal_year = mapped_column(String(4), nullable=False, comment='年度')
    start_date = mapped_column(String(8), nullable=False, comment='有効開始日')
    adjusted_emission_factor = mapped_column(Numeric(7, 6), comment='排出係数')
    end_date = mapped_column(String(8), comment='有効終了日')
    # created_at = mapped_column(TIMESTAMP(precision=6), comment='作成日時')
    # created_by = mapped_column(String(50), comment='作成者')
    # updated_at = mapped_column(TIMESTAMP(precision=6), comment='更新日時')
    # updated_by = mapped_column(String(50), comment='更新者')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
