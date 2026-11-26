from datetime import date, datetime

from cndx_corp_batch.common.constants import ImportedStatus
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.time import (
    calc_offset_month,
    get_current_time,
    is_batch_executable,
)
from cndx_corp_batch.jobs.base import BaseJob

from ..services.t_30min_import_mng_service import (
    T30minImportMngService,
)
from .arve_backup_job import (
    ArveBackupJob,
)
from .delete_ep_power_job import (
    DeleteEpPowerJob,
)
from .get_arve_latest_created_at_job import (
    GetArveLatestCreatedAtJob,
)
from .get_ep_data_api_parallel_job import (
    GetEpDataApiParallelJob,
)
from .get_ep_power_latest_created_at_job import (
    GetEpPowerLatestCreatedAtJob,
)
from .get_historical_arve_latest_created_at_job import (
    GetHistoricalArveLatestCreatedAtJob,
)
from .get_new_customers_job import (
    GetNewCustomersJob,
)
from .get_regular_customers_job import (
    GetRegularCustomersJob,
)
from .import_arve_customer_job import (
    ImportArveCustomerJob,
)
from .import_ep_contracted_power_job import (
    ImportEpContractedPowerJob,
)
from .import_ep_electricity_data_30min_job import (
    ImportEpElectricityData30min,
)


class Import30minCustJob(BaseJob):
    """30分値・顧客情報取込メインJOB

    Args:
        BaseJob (BaseJob)
    """

    def __init__(self, context: BatchContext, batch_date=None):
        """
        Args:
            context (BatchContext): バッチ設定とログ出力先。
            batch_date (date | None): バッチ実行年月日。省略時は日本時間の現在日時。
        """
        super().__init__(context)
        self.context = context

        self.report_ymd = calc_offset_month(
            batch_date if batch_date is not None else get_current_time(),
            self.context.config.cut_off_day,
            self.context.config.report_month_offset_before,
            self.context.config.report_month_offset_after,
        )
        self.historical_ymd = calc_offset_month(
            batch_date if batch_date is not None else get_current_time(),
            self.context.config.cut_off_day,
            self.context.config.arve_cust_month_offset_before,
            self.context.config.arve_cust_month_offset_after,
        )

        self.execPeriod = calc_offset_month(
            batch_date if batch_date is not None else get_current_time(),
            self.context.config.cut_off_day,
            -1,
            0,
        )

        self.get_arve_job = GetArveLatestCreatedAtJob(context)
        self.get_historical_arve_job = GetHistoricalArveLatestCreatedAtJob(context)
        self.backup_job = ArveBackupJob(context, self.historical_ymd)
        self.import_arve = ImportArveCustomerJob(context)
        self.get_ep_job = GetEpPowerLatestCreatedAtJob(context)
        self.delete_ep_job = DeleteEpPowerJob(context)
        self.get_regular_customers_job = GetRegularCustomersJob(
            context, self.historical_ymd, self.report_ymd
        )
        self.get_new_customers_job = GetNewCustomersJob(
            context, self.historical_ymd, self.report_ymd
        )
        self.get_ep_data_api_parallel_job = GetEpDataApiParallelJob(context)
        self.import_ep_contracted_power_job = ImportEpContractedPowerJob(context)
        self.import_ep_electricity_data30min = ImportEpElectricityData30min(context)
        self.import_30min_mng = T30minImportMngService(self.logger)

        self.start_hour = context.config.api_service_time_hour_from
        self.start_minute = context.config.api_service_time_minute_from
        self.end_hour = context.config.api_service_time_hour_to
        self.end_minute = context.config.api_service_time_minute_to

    def execute(self):
        """ """
        self.logger.info("30分・顧客情報取込バッチ実行開始。")
        # ARVEお客さま情報最新作成日時取得
        arve_latest_create_at = self.get_arve_job.execute()

        is_arve_import = True

        if arve_latest_create_at is not None:

            # 過去分ARVEお客様情報最新作成日時取得
            historical_arve_latest_acquisition_year_month = (
                self.get_historical_arve_job.execute()
            )
            historical_arve_ym = ()
            if historical_arve_latest_acquisition_year_month is None:
                # 過去分ARVEお客様情報TBLにデータが存在しない場合のみ特殊対応として、0001/01/01(Pythonの扱える最大過去)として処理を継続する。
                historical_arve_ym = (
                    1,
                    1,
                )
            else:
                historical_arve_latest_acquisition_year_month_datetime = (
                    datetime.strptime(
                        historical_arve_latest_acquisition_year_month, "%Y%m"
                    )
                )

                historical_arve_ym = (
                    historical_arve_latest_acquisition_year_month_datetime.year,
                    historical_arve_latest_acquisition_year_month_datetime.month,
                )

            self.logger.debug(f"過去分ARVE最新年月{historical_arve_ym}")

            report_ym = (self.report_ymd.year, self.report_ymd.month)
            self.logger.debug(f"レポート対象年月{report_ym}")

            if historical_arve_ym <= report_ym:
                # 最新更新日が〆日以前
                self.backup_job.execute()
            else:
                # 最新更新日が〆日後
                is_arve_import = False

        if is_arve_import:
            # 現在日時がAPI実行可能時間外の場合
            if not is_batch_executable(
                self.start_hour, self.start_minute, self.end_hour, self.end_minute
            ):

                self.logger.info("バッチ実行時間外のため終了")
                return

            # ARVEデータ取得
            self.import_arve.execute()

        # EPデータ参照基盤契約電力最新作成日時取得
        ep_latest_create_at = self.get_ep_job.execute()
        self.logger.info(f"ep_latest_create_at:{ep_latest_create_at}")
        self.logger.info(f"execPeriod:{self.execPeriod}")

        if ep_latest_create_at is not None:
            if ep_latest_create_at.date() < self.execPeriod:
                self.delete_ep_job.execute()

        self._regular_ep_data()

        self._new_ep_data()

        self.logger.info("30分・顧客情報取込バッチ実行完了。")

    def _regular_ep_data(self):
        """通常顧客30分値登録"""
        # 通常顧客30分値取得対象のリスト取得
        regular_supply_point_list = self.get_regular_customers_job.execute()

        self.logger.info(f"通常顧客対象地点数={len(regular_supply_point_list)}")
        # 分割の単位
        chunk_size = self.context.config.regular_chunk_size

        # 通常顧客30分値取得対象のリストが1件でもある場合
        if len(regular_supply_point_list) >= 1:
            # 通常顧客30分値取得対象のリストを分割件数づつLOOP
            target_date = self.report_ymd
            for i in range(0, len(regular_supply_point_list), chunk_size):
                self._ep_regular_data_transaction(
                    regular_supply_point_list, i, chunk_size, target_date
                )
                if (i + chunk_size) > len(regular_supply_point_list):
                    inprocess = len(regular_supply_point_list)
                else:
                    inprocess = i + chunk_size
                self.logger.info(
                    f"通常顧客取り込み状況..{inprocess}/{len(regular_supply_point_list)}"
                )

    def _new_ep_data(self):
        """新規顧客30分値登録"""
        # 新規顧客30分値取得対象のリスト取得
        new_supply_point_list = self.get_new_customers_job.execute()

        self.logger.info(f"新規顧客対象地点数={len(new_supply_point_list)}")
        self.logger.info(f"new_supply_point_list:{new_supply_point_list}")

        # 分割の単位
        chunk_size = self.context.config.new_chunk_size

        # 新規顧客30分値取得対象のリストが1件でもある場合
        if len(new_supply_point_list) >= 1:
            # 新規顧客30分値取得対象のリストを分割件数づつLOOP
            for i in range(0, len(new_supply_point_list), chunk_size):
                self._ep_newcommer_data_transaction(
                    supply_point_list=new_supply_point_list,
                    i=i,
                    chunk_size=chunk_size,
                    target_date=self.report_ymd,
                )

    def _ep_regular_data_transaction(
        self,
        supply_point_list: list[str],
        i: int,
        chunk_size: int,
        target_date: date
    ):
        """EPデータ参照基盤データ登録

        Args:
            supply_point_list list[str]: 供給地点特定番号リスト
            i (int): ループ番号
            chunk_size (int): チャンクサイズ
            target_date (date): レポート作成対象年月
        """
        # 現在日時がAPI実行可能時間外の場合
        if not is_batch_executable(
            self.start_hour, self.start_minute, self.end_hour, self.end_minute
        ):
            self.logger.info("バッチ実行時間外のため終了")
            return

        try:
            # 分割件数分取得
            chunk = supply_point_list[i: i + chunk_size]
            result_fetch_30min_values, result_fetch_qcis = (
                self.get_ep_data_api_parallel_job.execute(chunk, target_date)
            )

            with get_session() as session:
                self.import_ep_contracted_power_job.execute(session, result_fetch_qcis)
                self.import_ep_electricity_data30min.execute(
                    session, result_fetch_30min_values
                )
                self.import_30min_mng.execute_with_session(
                    session, chunk, target_date, ImportedStatus.DONE.value
                )
                session.commit()

        except Exception:
            # エラー発生時、30分値取込管理にエラーで登録する。
            self.import_30min_mng.execute(
                chunk, target_date, ImportedStatus.ERROR.value
            )

    def _ep_newcommer_data_transaction(
        self,
        supply_point_list: list[str],
        i: int,
        chunk_size: int,
        target_date: date,
    ):
        """EPデータ参照基盤データ登録

        Args:
            supply_point_list list[str]: 供給地点特定番号リスト
            i (int): ループ番号
            chunk_size (int): チャンクサイズ
            target_date (date): レポート作成対象年月
        """
        # 現在日時がAPI実行可能時間外の場合
        if not is_batch_executable(
            self.start_hour, self.start_minute, self.end_hour, self.end_minute
        ):
            self.logger.info("バッチ実行時間外のため終了")
            return

        try:
            # 分割件数分取得
            chunk = supply_point_list[i: i + chunk_size]
            result_fetch_30min_values, result_fetch_qcis = (
                self.get_ep_data_api_parallel_job.execute_newcommer(chunk, target_date)
            )

            with get_session() as session:
                self.import_ep_contracted_power_job.execute(session, result_fetch_qcis)
                self.import_ep_electricity_data30min.execute(
                    session, result_fetch_30min_values
                )
                self.import_30min_mng.execute_with_session(
                    session, chunk, target_date, ImportedStatus.DONE.value
                )
                session.commit()

        except Exception:
            # エラー発生時、30分値取込管理にエラーで登録する。
            self.import_30min_mng.execute(
                chunk, target_date, ImportedStatus.ERROR.value
            )
