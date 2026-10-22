from dataclasses import dataclass
import datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, Numeric, String

from .. import db
from .base_entity import BaseEntity

class MUser(BaseEntity):
    """
    ユーザーマスタエンティティ
    """
    __tablename__ = "m_user"
    __table_args__ = {"schema": "db_corp"}  # スキーマを指定

    user_id = Column(String(100), primary_key=True, comment="ユーザーID")
    user_name = Column(String(10), nullable=False, comment="ユーザー名")
    company_name = Column(String(100), nullable=False, comment="会社名")
    department_id = Column(String(8), nullable=False, comment="部門ID")
    department_name = Column(String(10), nullable=False, comment="部門名")
    user_password = Column(String(100), nullable=False, comment="パスワード")
    org_id = Column(String(20), nullable=True, comment="組織ID（FK）")
    user_role = Column(String(10), nullable=True, comment="ロール")
    start_date = Column(TIMESTAMP, nullable=True, comment="有効開始日")
    end_date = Column(TIMESTAMP, nullable=True, comment="有効終了日")
    delete_flg = Column(Boolean, nullable=True, comment="削除フラグ")
    created_by = Column(String(50), nullable=True, comment="作成者")
    created_at = Column(TIMESTAMP, nullable=True, comment="作成日時")
    updated_by = Column(String(50), nullable=True, comment="更新者")
    updated_at = Column(TIMESTAMP, nullable=True, comment="更新日時")

    __table_args__ = {"comment": "ユーザーマスタ"}

