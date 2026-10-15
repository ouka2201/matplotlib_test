from sqlalchemy import DateTime, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class TEpElectricityData30min(Base):
    __tablename__ = "t_ep_electricity_data_30min"
    __table_args__ = (
        PrimaryKeyConstraint(
            "t01_kyo_ctn_tok_no", "t01_get_ymd", name="t_ep_electricity_data_30min_pkey"
        ),
        {"comment": "EPデータ参照基盤30分値", "schema": "db_corp"},
    )

    t01_kyo_ctn_tok_no = mapped_column(
        String(22), primary_key=True, comment="供給地点特定番号(FK)"
    )
    t01_get_ymd = mapped_column(String(8), primary_key=True, comment="取得年月日")
    t01_kskj_ksu = mapped_column(String(2), nullable=False, comment="欠測時間帯件数")
    t01_fsij_ksu = mapped_column(String(2), nullable=False, comment="不正値時間帯件数")
    t01_30t_syr01 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（1）"
    )
    t01_30t_syr02 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（2）"
    )
    t01_30t_syr03 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（3）"
    )
    t01_30t_syr04 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（4）"
    )
    t01_30t_syr05 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（5）"
    )
    t01_30t_syr06 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（6）"
    )
    t01_30t_syr07 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（7）"
    )
    t01_30t_syr08 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（8）"
    )
    t01_30t_syr09 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（9）"
    )
    t01_30t_syr10 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（10）"
    )
    t01_30t_syr11 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（11）"
    )
    t01_30t_syr12 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（12）"
    )
    t01_30t_syr13 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（13）"
    )
    t01_30t_syr14 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（14）"
    )
    t01_30t_syr15 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（15）"
    )
    t01_30t_syr16 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（16）"
    )
    t01_30t_syr17 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（17）"
    )
    t01_30t_syr18 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（18）"
    )
    t01_30t_syr19 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（19）"
    )
    t01_30t_syr20 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（20）"
    )
    t01_30t_syr21 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（21）"
    )
    t01_30t_syr22 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（22）"
    )
    t01_30t_syr23 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（23）"
    )
    t01_30t_syr24 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（24）"
    )
    t01_30t_syr25 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（25）"
    )
    t01_30t_syr26 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（26）"
    )
    t01_30t_syr27 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（27）"
    )
    t01_30t_syr28 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（28）"
    )
    t01_30t_syr29 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（29）"
    )
    t01_30t_syr30 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（30）"
    )
    t01_30t_syr31 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（31）"
    )
    t01_30t_syr32 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（32）"
    )
    t01_30t_syr33 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（33）"
    )
    t01_30t_syr34 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（34）"
    )
    t01_30t_syr35 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（35）"
    )
    t01_30t_syr36 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（36）"
    )
    t01_30t_syr37 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（37）"
    )
    t01_30t_syr38 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（38）"
    )
    t01_30t_syr39 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（39）"
    )
    t01_30t_syr40 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（40）"
    )
    t01_30t_syr41 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（41）"
    )
    t01_30t_syr42 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（42）"
    )
    t01_30t_syr43 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（43）"
    )
    t01_30t_syr44 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（44）"
    )
    t01_30t_syr45 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（45）"
    )
    t01_30t_syr46 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（46）"
    )
    t01_30t_syr47 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（47）"
    )
    t01_30t_syr48 = mapped_column(
        String(9), nullable=False, comment="30分使用電力量（48）"
    )
    created_by = mapped_column(String(50), nullable=False, comment="作成者")
    created_at = mapped_column(
        DateTime, nullable=False, comment="作成日時", default=func.now()
    )
    updated_by = mapped_column(String(50), comment="更新者")
    updated_at = mapped_column(DateTime, comment="更新日時")
