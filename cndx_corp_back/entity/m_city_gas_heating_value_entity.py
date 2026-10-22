from sqlalchemy import Boolean, Column, DateTime, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MCityGasHeatingValue(Base):
    __tablename__ = 'm_city_gas_heating_value'
    __table_args__ = (
        PrimaryKeyConstraint('city_gas_supplier_cd', name='m_city_gas_heating_value_pkey'),
        {'comment': '都市ガス供給事業者マスタ', 'schema': 'db_common'}
    )

    city_gas_supplier_cd = mapped_column(String(5), nullable=False, comment='都市ガス供給事業者コード')
    city_gas_supplier_nm = mapped_column(String(50), comment='都市ガス供給事業者名')
    display_order = mapped_column(String(4), comment='表示順')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', nullable=False, default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())

