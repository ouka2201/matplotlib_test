from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class MStaffInfo(Base):
    __tablename__ = "m_staff_info"
    __table_args__ = {"schema": "db_corp"}

    corporate_number: Mapped[str] = mapped_column(
        String(13), primary_key=True, comment="法人番号（FK）"
    )
    agreement_category: Mapped[str] = mapped_column(
        String(2), primary_key=True, comment="同意書取得区分"
    )
    org_id: Mapped[str] = mapped_column(
        String(20), primary_key=True, comment="組織ID（FK）"
    )
    user_id: Mapped[str] = mapped_column(
        String(20), primary_key=True, comment="担当者ユーザーID（FK）"
    )

    consent_receipt_date: Mapped[str] = mapped_column(String(8), comment="同意書受領日")
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
