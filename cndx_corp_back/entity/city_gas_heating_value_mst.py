from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class CityGasHeatingValueMst(Base):
    __tablename__ = 'city_gas_heating_value_mst'
    __table_args__ = (
        PrimaryKeyConstraint('city_gas_supplier_code', 'report_year', 'calorific_value_code', name='city_gas_heating_value_mst_pkey'),
        {'comment': '都市ガス供給事業者別単位発熱量マスタ', 'schema': 'db_common'}
    )

    city_gas_supplier_code = mapped_column(String(5), nullable=False, comment='都市ガス供給事業者コード')
    report_year = mapped_column(String(4), nullable=False, comment='報告年度')
    calorific_value_code = mapped_column(String(1), nullable=False, comment='単位発熱量コード')
    heat_conversion_coefficient = mapped_column(Numeric(10, 6), comment='熱量換算係数')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', default=func.now(), onupdate=func.now())
