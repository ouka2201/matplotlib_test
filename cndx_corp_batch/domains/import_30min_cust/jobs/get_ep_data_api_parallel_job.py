import calendar
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from matplotlib.dates import relativedelta

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.jobs.base import BaseJob

from ..services.fetch_ep_contracted_power_service import (
    FetchEpContractedPowerService,
)
from ..services.fetch_ep_electricity_data_30min_service import (
    FetchEpElectricityData30minService,
)


class GetEpDataApiParallelJob(BaseJob):
    """EPデータ参照基盤取得並列処理JOB

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
        self.fetch_ep_electricity_data30min_service = (
            FetchEpElectricityData30minService(context, self.logger)
        )
        self.fetch_ep_contracted_power_service = FetchEpContractedPowerService(
            context, self.logger
        )

    def execute(
        self, chunks: list[str], target_date: date
    ) -> tuple[list, list]:
        """EPデータ参照基盤取得並列処理実行(通常顧客)

        Args:
            chunks (list[str]): 分割された供給地点特定番号リスト
            target_date (date): レポート作成対象年月

        Returns:
            tuple[list, list]: (EPデータ参照基盤30分値リスト, EPデータ参照基盤契約電力リスト)
        """
        logger = self.logger

        logger.debug(f"EPデータ参照基盤取得並列処理開始:{chunks}:cycle:{target_date}")

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_fetch_ep_regular_electricity_data30min = executor.submit(
                self._execute_fetch_ep_regular_electricity_data30min,
                chunks, target_date
            )

            try:
                result_fetch_ep_electricity_data30min = (
                    future_fetch_ep_regular_electricity_data30min.result()
                )
            except Exception:
                logger.exception(
                    "EPデータ参照基盤30分値取得並列処理でエラーが発生しました。"
                )
                raise
        try:
            result_fetch_ep_contracted_power = self._execute_fetch_ep_contracted_power(
                chunks=chunks
            )
        except Exception:
            logger.exception(
                "EPデータ参照基盤契約電力取得並列処理でエラーが発生しました。"
            )
            raise

        logger.debug("EPデータ参照基盤取得並列処理完了")
        return result_fetch_ep_electricity_data30min, result_fetch_ep_contracted_power

    def execute_newcommer(
        self, chunks: list[str], target_date: date
    ) -> tuple[list, list]:
        """EPデータ参照基盤取得並列処理実行(新規顧客)

        Args:
            chunks (list[str]): 分割された供給地点特定番号リスト
            target_date (date): レポート作成対象年月

        Returns:
            tuple[list, list]: (EPデータ参照基盤30分値リスト, EPデータ参照基盤契約電力リスト)
        """
        logger = self.logger

        logger.debug(f"EPデータ参照基盤取得並列処理開始:{chunks}:cycle:{target_date}")
        result_fetch_ep_contracted_power_all = []
        for i in range(12):
            export_date = target_date - relativedelta(months=i)

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_fetch_ep_newcommer_electricity_data30min = executor.submit(
                    self._execute_fetch_ep_newcommer_electricity_data30min,
                    chunks, export_date
                )

                try:
                    result_fetch_ep_electricity_data30min = (
                        future_fetch_ep_newcommer_electricity_data30min.result()
                    )
                except Exception:
                    logger.exception(
                        "EPデータ参照基盤30分値取得並列処理でエラーが発生しました。"
                    )
                    raise
                result_fetch_ep_contracted_power_all.extend(
                    result_fetch_ep_electricity_data30min
                )
        try:
            result_fetch_ep_contracted_power = self._execute_fetch_ep_contracted_power(
                chunks=chunks
            )
        except Exception:
            logger.exception(
                "EPデータ参照基盤契約電力取得並列処理でエラーが発生しました。"
            )
            raise

        logger.debug("EPデータ参照基盤取得並列処理完了")
        return result_fetch_ep_contracted_power_all, result_fetch_ep_contracted_power

    def _execute_fetch_ep_newcommer_electricity_data30min(
            self, chunks, target_date: date):
        """EPデータ参照基盤30分値取得API実行(新規顧客)

        Args:
            chunks (list[str]): 分割された供給地点特定番号リスト
            target_date (date): レポート作成対象年月

        Returns:
            list: EPデータ参照基盤30分値
        """
        results = []
        start_date, end_date = self._create_date_targetmonth(target_date)
        result = self.fetch_ep_electricity_data30min_service.execute_newcommer(
            supplay_point_list=chunks, start_date=start_date, end_date=end_date
        )
        results.extend(result)
        return results

    def _execute_fetch_ep_regular_electricity_data30min(
            self, chunks, target_date: date):
        """EPデータ参照基盤30分値取得API実行(通常顧客)

        Args:
            chunks (list[str]): 分割された供給地点特定番号リスト
            target_date (date): レポート作成対象年月

        Returns:
            list: EPデータ参照基盤30分値
        """
        results = []
        start_date, end_date = self._create_date_targetmonth(target_date)
        result = self.fetch_ep_electricity_data30min_service.execute_regular(
            supplay_point_list=chunks, start_date=start_date, end_date=end_date
        )
        results.extend(result)
        return results

    def _execute_fetch_ep_contracted_power(self, chunks: list[str]):
        """EPデータ参照基盤契約電力取得API実行

        Args:
            chunks (list[str]): 分割された供給地点特定番号リスト

        Returns:
            list: EPデータ参照基盤契約電力
        """
        return self.fetch_ep_contracted_power_service.execute(supplay_point_list=chunks)

    def _create_date_targetmonth(self, target_date: date) -> tuple[date, date]:
        """レポート作成対象年月の月初から月末を取得する

        Args:
            target_date (date): レポート作成対象年月

        Returns:
            list[tuple[date, date]]: 月初日、月末日
        """
        last_day = calendar.monthrange(target_date.year, target_date.month)[1]

        return (
            date(target_date.year, target_date.month, 1),
            date(target_date.year, target_date.month, last_day),
        )
