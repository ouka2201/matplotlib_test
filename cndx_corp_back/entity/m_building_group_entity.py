from sqlalchemy import Boolean, Column, DateTime, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MBuildingGroup(Base):
    __tablename__ = 'm_buiding_group'
    __table_args__ = (
        PrimaryKeyConstraint('corporate_number', 'agreement_category', 'org_id', 'group_id', name='m_buiding_group_pkey'),
        {'comment': '建物グループマスタ', 'schema': 'db_corp'}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID（FK）')
    group_id = mapped_column(String(16), nullable=False, comment='グループID（FK）')
    group_name = mapped_column(String(50), comment='グループ名')
    select_item1 = mapped_column(String(50), comment='選択肢１')
    select_item2 = mapped_column(String(50), comment='選択肢２')
    select_item3 = mapped_column(String(50), comment='選択肢３')
    select_item4 = mapped_column(String(50), comment='選択肢４')
    select_item5 = mapped_column(String(50), comment='選択肢５')
    select_item6 = mapped_column(String(50), comment='選択肢６')
    select_item7 = mapped_column(String(50), comment='選択肢７')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
