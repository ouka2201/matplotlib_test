from sqlalchemy import Boolean, Column, DateTime, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MCorpCodeInfo(Base):
    __tablename__ = 'm_corp_code_info'
    __table_args__ = (
        PrimaryKeyConstraint('code_type', 'code', name='m_corp_code_info_pkey'),
        {'comment': '法人コード情報マスタ', 'schema': 'db_corp'}
    )

    code_type = mapped_column(String(20), nullable=False, comment='コードタイプ')
    code = mapped_column(String(20), nullable=False, comment='コード')
    jp_code_name = mapped_column(String(50), nullable=False, comment='コード和名')
    en_code_name = mapped_column(String(50), comment='コード英名')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
