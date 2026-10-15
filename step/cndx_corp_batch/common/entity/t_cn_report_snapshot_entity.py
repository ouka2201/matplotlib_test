from sqlalchemy import Boolean, Column, Integer, Numeric, PrimaryKeyConstraint, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class TCnReportSnapshot(Base):
    __tablename__ = 't_cn_report_snapshot'
    __table_args__ = (
        PrimaryKeyConstraint('creation_id', 'year_month', 'year_flg', name='t_cn_report_snapshot_pkey'),
        {'comment': 'レポート作成要求（出力条件・KPI・積み上げ内訳）', 'schema': 'db_corp'}
    )

    creation_id = mapped_column(String(80), nullable=False, comment='識別子')
    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID')
    fiscal_year = mapped_column(String(4), nullable=False, comment='年度')
    registration_seq = mapped_column(Integer, nullable=False, comment='登録回数')
    year_month = mapped_column(String(6), nullable=False, comment='対象年月')
    month_flg = mapped_column(Numeric(2, 0), nullable=False, server_default=text('0'), comment='月度フラグ')
    year_flg = mapped_column(Numeric(2, 0), nullable=False, server_default=text('0'), comment='年度フラグ')
    is_for_bnk = mapped_column(Boolean, nullable=False, server_default=text('true'), comment='地銀/可視化')
    need_data_insufficiency_list = mapped_column(Boolean, nullable=False, server_default=text('false'), comment='データ欠損一覧（pdf）')
    need_report_backdata = mapped_column(Boolean, nullable=False, server_default=text('false'), comment='レポートバックデータ（csv）')
    need_kpi_list = mapped_column(Boolean, nullable=False, server_default=text('false'), comment='KPI一覧（csv）')
    created_at = mapped_column(TIMESTAMP(precision=6), nullable=False, server_default=text('now()'), comment='作成日時')
    report_selection_period_from = mapped_column(String(6), comment='期間選択（開始）')
    report_selection_period_to = mapped_column(String(6), comment='期間選択（終了）')
    format_type = mapped_column(String(20), comment='作成レポート選択')
    group_condition_1 = mapped_column(String(30), comment='グループ条件1')
    group_condition_2 = mapped_column(String(30), comment='グループ条件2')
    renewable_energy_procurement_current = mapped_column(Numeric(10, 6), comment='再エネ調達量_今年度')
    total_energy_use_current = mapped_column(Numeric(10, 6), comment='エネルギー消費量総量_今年度')
    renewable_energy_procurement_last = mapped_column(Numeric(10, 6), comment='再エネ調達量_前年度')
    total_energy_use_last = mapped_column(Numeric(10, 6), comment='エネルギー消費量総量_前年度')
    kpi_energy_saving_rate = mapped_column(Numeric(10, 6), comment='省エネ率実績割合(%)')
    kpi_electrification_rate = mapped_column(Numeric(10, 6), comment='電化率実績割合(%)')
    kpi_energy_creation_rate = mapped_column(Numeric(10, 6), comment='創エネ率実績割合(%)')
    kpi_renewable_network_rate = mapped_column(Numeric(10, 6), comment='CN外部調達比率(%)')
    cn_zeb_total_tco2_result = mapped_column(Numeric(10, 5), comment='合計（ZEB/内訳合計）')
    cn_zeb_credit_certificate = mapped_column(Numeric(10, 5), comment='証書・クレジット')
    cn_zeb_renewable_electric_power = mapped_column(Numeric(10, 5), comment='再エネ発電導入')
    cn_zeb_emission_factor_improvement = mapped_column(Numeric(10, 5), comment='排出係数の改善')
    delete_flg = mapped_column(Boolean, comment='削除フラグ')
    created_by = mapped_column(String(50), comment='作成者')
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(TIMESTAMP(precision=6), comment='更新日時')
