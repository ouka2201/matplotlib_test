from sqlalchemy import insert

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.dto.ep_electricity_data_30min_dto import (
    EpElectricityData30minDto,
)
from cndx_corp_batch.common.entity.t_ep_electricity_data_30min_entity import (
    TEpElectricityData30min,
)
from cndx_corp_batch.jobs.base import BaseJob


class ImportEpElectricityData30min(BaseJob):
    """EPデータ参照基盤30分値登録JOB

    Args:
        BaseJob (BaseJob)
    """

    def __init__(self, context: BatchContext):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
        """
        super().__init__(context)
        self.context = context

    def execute(self, session, responce):
        """EPデータ参照基盤30分値登録実行

        Args:
            session (Session): セッション
            responce (list): EPデータ参照基盤30分値
        """
        logger = self.logger

        logger.debug("EPデータ参照基盤30分値登録開始。")
        if len(responce) == 0:
            # EPデータ30分値電力量の登録対象リストが０件の場合
            logger.warning("EPデータ参照基盤30分値電力量の登録対象が0件のため登録をスキップします")
            return

        # DTOに格納
        ep_Electricity_Data_30min = [
            EpElectricityData30minDto(**item) for item in responce
        ]

        # Entityに変換
        ep_Electricity_Data_30min_Entity = [
            item.to_dict() for item in ep_Electricity_Data_30min
        ]

        try:
            # EPデータ参照基盤30分値登録
            session.execute(
                insert(TEpElectricityData30min), ep_Electricity_Data_30min_Entity
            )
            session.flush()

        except Exception:
            self.logger.exception("EPデータ参照基盤30分値登録失敗しました。")

        logger.debug("EPデータ参照基盤30分値登録終了。")
