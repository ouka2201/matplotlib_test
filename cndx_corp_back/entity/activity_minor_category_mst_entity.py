from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class ActivityMinorCategoryMst(Base):
    __tablename__ = 'activity_minor_category_mst'
    __table_args__ = (
        PrimaryKeyConstraint(
            "report_year",
            "major_category_id",
            "middle_category_id",
            "minor_category_id",
            name="activity_minor_category_mst_pkey",
        ),
        {"comment": "活動項目小分類（事業者）マスタ", "schema": "db_common"},
    )

    report_year = mapped_column(SmallInteger, nullable=False, comment='報告年度')
    major_category_id = mapped_column(String(2), nullable=False, comment='活動項目大分類ID')
    middle_category_id = mapped_column(String(4), nullable=False, comment='活動項目中分類ID')
    minor_category_id = mapped_column(String(4), nullable=False, comment='活動項目小分類ID')
    minor_category_nm = mapped_column(String(100), comment='活動項目小分類名')
    unit = mapped_column(String(10), comment='単位')
    conversion_coef = mapped_column(Numeric(5, 2), comment='換算係数')
    non_fossil_conv_coef = mapped_column(Numeric(5, 2), comment='非化石エネルギー転換換算係数')
    non_fossil_weight_coef = mapped_column(Numeric(5, 2), comment='非化石重み付け係数')
    electric_demand_opt_coef = mapped_column(Numeric(5, 2), comment='電気需要最適化換算係数')
    energy_co2_emission_coef = mapped_column(Numeric(7, 6), comment='排出係数（エネ起CO2）')
    non_energy_co2_emission_coef = mapped_column(Numeric(7, 6), comment='排出係数（非エネ起CO2）')
    ch4_emission_coef = mapped_column(Numeric(12, 10), comment='排出係数（CH4）')
    n2o_emission_coef = mapped_column(Numeric(12, 10), comment='排出係数（N2O）')
    hfc_emission_coef = mapped_column(Numeric(12, 10), comment='排出係数（HFC）')
    pfc_emission_coef = mapped_column(Numeric(12, 10), comment='排出係数（PFC）')
    sf6_emission_coef = mapped_column(Numeric(12, 10), comment='排出係数（SF6）')
    nf3_emission_coef = mapped_column(Numeric(12, 10), comment='排出係数（NF3）')
    conversion_value1 = mapped_column(SmallInteger, comment='変換値１')
    conversion_value2 = mapped_column(SmallInteger, comment='変換値２')
    non_energy_kbn = mapped_column(SmallInteger, comment='非エネルギー区分')
    global_warming_law_flag = mapped_column(SmallInteger, comment='温対法フラグ')
    energy_efficiency_law_flag = mapped_column(SmallInteger, comment='省エネ法フラグ')
    activity_item_screen_flag = mapped_column(SmallInteger, comment='活動項目選択画面表示フラグ')
    support_screen_kbn = mapped_column(String(2), comment='補助画面表示区分')
    unit_input_enabled_flag = mapped_column(SmallInteger, comment='単位入力可否フラグ')
    conversion_coef_input_flag = mapped_column(SmallInteger, comment='換算係数入力可否フラグ')
    usage_input_enabled_flag = mapped_column(SmallInteger, comment='使用量入力可否フラグ')
    by_product_input_enabled_flag = mapped_column(SmallInteger, comment='販売副生入力可否フラグ')
    unused_heat_input_enabled_flag = mapped_column(SmallInteger, comment='購入未利用熱入力可否フラグ')
    activity_max_limit = mapped_column(Numeric(3, 1), comment='活動量最大値')
    activity_min_limit = mapped_column(Numeric(3, 1), comment='活動量最小値')
    activity_item_comment = mapped_column(String(200), comment='活動項目コメント')
    heat_support_screen_flag = mapped_column(SmallInteger, comment='熱関係補助画面表示フラグ')
    electricity_support_screen_flag = mapped_column(SmallInteger, comment='電気関係補助画面表示フラグ')
    non_fossil_kbn = mapped_column(SmallInteger, comment='化石・非化石区分')
    self_generation_screen_flag = mapped_column(SmallInteger, comment='自家発電（他事業所からの供給）画面表示フラグ')
    display_order = mapped_column(String(4), comment='表示順')
    start_date = mapped_column(String(8), comment='有効開始日')
    end_date = mapped_column(String(8), comment='有効終了日')
    delete_flag = mapped_column(Boolean, comment='削除フラグ')
    created_by = mapped_column(String(50), comment='登録者')
    created_at = mapped_column(DateTime, comment='登録日時')
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時')
