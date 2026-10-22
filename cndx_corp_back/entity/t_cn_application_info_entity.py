from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, PrimaryKeyConstraint, SmallInteger, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TCnApplicationInfo(Base):
    __tablename__ = 't_cn_application_info'
    __table_args__ = (
        PrimaryKeyConstraint('corporate_number', 'agreement_category', 'org_id', 'fiscal_year', 'registration_seq', name='t_cn_application_info_pkey'),
        {'comment': 'CN対策実施申込情報', 'schema': 'db_corp'}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID（FK）')
    fiscal_year = mapped_column(String(4), nullable=False, comment='年度')
    registration_seq = mapped_column(Integer, nullable=False, comment='登録回数')
    company_name = mapped_column(String(50), comment='企業名')
    entry_draft_flag = mapped_column(String(1), comment='登録下書区分')
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
    address_prefecture = mapped_column(String(20), comment='本社住所(都道府県)')
    address_city = mapped_column(String(100), comment='本社住所(市区町村)')
    report_period_start_year_month = mapped_column(String(6), comment='レポート作成対象期間開始年月')
    report_period_end_year_month = mapped_column(String(6), comment='レポート作成対象期間終了年月')
    competitor_industry_co2_avg = mapped_column(Numeric(6, 4), comment='他社比較業種_CO2排出源単位平均値')
    energy_saving_denominator = mapped_column(Numeric(6, 4), comment='省エネ率分母')
    kpi_target_energy_saving_rate = mapped_column(Numeric(5, 2), comment='KPI目標値・省エネ率')
    kpi_target_electrification_rate = mapped_column(Numeric(5, 2), comment='KPI目標値・電化率')
    kpi_target_energy_creation = mapped_column(Numeric(5, 2), comment='KPI目標値・創エネ')
    kpi_target_renewable_network_rate = mapped_column(Numeric(5, 2), comment='KPI目標値・再エネ・ネットワーク率')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
