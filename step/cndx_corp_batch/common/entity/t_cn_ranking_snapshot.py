from sqlalchemy import Boolean, Column, Integer, Numeric, PrimaryKeyConstraint, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TCnRankingSnapshot(Base):
    __tablename__ = 't_cn_ranking_snapshot'
    __table_args__ = (
        PrimaryKeyConstraint('creation_id', 'energy_code', name='t_cn_ranking_snapshot_pkey'),
        {'comment': 'CNランキングスナップショット', 'schema': 'db_corp'}
    )

    creation_id = mapped_column(String(80), nullable=False, comment='識別子')
    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID')
    fiscal_year = mapped_column(String(4), nullable=False, comment='年度')
    registration_seq = mapped_column(Integer, nullable=False, comment='登録回数')
    energy_code = mapped_column(String(20), nullable=False, comment='エネルギーコード')
    created_at = mapped_column(TIMESTAMP(precision=6), nullable=False, server_default=text('now()'), comment='作成日時')
    energy_ranking_name = mapped_column(String(100), comment='ランキング名')
    energy_ranking = mapped_column(Numeric(2, 0), comment='ランキング')
    delete_flg = mapped_column(Boolean, comment='削除フラグ')
    created_by = mapped_column(String(50), comment='作成者')
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(TIMESTAMP(precision=6), comment='更新日時')
