from sqlalchemy import Column, DateTime, PrimaryKeyConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class PrefectureMst(Base):
    __tablename__ = 'prefecture_mst'
    __table_args__ = (
        PrimaryKeyConstraint('pref_cd', name='prefecture_mst_pkey'),
        {'schema': 'db_common'}
    )

    pref_cd = mapped_column(String(2))
    pref_nm = mapped_column(String(4))
    delete_flag = mapped_column(SmallInteger)
    created_by = mapped_column(String(50))
    created_at = mapped_column(DateTime)
    updated_by = mapped_column(String(50))
    updated_at = mapped_column(DateTime)
