from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TMonthlyUnitDenominator(Base):
    __tablename__ = 't_monthly_unit_denominator'
    __table_args__ = (
        PrimaryKeyConstraint('corporate_number', 'agreement_category', 'org_id', 'building_id', name='t_monthly_unit_denominator_pkey'),
        {'comment': '月別原単位分母', 'schema': 'db_corp'}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID（FK）')
    building_id = mapped_column(String(113), nullable=False, comment='拠点ID（FK）')
    unit_denominator_kbn = mapped_column(String(4), nullable=False, comment='原単位分母区分')
    unit_denominator_kbn_branch = mapped_column(String(2), nullable=False, comment='原単位分母区分枝番')
    year_month = mapped_column(String(6), comment='年月')
    unit_denominator_unit = mapped_column(String(50), comment='原単位分母単位')
    other_unit_denominator_unit = mapped_column(String(50), comment='その他原単位分母単位')
    unit_denominator_val = mapped_column(Numeric(10, 3), comment='原単位分母数値')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
