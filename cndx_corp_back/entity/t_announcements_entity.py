from sqlalchemy import Column, Numeric, PrimaryKeyConstraint, SmallInteger, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TAnnouncements(Base):
    __tablename__ = 't_announcements'
    __table_args__ = (
        PrimaryKeyConstraint(
            "announcement_id",
            name="t_announcements_pkey",
        ),
        {"comment": "", "schema": "db_corp"},
    )

    announcement_id = mapped_column(SmallInteger, nullable=False)
    title = mapped_column(String(20), nullable=False)
    message1 = mapped_column(String(200))
    message2 = mapped_column(String(200))
    message3 = mapped_column(String(200))
    start_date = mapped_column(DateTime)
    end_date = mapped_column(DateTime)
    delete_flg = mapped_column(Boolean)
    created_by = mapped_column(String(50))
    created_at = mapped_column(DateTime)
    updated_by = mapped_column(String(50))
    updated_at = mapped_column(DateTime)


