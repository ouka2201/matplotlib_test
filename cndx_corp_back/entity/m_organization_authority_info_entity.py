from sqlalchemy import Boolean, Column, DateTime, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MOrganizationAuthorityInfo(Base):
    __tablename__ = 'm_organization_authority_info'
    __table_args__ = (
        PrimaryKeyConstraint('org_type_code', 'authority_id', 'user_role', name='m_organization_authority_info_pkey'),
        {'comment': '組織権限情報', 'schema': 'db_corp'}
    )

    org_type_code = mapped_column(String(2), nullable=False, comment='組織種別コード')
    authority_id = mapped_column(String(15), nullable=False, comment='権限ID')
    user_role = mapped_column(String(1), nullable=False, comment='ロール')
    org_type = mapped_column(String(20), comment='組織種別')
    screen_name = mapped_column(String(20), comment='画面名')
    authority_code = mapped_column(String(1), comment='権限コード')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
