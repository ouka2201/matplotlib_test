from sqlalchemy import insert

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.dto.ep_contracted_power_dto import (
    EpContractedPowerDto,
)
from cndx_corp_batch.common.entity.t_ep_contracted_power_entity import (
    TEpContractedPower,
)
from cndx_corp_batch.jobs.base import BaseJob


class ImportEpContractedPowerJob(BaseJob):
    """EPデータ参照基盤契約電力登録JOB

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
        """EPデータ参照基盤契約電力登録実行

        Args:
            session (Session): セッション
            responce (list): EPデータ参照基盤契約電力
        """
        logger = self.logger

        logger.debug("EPデータ参照基盤契約電力登録開始。")
        if len(responce) == 0:
            # EPデータ契約電力の登録対象リストが０件の場合
            logger.warning("EPデータ参照基盤契約電力の登録対象が0件のため登録をスキップします")
            return

        # DTOに格納
        ep_contracted_power = [EpContractedPowerDto(**item) for item in responce]

        # Entityに変換
        ep_contracted_powers = [item.to_dict() for item in ep_contracted_power]

        try:
            # EPデータ参照基盤契約電力登録
            session.execute(insert(TEpContractedPower), ep_contracted_powers)
            session.flush()

        except Exception:
            self.logger.exception("EPデータ参照基盤契約電力登録失敗しました。")

        logger.debug("EPデータ参照基盤契約電力登録終了。")
