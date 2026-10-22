from sqlalchemy import Column, DateTime, Numeric, PrimaryKeyConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class NonFossilCertConstantMst(Base):
    __tablename__ = 'non_fossil_cert_constant_mst'
    __table_args__ = (
        PrimaryKeyConstraint('report_target_year', 'fossil_free_cert_type_id', name='non_fossil_cert_constant_mst_pkey'),
        {'schema': 'db_common'}
    )

    report_target_year = mapped_column(SmallInteger, nullable=False)
    fossil_free_cert_type_id = mapped_column(String(1), nullable=False)
    national_average_coef = mapped_column(Numeric(7, 6))
    correction_rate = mapped_column(Numeric(7, 6))
    delete_flag = mapped_column(SmallInteger)
    created_by = mapped_column(String(16))
    created_at = mapped_column(DateTime)
    updated_by = mapped_column(String(16))
    updated_at = mapped_column(DateTime)
