from cndx_corp_batch.common.api_client import ApiClient
from cndx_corp_batch.common.context import BatchContext

END_POINT = "/api/ep_contracted_power"


class FetchEpContractedPowerService:
    """EPデータ参照基盤契約電力取得サービス"""

    def __init__(self, context: BatchContext, logger):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
            logger: ロガー
        """
        self.context = context
        self.logger = logger
        # APIクライアントセットアップ
        self.client = ApiClient(
            self.context.config.ep_contract_power,
        )

    def execute(self, supplay_point_list: list[str]) -> list:
        """EPデータ参照基盤契約電力取得API実行

        Args:
            supplay_point_list (list[str]): _description_

        Returns:
            Any: EPデータ参照基盤契約電力
        """
        filter_param = (
            "("
            + " OR ".join(
                [
                    f"\"QSQB_DCIS2_SPL_PT_SPC_NO\"='{value}'"
                    for value in supplay_point_list
                ]
            )
            + ")"
        )

        params = {"$filter": filter_param}

        # EPデータ参照基盤契約電力取得
        res = self.client.get_all_pages(params=params)

        return res
