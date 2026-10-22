from sqlalchemy import Column, Numeric, PrimaryKeyConstraint, SmallInteger, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class ElectricSupplierMenuMst(Base):
    __tablename__ = 'electric_supplier_menu_mst'
    __table_args__ = (
        PrimaryKeyConstraint(
            "electric_company_reg_no",
            "report_year",
            "publication_count",
            "menu_no",
            name="electric_supplier_menu_mst_pkey",
        ),
        {"comment": "電気事業者メニュー別マスタ", "schema": "db_common"},
    )

    electric_company_reg_no = mapped_column(String(5), nullable=False)
    report_year = mapped_column(SmallInteger, nullable=False)
    publication_count = mapped_column(SmallInteger, nullable=False)
    menu_no = mapped_column(SmallInteger, nullable=False)
    menu_nm = mapped_column(String(50), nullable=False)
    base_emission_coef = mapped_column(Numeric(7, 6))
    adjusted_emission_coef = mapped_column(Numeric(7, 6))
    fossil_free_cert_usage = mapped_column(Numeric(5, 2))
    delete_flag = mapped_column(SmallInteger)
    insert_name = mapped_column(String(50))
    insert_datetime = mapped_column(TIMESTAMP(precision=6))
    update_name = mapped_column(String(50))
    update_datetime = mapped_column(TIMESTAMP(precision=6))
