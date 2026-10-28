from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class TElectricityData30min(Base):
    __tablename__ = 't_electricity_data_30min'
    __table_args__ = (
        PrimaryKeyConstraint('corp_number', 'agreement_category', 'org_id', 'building_id', 'acquisition_date', name='t_electricity_data_30min_pkey'),
        {'comment': '30分値の生データ情報', 'schema': 'db_corp'}
    )

    corp_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False)
    org_id = mapped_column(String(20), nullable=False)
    building_id = mapped_column(String(113), nullable=False, comment='拠点ID（FK）')
    supply_point_number = mapped_column(String(27), nullable=False, comment='供給地点特定番号')
    acquisition_date = mapped_column(String(8), nullable=False, comment='取得_年月日')
    corp_name = mapped_column(String(100), comment='お客さま名')
    building_name = mapped_column(String(100), comment='建物名')
    arve_corp_name = mapped_column(String(1300), comment='ARVE連携お客さま名')
    arve_office_code = mapped_column(String(3), comment='ARVE連携事業所コード')
    arve_customer_number = mapped_column(String(16), comment='ARVE連携お客さま番号')
    ep_customer_number = mapped_column(String(16), comment='EPお客さま番号')
    company_id = mapped_column(String(14), comment='企業ID')
    missing_time_range_count = mapped_column(Integer, comment='欠測時間帯_件数')
    invalid_time_range_count = mapped_column(Integer, comment='不正値時間帯_件数')
    v30min_used_energy_1 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_1')
    v30min_used_energy_2 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_2')
    v30min_used_energy_3 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_3')
    v30min_used_energy_4 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_4')
    v30min_used_energy_5 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_5')
    v30min_used_energy_6 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_6')
    v30min_used_energy_7 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_7')
    v30min_used_energy_8 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_8')
    v30min_used_energy_9 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_9')
    v30min_used_energy_10 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_10')
    v30min_used_energy_11 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_11')
    v30min_used_energy_12 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_12')
    v30min_used_energy_13 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_13')
    v30min_used_energy_14 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_14')
    v30min_used_energy_15 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_15')
    v30min_used_energy_16 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_16')
    v30min_used_energy_17 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_17')
    v30min_used_energy_18 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_18')
    v30min_used_energy_19 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_19')
    v30min_used_energy_20 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_20')
    v30min_used_energy_21 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_21')
    v30min_used_energy_22 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_22')
    v30min_used_energy_23 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_23')
    v30min_used_energy_24 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_24')
    v30min_used_energy_25 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_25')
    v30min_used_energy_26 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_26')
    v30min_used_energy_27 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_27')
    v30min_used_energy_28 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_28')
    v30min_used_energy_29 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_29')
    v30min_used_energy_30 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_30')
    v30min_used_energy_31 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_31')
    v30min_used_energy_32 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_32')
    v30min_used_energy_33 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_33')
    v30min_used_energy_34 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_34')
    v30min_used_energy_35 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_35')
    v30min_used_energy_36 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_36')
    v30min_used_energy_37 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_37')
    v30min_used_energy_38 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_38')
    v30min_used_energy_39 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_39')
    v30min_used_energy_40 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_40')
    v30min_used_energy_41 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_41')
    v30min_used_energy_42 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_42')
    v30min_used_energy_43 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_43')
    v30min_used_energy_44 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_44')
    v30min_used_energy_45 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_45')
    v30min_used_energy_46 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_46')
    v30min_used_energy_47 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_47')
    v30min_used_energy_48 = mapped_column(Numeric(10, 4), comment='V30分_使用_電力量_48')
    file_update_date = mapped_column(DateTime, comment='ファイル更新日時')
    delete_flg = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
