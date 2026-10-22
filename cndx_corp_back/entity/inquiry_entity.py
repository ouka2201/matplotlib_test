from dataclasses import dataclass

from sqlalchemy import Column, Integer, String, inspect

from cndx_corp_back import db


@dataclass
class Inquiry(db.Model):
    """
    調査表エンティティ
    """

    __tablename__ = "inquiries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    reportingYear = Column("reportingyear", String)
    companyName = Column("companyname", String)
    deploymentName = Column("deploymentname", String)
    reptName = Column("reptname", String)
    internalNumber = Column("internalnumber", String)
    industryClassification = Column("industryclassification", String)
    electricitySupply = Column("electricitysupply", String)
    gasBusinessName = Column("gasbusinessname", String)
    otherGasBusinessName = Column("othergasbusinessname", String)

    def to_dict(self):
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
