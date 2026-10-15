from sqlalchemy.orm import Session

from cndx_corp_batch.common.entity.m_corporate_basic_entity import MCorporateBasic


class MCorpBasicRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_corpnumber(self, corporate_number: str):
        return (
            self.session.query(MCorporateBasic)
            .filter(
                MCorporateBasic.corporate_number == corporate_number,
                MCorporateBasic.delete_flg.is_(False),
            )
            .one()
        )
