from sqlalchemy import Boolean, Column, Date, DateTime, PrimaryKeyConstraint, String, Integer, func, Sequence
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()

user_id_seq = Sequence('db_corp.m_user_user_id_seq')

class MUser(Base):
    __tablename__ = 'm_user'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', name='m_user_pkey'),
        {'comment': 'ユーザー情報', 'schema': 'db_corp'}
    )

    user_id = mapped_column(String(8), server_default=user_id_seq.next_value(), comment='ユーザーID')
    email_address = mapped_column(String(100), nullable=False, comment="メールアドレス")
    user_name = mapped_column(String(50), nullable=False, comment='ユーザー名')
    company_name = mapped_column(String(100), nullable=False, comment='会社名')
    delete_flg = mapped_column(Boolean, nullable=False, comment='削除フラグ', default=False)
    department_id = mapped_column(String(3), comment='部門ID')
    user_password = mapped_column(String(100), nullable=False, server_default='Password@1', comment='パスワード')
    org_id = mapped_column(String(20), comment='組織ID（FK）')
    user_role = mapped_column(String(10), nullable=False, comment='ロール')
    user_status = mapped_column(String(1), comment='ステータス')
    start_date = mapped_column(Date, comment='有効開始日')
    end_date = mapped_column(Date, comment='有効終了日')
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())

