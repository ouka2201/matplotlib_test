from datetime import date

from dateutil.relativedelta import relativedelta

class GetTargetYearMonthService:
    def __init__(self, logger):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
            logger: ロガー
        """
        self.logger = logger

    def execute(
        self,
        batch_execution_date: date,
        batch_execution_day: date,
        final_meter_reading_date: int,
        offset_month_1: int,
        offset_month_2: int,
    ):
        """対象年月取得

        Args:
            batch_excute_date (date): バッチ実行年月日
            batch_excute_day (date): バッチ実行日

        Returns:
            string: 対象年月
        """

        # 対象年月設定
        if batch_execution_day <= final_meter_reading_date:
            target_year_month = batch_execution_date - relativedelta(
                months=offset_month_1
            )
        else:
            target_year_month = batch_execution_date - relativedelta(
                months=offset_month_2
            )

        target_year_month = target_year_month.strftime("%Y%m")

        # ログ出力
        logger = self.logger
        logger.info(f"対象年月取得完了:{target_year_month}")

        return target_year_month
