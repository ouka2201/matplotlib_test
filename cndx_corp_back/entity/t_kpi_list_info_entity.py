from sqlalchemy import (
    Boolean,
    DateTime,
    Numeric,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class TKpiListInfo(Base):
    __tablename__ = "t_kpi_list_info"
    __table_args__ = (
        PrimaryKeyConstraint(
            "corporate_number", "agreement_category", "org_id", "building_id",
            name="t_kpi_list_info_pkey"
        ),
        {"comment": "KPI一覧情報", "schema": "db_corp"}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment="法人番号（FK）")
    agreement_category = mapped_column(String(2), nullable=False, comment="同意書取得区分")
    org_id = mapped_column(String(20), nullable=False, comment="組織ID（FK）")
    building_id = mapped_column(String(113), nullable=False, comment="拠点ID（FK）")
    target_period = mapped_column(String(20), comment="対象期間")
    location_identifier_name = mapped_column(String(100), comment="拠点識別名")
    total_floor_area = mapped_column(Numeric(10, 2), comment="延床面積")
    co2_emission_unit = mapped_column(Numeric(10, 4), comment="CO2排出原単位")
    primary_energy = mapped_column(Numeric(15, 2), comment="一次エネルギー")
    energy_saving_rate = mapped_column(Numeric(5, 2), comment="省エネ率")
    electrification_rate = mapped_column(Numeric(5, 2), comment="電化率")
    energy_creation_rate = mapped_column(Numeric(5, 2), comment="創エネ率")
    network_rate = mapped_column(Numeric(5, 2), comment="ﾈｯﾄﾜｰｸ率")
    delete_flg = mapped_column(Boolean, comment="削除フラグ")
    created_by = mapped_column(String(50), comment="作成者")
    created_at = mapped_column(DateTime, comment="作成日時")
    updated_by = mapped_column(String(50), comment="更新者")
    updated_at = mapped_column(DateTime, comment="更新日時")
