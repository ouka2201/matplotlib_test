from sqlalchemy import Boolean, Column, PrimaryKeyConstraint, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class MJpStIndustryClassification(Base):
    __tablename__ = 'm_jp_st_industry_classification'
    __table_args__ = (
        PrimaryKeyConstraint('industry_code', name='m_jp_st_industry_classification_pkey'),
        {'schema': 'db_common'}
    )

    division_code = mapped_column(String(1), nullable=False)
    major_group_code = mapped_column(String(3), nullable=False)
    group_code = mapped_column(String(4), nullable=False)
    industry_code = mapped_column(String(4))
    division_name = mapped_column(String(50))
    major_group_name = mapped_column(String(50))
    group_name = mapped_column(String(50))
    industry_name = mapped_column(String(100))
    start_date = mapped_column(String(8))
    end_date = mapped_column(String(8))
    created_at = mapped_column(TIMESTAMP(precision=6))
    created_by = mapped_column(String(50))
    updated_at = mapped_column(TIMESTAMP(precision=6))
    updated_by = mapped_column(String(50))
    delete_flag = mapped_column(Boolean)
