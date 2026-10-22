from sqlalchemy import Boolean, DateTime, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class TSessionInfo(Base):
    __tablename__ = 't_session_info'
    __table_args__ = (
        PrimaryKeyConstraint('session_id', name='t_session_info_pkey'),
        {'comment': 'セッション情報', 'schema': 'db_corp'}
    )

    # 主キー（Python側でUUIDv4を生成してCookieに持たせる）
    session_id = mapped_column(
        String(64),
        nullable=False,
        comment='セッションID（UUIDv4）'
    )

    # 必須フィールド
    user_id = mapped_column(String(8), nullable=False, comment='ユーザーID')
    is_active = mapped_column(Boolean, nullable=False, default=True, comment='アクティブフラグ')
    delete_flg = mapped_column(Boolean, nullable=False, default=False, comment='削除フラグ')

    # 任意フィールド
    created_by = mapped_column(String(50), nullable=True, comment='作成者')
    created_at = mapped_column(DateTime, nullable=True, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), nullable=True, comment='更新者')
    updated_at = mapped_column(DateTime, nullable=True, comment='更新日時', onupdate=func.now())
