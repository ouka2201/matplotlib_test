from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MBenchmarkInfo(Base):
    __tablename__ = 'm_benchmark_info'
    __table_args__ = (
        PrimaryKeyConstraint('industry_class_detail_code', 'pulldown_code', 'total_floor_area_flag', 'target_total_floor_area_min', name='m_benchmark_info_pkey'),
        {'comment': '公表ベンチマークデータ情報', 'schema': 'db_corp'}
    )

    industry_class_detail_code = mapped_column(String(4), nullable=False, comment='日本標準産業分類（細分類）')
    pulldown_code = mapped_column(String(5), nullable=False, comment='プルダウンコード')
    total_floor_area_flag = mapped_column(String(1), nullable=False, comment='延床面積別フラグ')
    target_total_floor_area_min = mapped_column(Numeric(12, 2), nullable=False, comment='対象延床（以上）')
    industry_class_detail_name = mapped_column(String(100), comment='日本標準産業分類（細分類）名称')
    pulldown_item_name = mapped_column(String(100), comment='プルダウン項目')
    energy_saving_denominator = mapped_column(Numeric(22, 17), comment='省エネ率分母')
    target_total_floor_area_max = mapped_column(Numeric(12, 2), comment='対象延床（未満）')
    competitor_industry_co2_avg = mapped_column(Numeric(6, 4), comment='他社比較業種_CO2排出源単位平均値')
    delete_flg = mapped_column(Boolean, comment='削除フラグ')
    created_by = mapped_column(String(50), comment='登録者')
    created_at = mapped_column(DateTime, comment='登録日時')
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時')
