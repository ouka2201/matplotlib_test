from typing import Iterable

from sqlalchemy.orm import Session

from cndx_corp_batch.common.entity.m_building_entity import MBuilding


class MBuildingRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_corpnumber(self, corporate_number: str, org_id: str):
        return (
            self.session.query(MBuilding)
            .filter(
                MBuilding.corporate_number == corporate_number,
                MBuilding.agreement_org == org_id,
                MBuilding.delete_flg.is_(False),
            )
            .all()
        )

    def find_by_conditions(self, *filters):
        query = self.session.query(MBuilding).filter(*filters)

        sql = str(
            query.statement.compile(
                dialect=self.session.bind.dialect,
                compile_kwargs={"literal_binds": True},
            )
        )

        # print(sql)

        return self.session.query(MBuilding).filter(*filters).all()
