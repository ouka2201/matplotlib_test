import logging
import logging.handlers
import multiprocessing
from concurrent.futures import (
    ProcessPoolExecutor,
)
from typing import Any

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
from .get_power_report_target_job import GetPowerReportTargetJob
from .register_unregistered_report_target_job import RegisterUnregisteredReportTargetJob


class GenerateAllPowerReportJob(BaseJob):
    """バッチ処理内容定義書1～4・LOOP：対象年月を決定し、作成対象を登録・取得して並列に処理する。

    供給地点特定番号ごとに1件ずつ、CPUコア数を上限として処理する。
    個別の処理に失敗しても、後続の対象を処理する。
    """

    def __init__(self, context: BatchContext, batch_date: Any = None) -> None:
        """処理1・2／データ項目更新仕様説明書No.1・2：実行日から対象年月を設定する。

        【補足】バッチ年月仕様の既定値は、1～14日が実行月の3か月前、
        15日～月末が2か月前。実装では環境設定と実行日引数で指定できる。

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

        self.register_report_job = RegisterUnregisteredReportTargetJob(
            context, self.report_ymd
        )
        self.get_report_target_job = GetPowerReportTargetJob(context, self.report_ymd)

    def execute(self) -> Any:
        self.logger.info("電力見える化レポート一括作成バッチ実行開始。")

        # 処理3：30分値の取込が完了した対象を、
        # 管理情報へ状態2（作成中）で登録する。
        self.register_report_job.execute()

        # 処理4：対象年月の状態2（作成中）・5（エラー）を取得する。
        targets = self.get_report_target_job.execute()

        output_count = len(targets)
        # LOOP：対象が0件の場合は処理を終了し、ワーカーを起動しない。
        if not targets:
            self.logger.info("作成対象は0件です。")
            return
        # LOOP：コア数分で並列処理する。対象件数より多くのプロセスは作らない。
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
                        executor.submit(execute, row, self.report_ymd)
                        for row in targets
                    ]
                    for i, future in enumerate(futures, 1):
                        try:
                            future.result()
                            self.logger.info("タスク %s/%s 処理終了", i, output_count)
                        except Exception:
                            # 個別の例外を記録し、後続の対象の処理を続ける。
                            self.logger.exception(
                                "タスク %s/%s エラー", i, output_count
                            )
            finally:
                listener.stop()
        self.logger.info("電力見える化レポート一括作成バッチ実行完了。")
