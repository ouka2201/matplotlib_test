from sqlalchemy import Boolean, Column, DateTime, PrimaryKeyConstraint, String, func, Integer
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MUserOrganizationInfo(Base):
    __tablename__ = 'm_user_organization_info'
    __table_args__ = (
        PrimaryKeyConstraint('org_id', name='m_user_organization_info_pkey'),
        {'comment': '利用者組織情報', 'schema': 'db_corp'}
    )

    org_id = mapped_column(String(20), comment='組織ID')
    org_name = mapped_column(String(100), comment='組織名')
    parent_org_id = mapped_column(String(20), comment='親組織ID')
    company_code = mapped_column(String(3), comment='会社コード')
    company_name = mapped_column(String(100), comment='企業名')
    bank_code = mapped_column(String(4), comment='銀行コード')
    branch_code = mapped_column(String(3), comment='支店コード')
    branch_name = mapped_column(String(100), comment='支店名')
    org_type_code = mapped_column(String(2), comment='組織種別コード')
    org_type = mapped_column(String(20), comment='組織種別')
    business_type = mapped_column(String(100), comment='事業者区分')
    max_user_reg = mapped_column(Integer, comment='ユーザー登録数上限')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
