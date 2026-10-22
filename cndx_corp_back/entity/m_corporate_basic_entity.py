from sqlalchemy import Boolean, DateTime, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class MCorporateBasic(Base):
    __tablename__ = "m_corporate_basic"
    __table_args__ = (
        PrimaryKeyConstraint("corporate_number", name="m_corporate_basic_pkey"),
        {"comment": "企業基本情報マスタ", "schema": "db_corp"},
    )

    corporate_number = mapped_column(String(13), comment="法人番号")
    company_name_kana = mapped_column(String(100), comment="企業名(ふりがな)")
    company_name = mapped_column(String(100), comment="企業名")
    company_address_prefecture = mapped_column(String(20), comment="企業所在地(都道府県)")
    company_address_city = mapped_column(
        String(100), comment="企業所在地(市区町村以降)"
    )
    # business_office_count = mapped_column(SmallInteger, comment='事業所数')
    delete_flg = mapped_column(Boolean, comment="削除フラグ", default=False)
    created_by = mapped_column(String(50), comment="作成者")
    created_at = mapped_column(DateTime, comment="作成日時", default=func.now())
    updated_by = mapped_column(String(50), comment="更新者")
    updated_at = mapped_column(DateTime, comment="更新日時", onupdate=func.now())
