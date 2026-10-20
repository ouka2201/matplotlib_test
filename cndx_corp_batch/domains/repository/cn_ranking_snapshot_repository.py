from typing import Iterable

from sqlalchemy.orm import Session

from cndx_corp_batch.common.entity.t_cn_ranking_snapshot import TCnRankingSnapshot


class TCnRankingSnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_creation_id(self, creation_id: str):
        return (
            self.session.query(TCnRankingSnapshot)
            .filter(
                TCnRankingSnapshot.creation_id == creation_id,
                TCnRankingSnapshot.delete_flg.is_(False),
            )
            .all()
        )

    def soft_delete_by_creation_id(self, creation_id: str) -> int:
        """
        論理削除
        Returns:
            更新件数
        """
        result = (
            self.session.query(TCnRankingSnapshot)
            .filter(
                TCnRankingSnapshot.creation_id == creation_id,
                TCnRankingSnapshot.delete_flg.is_(False),
            )
            .update(
                {"delete_flg": True},
                synchronize_session=False,  # session上のORMは更新しないため、前処理の検索対象のdelete_flgはfalseのまま
            )
        )
        return result

    def soft_delete_by_creation_ids(
        self,
        creation_ids: Iterable[str],
    ) -> int:
        """
        creation_id のリストを指定して論理削除する

        Args:
            creation_ids: creation_id の iterable

        Returns:
            更新件数
        """
        if not creation_ids:
            return 0

        result = (
            self.session.query(TCnRankingSnapshot)
            .filter(
                TCnRankingSnapshot.creation_id.in_(creation_ids),
                TCnRankingSnapshot.delete_flg.is_(False),
            )
            .update(
                {"delete_flg": True},
                synchronize_session=False,  # Batch 前提
            )
        )
        return result

    def hard_delete_by_creation_id(self, creation_id: str) -> int:
        """
        物理削除
        Returns:
            削除件数
        """
        result = (
            self.session.query(TCnRankingSnapshot)
            .filter(
                TCnRankingSnapshot.creation_id == creation_id,
            )
            .delete(
                synchronize_session=False,
            )
        )
        return result
