from sqlalchemy import DateTime, PrimaryKeyConstraint, String, func
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class TArveCustomerInfo(Base):
    __tablename__ = "t_arve_customer_info"
    __table_args__ = (
        PrimaryKeyConstraint(
            "cmn_supplypointspecificnum__c", name="t_arve_customer_info_pkey"
        ),
        {"comment": "ARVEお客さま情報", "schema": "db_corp"},
    )

    cmn_supplypointspecificnum__c = mapped_column(
        String(22), primary_key=True, comment="供給地点特定番号(FK)"
    )
    cmn_businesstype__c = mapped_column(String(4), comment="業務種別")
    cmn_oldcustomernum__c = mapped_column(String(16), comment="お客さま番号")
    cmn_powercontract__c = mapped_column(String(10), comment="契約電力(kW)")
    cmn_contracttype__c = mapped_column(String(1300), comment="契約種別")
    cmn_demandlocationaddress__c = mapped_column(String(1300), comment="契約場所_住所")
    cmn_linkedsourcecontractitem__c = mapped_column(
        String(18), comment="紐づけ元契約商品"
    )
    cmn_oldjuyobasho__c = mapped_column(String(18), comment="旧契約需要場所")
    cmn_acutualmaterreadingdate__c = mapped_column(String(2), comment="計量日")
    cmn_contractenddate2__c = mapped_column(String(10), comment="契約終了日")
    cmn_contractstatus__c = mapped_column(String(5), comment="契約状態")
    cmn_demandlocationfullname_ref__c = mapped_column(
        String(1300), comment="契約場所_名義(姓)＿契約場所_名義(名)"
    )
    cmn_kigyoid_fk__c = mapped_column(String(1300), comment="企業ID")
    cmn_salescontactaccount__c = mapped_column(
        String(1300), comment="営業窓口アカウント"
    )
    cmn_user_performanceaccountabilityrep__c = mapped_column(
        String(1300), comment="実績責任担当者"
    )
    org_id = mapped_column(String(20), comment="組織ID（FK）")
    user_org_name = mapped_column(String(1300), comment="担当組織")
    recordtypeid = mapped_column(String(20), comment="レコードタイプ ID")
    okyakusamabango14__c = mapped_column(String(14), comment="お客様番号(14桁)")
    sagyokenmeibango__c = mapped_column(String(1300), comment="作業件名番号")
    status__c = mapped_column(String(20), comment="ステータス")
    created_by = mapped_column(String(50), nullable=False, comment="作成者")
    created_at = mapped_column(
        DateTime, nullable=False, comment="作成日時", default=func.now()
    )
    updated_by = mapped_column(String(50), comment="更新者")
    updated_at = mapped_column(DateTime, comment="更新日時")
