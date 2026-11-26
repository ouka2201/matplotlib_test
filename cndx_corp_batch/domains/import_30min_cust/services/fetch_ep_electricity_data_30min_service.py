from datetime import (
    date,
)

from cndx_corp_batch.common.api_client import ApiClient
from cndx_corp_batch.common.context import BatchContext


class FetchEpElectricityData30minService:
    """EPデータ参照基盤30分値取得サービス

    Attributes:
        BaseJob (_type_): _description_
    """

    def __init__(self, context: BatchContext, logger):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
            logger: ロガー
        """
        self.context = context
        self.logger = logger
        # APIクライアントセットアップ
        # 通常顧客用
        self.regular_client = ApiClient(
            self.context.config.ep_regular_data,
        )
        # 新規顧客用
        self.newcommer_client = ApiClient(
            self.context.config.ep_newcommer_data,
        )

    def _execute(
            self,
            supplay_point_list: list[str],
            start_date: date,
            end_date: date, client: ApiClient):
        """EPデータ参照基盤30分値取得API実行

        Args:
            supplay_point_list (list[str]): 供給地点特定番号リスト
            start_date (date): 抽出開始日
            end_date (date): 抽出終了日
            client(APIClient): REST APIクライアント

        Returns:
            Any: EPデータ参照基盤30分値
        """

        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        filter_param = (
            "(("
            + " OR ".join(
                [f"\"T01_KYO_CTN_TOK_NO\"='{value}'" for value in supplay_point_list]
            )
            + ")"
            + " AND "
            + "("
            + f"trim(\"T01_GET_YMD\") >= '{start_date_str}'"
            + f" AND trim(\"T01_GET_YMD\") <= '{end_date_str}'"
            + "))"
        )

        params = {"$filter": filter_param}

        # EPデータ参照基盤30分値取得
        res = client.get_all_pages(params=params)

        return res

    def execute_regular(
            self, supplay_point_list: list[str], start_date: date, end_date: date):
        """通常顧客向けEPデータ参照基盤30分値取得API実行

        Args:
            supplay_point_list (list[str]): 供給地点特定番号リスト
            start_date (date): 抽出開始日
            end_date (date): 抽出終了日

        Returns:
            Any: EPデータ参照基盤30分値
        """
        client = self.regular_client
        return self._execute(
            supplay_point_list=supplay_point_list,
            start_date=start_date,
            end_date=end_date,
            client=client)

    def execute_newcommer(
            self, supplay_point_list: list[str], start_date: date, end_date: date):
        """新規顧客向けEPデータ参照基盤30分値取得API実行

        Args:
            supplay_point_list (list[str]): 供給地点特定番号リスト
            start_date (date): 抽出開始日
            end_date (date): 抽出終了日

        Returns:
            Any: EPデータ参照基盤30分値
        """
        client = self.newcommer_client
        return self._execute(
            supplay_point_list=supplay_point_list,
            start_date=start_date,
            end_date=end_date,
            client=client)
