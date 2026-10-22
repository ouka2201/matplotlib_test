from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class MCompetitorIndustry(Base):
    __tablename__ = 'm_competitor_industry'
    __table_args__ = (
        PrimaryKeyConstraint('industry_class_major_code', 'industry_class_middle_code', 'industry_class_minor_code', 'industry_class_detail_code', 'benchmark_industry_code', 'floor_area_flag', 'target_floor_area_min', name='m_competitor_industry_pkey'),
        {'comment': '他社比較業種マスタ', 'schema': 'db_corp'}
    )

    industry_class_major_code = mapped_column(String(1), nullable=False, comment='大分類')
    industry_class_middle_code = mapped_column(String(2), nullable=False, comment='中分類')
    industry_class_minor_code = mapped_column(String(3), nullable=False, comment='小分類')
    industry_class_detail_code = mapped_column(String(4), nullable=False, comment='細分類')
    benchmark_industry_code = mapped_column(String(50), nullable=False, comment='省エネ法ベンチマーク業種コード')
    floor_area_flag = mapped_column(String(1), nullable=False, comment='延床面積別フラグ')
    target_floor_area_min = mapped_column(Numeric(10, 2), nullable=False, comment='対象延床（以上）')
    industry_class_major_name = mapped_column(String(50), comment='大分類の名称')
    industry_class_middle_name = mapped_column(String(50), comment='中分類の名称')
    industry_class_minor_name = mapped_column(String(50), comment='小分類の名称')
    industry_class_detail_name = mapped_column(String(50), comment='細分類の名称')
    benchmark_industry_name = mapped_column(String(50), comment='省エネ法ベンチマーク業種名')
    competitor_industry = mapped_column(String(50), comment='他社比較業種')
    target_floor_area_max = mapped_column(Numeric(10, 2), comment='対象延床（未満）')
    competitor_industry_year = mapped_column(Integer, comment='他社比較業種_年度')
    competitor_industry_co2_avg = mapped_column(Numeric(6, 2), comment='他社比較業種_CO2排出源単位平均値')
    competitor_industry_data_source = mapped_column(String(50), comment='他社比較業種平均データソース')
    energy_saving_denominator = mapped_column(Numeric(6, 2), comment='省エネ率分母')
    energy_saving_denominator_source = mapped_column(String(50), comment='省エネ率分母データソース')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
