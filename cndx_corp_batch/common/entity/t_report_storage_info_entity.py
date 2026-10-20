from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, PrimaryKeyConstraint, String, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()


class TReportStorageInfo(Base):
    __tablename__ = 't_report_storage_info'
    __table_args__ = (
        PrimaryKeyConstraint('creation_id', 'building_id', 'report_classify', name='t_report_storage_info_pkey'),
        {'comment': 'レポート格納情報', 'schema': 'db_corp'}
    )

    creation_id = mapped_column(String(80), nullable=False, comment='識別子ID')
    building_id = mapped_column(String(113), nullable=False, comment='拠点ID（FK）')
    report_classify = mapped_column(String(2), nullable=False, comment='レポート区分')
    corporate_number = mapped_column(String(13), nullable=False, comment='法人番号（FK）')
    agreement_category = mapped_column(String(2), nullable=False, comment='同意書取得区分')
    org_id = mapped_column(String(20), nullable=False, comment='組織ID（FK）')
    fiscal_year = mapped_column(String(4), nullable=False, comment='年度')
    registration_seq = mapped_column(Integer, nullable=False, comment='登録回数')
    delete_flg = mapped_column(Boolean, nullable=False, server_default=text('false'), comment='削除フラグ')
    group1 = mapped_column(String(20), comment='グループ1')
    group2 = mapped_column(String(20), comment='グループ2')
    group3 = mapped_column(String(20), comment='グループ3')
    group4 = mapped_column(String(20), comment='グループ4')
    group5 = mapped_column(String(20), comment='グループ5')
    group1_id = mapped_column(String(2), comment='グループ1_id')
    group2_id = mapped_column(String(2), comment='グループ2_id')
    option1_id = mapped_column(String(2), comment='オプション1_id')
    option2_id = mapped_column(String(2), comment='オプション2_id')
    report_save_path = mapped_column(String(200), comment='レポート格納先')
    report_status = mapped_column(String(2), comment='ステータス')
    report_selection_period_from = mapped_column(String(6), comment='選択期間（開始）')
    format_type = mapped_column(String(20), comment='フォーマットタイプ')
    site_selection_type = mapped_column(String(30), comment='拠点選択タイプ')
    report_created_at = mapped_column(TIMESTAMP(precision=6), comment='レポート作成年月日')
    report_created_by = mapped_column(String(50), comment='レポート作成者')
    created_by = mapped_column(String(50), comment='作成者')
    created_at = mapped_column(DateTime, comment='作成日時', default=func.now())
    updated_by = mapped_column(String(50), comment='更新者')
    updated_at = mapped_column(DateTime, comment='更新日時', onupdate=func.now())
    target_month = mapped_column(String(6), comment='対象月')
    png_bytes = mapped_column(LargeBinary, comment='レポート図バイナリ')
    batch_id = mapped_column(String(50), comment='バッチid')
