from sqlalchemy import Boolean, Column, DateTime, Numeric, PrimaryKeyConstraint, String,  func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TVisualizationEnergyStorageJfs(Base):
    __tablename__ = 't_visualization_energy_storage_jfs'
    __table_args__ = (
        PrimaryKeyConstraint('corporate_number', 'agreement_category', 'building_id', 'year_month', 'sheet_category_type', 'energy_category_name', 'supply_company', name='t_visualization_energy_storage_jfs_pkey'),
        {'comment': '可視化事業者受領エネルギーの生データ情報（JFS）', 'schema': 'db_corp'}
    )

    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    building_id = mapped_column(String(113), nullable=False, comment='拠点ID（FK）')
    year_month = mapped_column(String(8), nullable=False, comment='年月')
    sheet_category_type = mapped_column(String(1), nullable=False, comment='シート分類区分')
    energy_category_name = mapped_column(String(100), nullable=False, comment='エネルギー分類名')
    supply_company = mapped_column(String(100), nullable=False, comment='供給事業会社名')
    menu_supply_area = mapped_column(String(100), comment='メニュー・供給地域')
    category = mapped_column(String(50), comment='区分')
    unit = mapped_column(String(10), comment='単位')
    usage_amount = mapped_column(Numeric(10, 2), comment='使用量')
    zip_code = mapped_column(String(8), comment='拠点_郵便番号')
    municipality_code = mapped_column(String(5), comment='拠点_自治体コード')
    delete_flag = mapped_column(Boolean, comment='削除フラグ', default=False)
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
