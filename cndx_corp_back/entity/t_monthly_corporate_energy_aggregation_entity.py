from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TMonthlyCorporateEnergyAggregation(Base):
    __tablename__ = 't_monthly_corporate_energy_aggregation'
    __table_args__ = (
        PrimaryKeyConstraint('corporate_number', 'agreement_category', 'org_id', 'energy_code', 'target_year_month', 'registration_seq', name='t_monthly_corporate_energy_aggregation_pkey'),
        {'comment': '月別法人エネルギー集計情報', 'schema': 'db_corp'}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID（FK）')
    energy_code = mapped_column(String(20), nullable=False, comment='エネルギ―コード')
    target_year_month = mapped_column(String(6), nullable=False, comment='対象年月')
    registration_seq = mapped_column(Integer, nullable=False, comment='登録回数')
    fiscal_year = mapped_column(String(4), comment='登录年度')
    energy_category_name = mapped_column(String(100), comment='エネルギー名')
    energy_name_for_coefficient_matching = mapped_column(String(100), comment='エネルギ―名称（係数突合用）')
    energy_quantity_for_law = mapped_column(Numeric(25, 10), comment='エネルギー使用量（省エネ法）')
    energy_usage_area_unit = mapped_column(Numeric(25, 10), comment='エネルギー使用量原単位')
    energy_unit_for_law = mapped_column(String(20), comment='エネルギー使用量単位（省エネ法）')
    energy_quantity = mapped_column(Numeric(25, 10), comment='エネルギー使用量（元データ）')
    energy_unit_original = mapped_column(String(20), comment='エネルギー使用量単位（元データ）')
    energy_quantity_for_report = mapped_column(Numeric(25, 10), comment='エネルギー使用量（レポート）')
    energy_unit_for_report = mapped_column(String(20), comment='エネルギー使用量単位（レポート）')
    supplier_name = mapped_column(String(100), comment='供給事業者名')
    supply_menu = mapped_column(String(100), comment='供給メニュー')
    supply_conditions = mapped_column(String(100), comment='供給条件')
    heat_converted_energy_usage = mapped_column(Numeric(25, 10), comment='熱量換算エネルギー使用量')
    heat_converted_energy_usage_area_unit = mapped_column(Numeric(25, 10), comment='熱量換算エネルギー使用量原単位')
    heat_converted_energy_unit = mapped_column(String(20), comment='熱量換算エネルギー使用量単位')
    heat_conversion_coefficient = mapped_column(Numeric(10, 6), comment='熱量換算係数')
    heat_conversion_coefficient_source = mapped_column(String(100), comment='熱量換算係数データソース')
    heat_conversion_coefficient_unit = mapped_column(String(20), comment='熱量換算係数単位')
    co2_base_emissions = mapped_column(Numeric(18, 10), comment='CO2基礎排出量')
    co2_base_emissions_unit = mapped_column(String(20), comment='CO2基礎排出量単位')
    co2_base_emission_factor = mapped_column(Numeric(10, 6), comment='CO2基礎排出係数')
    co2_base_emission_factor_unit = mapped_column(String(20), comment='CO2基礎排出係数単位')
    co2_adjusted_emissions = mapped_column(Numeric(18, 10), comment='CO2調整後排出量')
    co2_adjusted_emissions_unit = mapped_column(String(20), comment='CO2調整後排出量単位')
    co2_adjusted_emissions_area_unit = mapped_column(Numeric(18, 10), comment='CO2調整後排出量原単位')
    co2_adjusted_emission_factor = mapped_column(Numeric(10, 6), comment='CO2調整後排出係数')
    co2_adjusted_emission_factor_source = mapped_column(String(100), comment='CO2調整後排出係数データソース')
    co2_adjusted_emission_factor_unit = mapped_column(String(20), comment='CO2調整後排出係数単位')
    credit_certificate_purchase_energy_amount = mapped_column(Numeric(25, 10), comment='証書・クレジット購入量（エネルギー量）')
    credit_certificate_unit = mapped_column(String(20), comment='証書・クレジット単位')
    credit_certificate_purchase_tco2_amount = mapped_column(Numeric(25, 10), comment='証書・クレジット購入量（tｰCO2）')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
