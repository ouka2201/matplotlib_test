from sqlalchemy import Column, DateTime, PrimaryKeyConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class NonFossilEnergyTypeMst(Base):
    __tablename__ = 'non_fossil_energy_type_mst'
    __table_args__ = (
        PrimaryKeyConstraint('category_id', name='non_fossil_energy_type_mst_pkey'),
        {'schema': 'db_common'}
    )

    category_id = mapped_column(String(1))
    category_nm = mapped_column(String(5))
    unit = mapped_column(String(5))
    green_energy_cert_type_nm = mapped_column(String(20))
    delete_flag = mapped_column(SmallInteger)
    created_by = mapped_column(String(16))
    created_at = mapped_column(DateTime)
    updated_by = mapped_column(String(16))
    updated_at = mapped_column(DateTime)
