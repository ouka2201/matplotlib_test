from sqlalchemy import Boolean, Column, DateTime, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MConsentRouteInfo(Base):
    __tablename__ = 'm_consent_route_info'
    __table_args__ = (
        PrimaryKeyConstraint('agreement_category', name='m_consent_route_info_pkey'),
        {'comment': '同意書取得経路情報', 'schema': 'db_corp'}
    )

    agreement_category = mapped_column(String(2), comment='同意書取得区分')
    agreement_name = mapped_column(String(100), comment='同意書取得経路')
    org_id = mapped_column(String(20), comment='組織ID')
    delete_flg = mapped_column(Boolean, comment='削除フラグ')
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
