from datetime import date

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.jobs.base import BaseJob

from ..services.create_zip_file_service import CreateZipFileService
from ..services.get_batch_execution_date_service import GetBatchexecutionDateService
from ..services.get_target_year_month_service import GetTargetYearMonthService
from ..services.get_zip_report_users_service import GetZipReportUsersService


class UserPowerReportJob(BaseJob):
    """担当者別zipファイル作成メインJOB

    Args:
        BaseJob (BaseJob)
    """

    def __init__(self, context: BatchContext, batch_execution_date: date):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
            batch_execution_date (date): バッチ実行年月日
        """
        super().__init__(context)
        self.batch_execution_date = batch_execution_date
        self.get_batch_execution_date_service = GetBatchexecutionDateService(
            context, self.logger
        )
        self.get_target_year_month_service = GetTargetYearMonthService(self.logger)
        self.get_zip_report_users_service = GetZipReportUsersService(self.logger)
        self.create_zip_file_service = CreateZipFileService(self.logger)

    def execute(self):
        self.logger.info("担当者別zipファイル作成バッチ実行開始。")

        # バッチ実行年月日取得
        batch_execution_date, batch_execution_day = (
            self.get_batch_execution_date_service.execute(self.batch_execution_date)
        )

        # 対象年月設定
        target_year_month = self.get_target_year_month_service.execute(
            batch_execution_date,
            batch_execution_day,
            self.context.config.final_meter_reading_date,
            self.context.config.offset_month_1,
            self.context.config.offset_month_2,
        )

        # ZIP化対象取得
        zip_users_list = self.get_zip_report_users_service.execute(target_year_month)

        # 担当者別レポートZIP化
        if zip_users_list.rowcount > 0:
            self.create_zip_file_service.execute(
                zip_users_list,
                target_year_month,
                self.context.config.user_power_report_file_path,
            )
        else:
            self.logger.info("ZIP化対象なし。")

        self.logger.info("担当者別zipファイル作成バッチ実行完了。")
