from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, String, text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MNonFossilCertificateConstant(Base):
    __tablename__ = 'm_non_fossil_certificate_constant'
    __table_args__ = (
        PrimaryKeyConstraint('fossil_free_cert_type_id', 'report_year', name='m_non_fossil_certificate_constant_pkey'),
        {'comment': '非化石証書定数マスタ', 'schema': 'db_corp'}
    )

    fossil_free_cert_type_id = mapped_column(String(1), nullable=False, comment='非化石証書種別ID')
    report_year = mapped_column(String(4), nullable=False, comment='報告年度')
    delete_flg = mapped_column(Boolean, nullable=False, server_default=text('false'), comment='削除フラグ')
    non_fossil_cert_type_name = mapped_column(String(100), comment='非化石証書種別名')
    national_average_factor = mapped_column(Numeric(10, 6), comment='全国平均係数')
    correction_rate = mapped_column(Numeric(10, 6), comment='補正率')
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時')
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時')
