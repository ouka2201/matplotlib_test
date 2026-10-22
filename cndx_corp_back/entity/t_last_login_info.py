from sqlalchemy import Boolean, DateTime, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class TLastLoginInfo(Base):
    __tablename__ = 't_last_login_info'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', name='t_last_login_info_pkey'),
        {'comment': '最終ログイン情報', 'schema': 'db_corp'}
    )

    # 主キー
    user_id = mapped_column(String(8), nullable=False, comment='ユーザーID')

    # 必須フィールド
    last_login_datetime = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        comment='最終ログイン日時'
    )
    session_id = mapped_column(
        String(64),
        nullable=False,
        comment='セッションID（UUIDv4）'
    )
    delete_flg = mapped_column(Boolean, nullable=False, default=False, comment='削除フラグ')

    # 任意フィールド
    created_by = mapped_column(String(50), nullable=True, comment='作成者')
    created_at = mapped_column(DateTime, nullable=True, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), nullable=True, comment='更新者')
    updated_at = mapped_column(DateTime, nullable=True, comment='更新日時')
