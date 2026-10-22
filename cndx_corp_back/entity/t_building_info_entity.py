from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TBuildingInfo(Base):
    __tablename__ = 't_building_info'
    __table_args__ = (
        PrimaryKeyConstraint('corporate_number', 'agreement_category', 'org_id', 'building_id', 'registration_seq', 'fiscal_year', name='t_building_info_pkey'),
        {'comment': '建物情報', 'schema': 'db_corp'}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID（FK）')
    building_id = mapped_column(String(113), nullable=False, comment='拠点ID')
    registration_seq = mapped_column(Integer, nullable=False, comment='登録回数')
    fiscal_year = mapped_column(String(4), nullable=False, comment='年度')
    supply_point_number = mapped_column(String(22), comment='供給地点特定番号')
    entry_draft_flag = mapped_column(String(1), comment='登録下書区分')
    location_identifier_name = mapped_column(String(100), comment='拠点識別名')
    zip_code = mapped_column(String(8), comment='郵便番号')
    municipality_code = mapped_column(String(5), comment='自治体コード')
    address_prefecture = mapped_column(String(20), comment='住所（都道府県）')
    address_city = mapped_column(String(100), comment='住所（市区町村）')
    industry_class_major_code = mapped_column(String(1), comment='日本標準産業分類（大分類）')
    industry_class_middle_code = mapped_column(String(2), comment='日本標準産業分類（中分類）')
    industry_class_minor_code = mapped_column(String(3), comment='日本標準産業分類（小分類）')
    industry_class_detail_code = mapped_column(String(4), comment='日本標準産業分類（細分類）')
    industry_class_major_name = mapped_column(String(50), comment='日本標準産業分類名称（大分類）')
    industry_class_middle_name = mapped_column(String(50), comment='日本標準産業分類名称（中分類）')
    industry_class_minor_name = mapped_column(String(50), comment='日本標準産業分類名称（小分類）')
    industry_class_detail_name = mapped_column(String(50), comment='日本標準産業分類名称（細分類）')
    energy_benchmark_target_industry = mapped_column(String(50), comment='省エネ法ベンチマーク対象業種')
    energy_benchmark_indicator = mapped_column(String(100), comment='省エネ法ベンチマーク指標')
    energy_benchmark_year = mapped_column(String(4), comment='省エネ法ベンチマーク指標年度')
    gross_floor_area = mapped_column(Numeric(8, 2), comment='延床面積')
    electricity_supplier_no = mapped_column(String(10), comment='契約先電気事業者登録番号')
    electricity_supplier_name = mapped_column(String(50), comment='契約先電気事業者')
    electricity_contract_menu = mapped_column(String(50), comment='契約先電力メニュー')
    ep_office_code = mapped_column(String(3), comment='EP事業所コード')
    ep_customer_number = mapped_column(String(13), comment='EPお客さま番号')
    city_gas_supplier_no = mapped_column(String(10), comment='契約先都市ガス供給事業者登録番号')
    city_gas_supplier_name = mapped_column(String(50), comment='契約先都市ガス供給事業者')
    heat_supplier_no = mapped_column(String(10), comment='契約先熱供給事業者登録番号')
    heat_supplier_name = mapped_column(String(50), comment='契約先熱供給事業者')
    heat_contract_menu = mapped_column(String(50), comment='契約先熱メニュー')
    delete_flg = mapped_column(Boolean, comment='削除フラグ',default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
    competitor_industry_co2_avg = mapped_column(Numeric(6, 4), comment='他社比較業種_CO2排出源単位平均値')
    energy_saving_denominator = mapped_column(Numeric(22, 17), comment='省エネ率分母')