from sqlalchemy import text

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.jobs.base import BaseJob


class DeleteEpPowerJob(BaseJob):
    """
    EPデータ参照基盤契約電力削除JOB

    Attributes:
        BaseJob (BaseJob)
    """

    def __init__(self, context: BatchContext):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
        """
        super().__init__(context)
        self.context = context

    def execute(self):
        """EPデータ参照基盤契約電力削除実行"""
        logger = self.logger

        logger.info("EPデータ参照基盤契約電力データ削除処理開始。")

        # EPデータ参照基盤契約電力削除
        with get_session() as session:
            sql_query = load_sql_file("truncate_t_ep_contracted_power.sql")
            session.execute(text(sql_query))
            session.commit()

        logger.info("EPデータ参照基盤契約電力データ削除処理完了。")
