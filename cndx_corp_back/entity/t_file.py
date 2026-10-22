from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, PrimaryKeyConstraint, String, Text, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TFile(Base):
    __tablename__ = 't_file'
    __table_args__ = (
        PrimaryKeyConstraint('file_id', name='t_file_pkey'),
        {'comment': 'ファイル管理', 'schema': 'db_corp'}
    )

    file_id = mapped_column(Integer, comment='ファイルID')
    file_name = mapped_column(String(255), nullable=False, comment='ファイル名')
    file_path = mapped_column(String(255), nullable=False, comment='ファイルパス')
    file_type = mapped_column(String(10), comment='ファイルの種類')
    file_size = mapped_column(BigInteger, comment='ファイルサイズ（バイト単位）')
    uploaded_by = mapped_column(String(50), comment='アップロード者')
    uploaded_at = mapped_column(DateTime, comment='アップロード日時')
    description = mapped_column(Text, comment='ファイル説明')
    status = mapped_column(String(255), comment='状態')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
