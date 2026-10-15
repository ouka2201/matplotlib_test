import logging
import logging.handlers
import multiprocessing
from concurrent.futures import (
    ProcessPoolExecutor,
)

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.time import (
    calc_offset_month,
    get_current_time,
)
from cndx_corp_batch.common.utils import cpu_workers
from cndx_corp_batch.jobs.base import BaseJob

from ..services.create_power_report_service import (
    execute,
    multiprocessing_initializer,
)
from .get_power_report_target import GetPowerReportTarget
from .register_unregistered_report_target_job import RegisterUnregisteredReportTargetJob


class GenerateAllPowerReportJob(BaseJob):
    """電力見える化レポート一括作成メインJOB

    Args:
        BaseJob (BaseJob)
    """

    def __init__(self, context: BatchContext, batch_date=None):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
        """
        super().__init__(context)
        self.context = context

        self.report_ymd = calc_offset_month(
            batch_date if batch_date is not None else get_current_time(),
            self.context.config.cut_off_day,
            self.context.config.report_month_offset_before,
            self.context.config.report_month_offset_after,
        )

        self.register_report_job = RegisterUnregisteredReportTargetJob(
            context, self.report_ymd
        )
        self.get_report_target_job = GetPowerReportTarget(context, self.report_ymd)

    def execute(self):
        self.logger.info("電力見える化レポート一括作成バッチ実行開始。")

        # 30分値データ取込確認ジョブ
        self.register_report_job.execute()

        # レポート作成対象情報取得
        targets = self.get_report_target_job.execute()

        output_count = len(targets)
        if not targets:
            self.logger.info("作成対象は0件です。")
            return
        count = min(cpu_workers(), output_count)

        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(processName)s %(message)s"
        )
        console_handler.setFormatter(formatter)

        with multiprocessing.Manager() as manager:
            log_queue = manager.Queue()
            listener = logging.handlers.QueueListener(log_queue, console_handler)
            listener.start()
            try:
                with ProcessPoolExecutor(
                    max_workers=count,
                    initializer=multiprocessing_initializer,
                    initargs=(self.context.config.db_url, log_queue),
                ) as executor:
                    futures = [
                        executor.submit(execute, row, self.report_ymd) for row in targets
                    ]
                    for i, future in enumerate(futures, 1):
                        try:
                            future.result()
                            self.logger.info("タスク %s/%s 処理終了", i, output_count)
                        except Exception:
                            self.logger.exception("タスク %s/%s エラー", i, output_count)
            finally:
                listener.stop()
        self.logger.info("電力見える化レポート一括作成バッチ実行完了。")
