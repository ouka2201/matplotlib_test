from sqlalchemy import DateTime, Integer, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class TEpContractedPower(Base):
    __tablename__ = "t_ep_contracted_power"
    __table_args__ = (
        PrimaryKeyConstraint(
            "qsqb_dcis2_spl_pt_spc_no", name="t_ep_contracted_power_pkey"
        ),
        {"comment": "EPデータ参照基盤契約電力", "schema": "db_corp"},
    )

    qsqb_dcis2_spl_pt_spc_no = mapped_column(
        String(22), primary_key=True, comment="供給(受電)地点特定番号"
    )
    qsqb_dcis2_hvpw_ctrt = mapped_column(
        Integer, nullable=False, comment="高圧契約電力(kW)"
    )
    created_by = mapped_column(String(50), nullable=False, comment="作成者")
    created_at = mapped_column(
        DateTime, nullable=False, comment="作成日時", default=func.now()
    )
    updated_by = mapped_column(String(50), comment="更新者")
    updated_at = mapped_column(DateTime, comment="更新日時")
