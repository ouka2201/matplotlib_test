from datetime import date

from cndx_corp_batch.common.context import BatchContext


class GetBatchexecutionDateService:
    def __init__(self, context: BatchContext, logger):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
            logger: ロガー
        """
        self.context = context
        self.logger = logger

    def execute(self, batch_execution_date: date):
        """対象年月取得
        Args:
            batch_execution_date (date): バッチ実行年月日

        Returns:
            date: バッチ実行年月日
            date: バッチ実行日
        """

        today = date.today()

        if batch_execution_date is None:
            batch_execution_date = today

        batch_execution_day = batch_execution_date.day

        # ログ出力
        logger = self.logger
        logger.info(f"バッチ実行年月日取得完了:{batch_execution_date}")

        return batch_execution_date, batch_execution_day
