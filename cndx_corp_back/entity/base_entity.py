from datetime import datetime

from sqlalchemy.types import Numeric

from cndx_corp_back.ext import db


class BaseEntity(db.Model):
    """
    全てのエンティティクラスの基底クラス
    """

    __abstract__ = True

    def to_dict(self):
        def convert_value(value):
            if isinstance(value, (int, str, bool)):
                return value
            elif isinstance(value, (float, Numeric)):
                return float(value) if value is not None else None
            elif isinstance(value, datetime):
                return value.isoformat() if value is not None else None
            return value

        return {
            c.name: convert_value(getattr(self, c.name)) for c in self.__table__.columns
        }
