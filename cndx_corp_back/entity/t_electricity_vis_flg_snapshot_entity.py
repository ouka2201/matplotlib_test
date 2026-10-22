from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, String, text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TElectricityVisFlgSnapshot(Base):
    __tablename__ = 't_electricity_vis_flg_snapshot'
    __table_args__ = (
        PrimaryKeyConstraint('creation_id', 'acquisition_date', 'acquisition_time', name='t_electricity_vis_flg_snapshot_pkey'),
        {'comment': '電力見える化レポートフラグ付けスナップショット', 'schema': 'db_corp'}
    )

    creation_id = mapped_column(String(80), nullable=False, comment='識別子')
    corp_number = mapped_column(String(13), nullable=False, comment='法人番号')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID')
    building_id = mapped_column(String(113), nullable=False, comment='拠点ID')
    supply_point_number = mapped_column(String(27), nullable=False, comment='供給地点特定番号')
    acquisition_date = mapped_column(String(8), nullable=False, comment='取得_年月日')
    acquisition_time = mapped_column(String(5), nullable=False, comment='取得_時刻')
    created_at = mapped_column(DateTime, nullable=False, server_default=text('now()'), comment='作成日時')
    corp_name = mapped_column(String(100), comment='お客さま名')
    building_name = mapped_column(String(100), comment='建物名')
    ep_customer_number = mapped_column(String(16), comment='EPお客さま番号')
    report_max_day = mapped_column(String(5))
    report_max_week = mapped_column(String(5))
    report_max_frequency = mapped_column(String(5))
    report_target_month = mapped_column(String(5))
    report_max_target_month = mapped_column(String(5))
    delete_flg = mapped_column(Boolean, comment='削除フラグ')
    created_by = mapped_column(String(50), comment='作成者')
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時')
    company_id = mapped_column(String(50))
    building_address = mapped_column(String(120))
    contracted_power = mapped_column(Numeric(10, 4))
