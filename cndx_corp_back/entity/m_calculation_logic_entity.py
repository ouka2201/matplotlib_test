from sqlalchemy import Boolean, Column, Integer, PrimaryKeyConstraint, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MCalculationLogic(Base):
    __tablename__ = 'm_calculation_logic'
    __table_args__ = (
        PrimaryKeyConstraint('logic_id', 'effectivefrom', name='m_calculation_logic_pkey'),
        {'schema': 'db_corp'}
    )

    logic_id = mapped_column(Integer, nullable=False)
    name = mapped_column(String(255), nullable=False)
    formula = mapped_column(Text, nullable=False)
    variables = mapped_column(JSONB, nullable=False)
    effectivefrom = mapped_column(String(8), nullable=False)
    description = mapped_column(Text)
    effectiveto = mapped_column(String(8))
    target_year = mapped_column(String(4))
    created_by = mapped_column(String(50))
    created_at = mapped_column(TIMESTAMP(precision=6))
    updated_by = mapped_column(String(50))
    updated_at = mapped_column(TIMESTAMP(precision=6))
    delete_flg = mapped_column(Boolean)
