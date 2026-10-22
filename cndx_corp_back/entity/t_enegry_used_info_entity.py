from sqlalchemy import (
    Boolean,
    DateTime,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class TEnegryUsedInfo(Base):
    __tablename__ = 't_enegry_used_info'
    __table_args__ = (
        PrimaryKeyConstraint('corporate_number', 'agreement_category', 'building_id', 'energy_code', 'year_month', name='t_enegry_used_info_pkey'),
        {'comment': 'エネルギー利用情報', 'schema': 'db_corp'}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    building_id = mapped_column(String(113), nullable=False, comment='建物ID（FK）')
    energy_code = mapped_column(String(20), nullable=False, comment='エネルギーコード(FK)')
    year_month = mapped_column(String(6), nullable=False, comment='対象年月')
    fiscal_year = mapped_column(String(4), comment='年度')
    corporate_name = mapped_column(String(100), comment='企業名')
    office_name = mapped_column(String(100), comment='事業所名')
    registration_number = mapped_column(SmallInteger, comment='登録回数')
    energy_name = mapped_column(String(20), comment='エネルギー名称')
    primary_energy_data = mapped_column(Numeric(10, 4), comment='一次エネルギー量（kWh）')
    co2_emissions = mapped_column(Numeric(10, 4), comment='CO2排出量')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
