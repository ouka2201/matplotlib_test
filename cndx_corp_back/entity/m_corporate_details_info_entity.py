from sqlalchemy import Boolean, DateTime, PrimaryKeyConstraint, SmallInteger, String, func
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class MCorporateDetailsInfo(Base):
    __tablename__ = 'm_corporate_details_info'
    __table_args__ = (
        PrimaryKeyConstraint('corporate_number', 'agreement_category', 'org_id', name='m_corporate_details_info_pkey'),
        {'comment': '企業詳細情報マスタ', 'schema': 'db_corp'}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(15), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID（FK）')
    ghg_system_company_name = mapped_column(String(50), comment='GHG排出量算定システム会社名')
    industry_class_major_code = mapped_column(String(1), comment='日本標準産業分類（大分類）')
    industry_class_middle_code = mapped_column(String(2), comment='日本標準産業分類（中分類）')
    industry_class_minor_code = mapped_column(String(3), comment='日本標準産業分類（小分類）')
    industry_class_detail_code = mapped_column(String(4), comment='日本標準産業分類（細分類）')
    industry_class_major_name = mapped_column(String(50), comment='日本標準産業分類名称（大分類）')
    industry_class_middle_name = mapped_column(String(50), comment='日本標準産業分類名称（中分類）')
    industry_class_minor_name = mapped_column(String(50), comment='日本標準産業分類名称（小分類）')
    industry_class_detail_name = mapped_column(String(50), comment='日本標準産業分類名称（細分類）')
    business_office_count = mapped_column(SmallInteger, comment='事業所数')
    energy_benchmark_target_industry = mapped_column(String(50), comment='省エネ法ベンチマーク対象業種')
    energy_benchmark_indicator = mapped_column(String(100), comment='省エネ法ベンチマーク指標')
    energy_benchmark_year = mapped_column(String(4), comment='省エネ法ベンチマーク指標年度')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
