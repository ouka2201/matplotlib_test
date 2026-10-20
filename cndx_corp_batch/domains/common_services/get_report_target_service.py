from typing import List

from cndx_corp_batch.common.constants import ReportStatus
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.entity.t_report_storage_info_entity import (
    TReportStorageInfo,
)
from cndx_corp_batch.domains.repository.treport_repository import (
    ReportStorageRepository,
)


class ReportTargetsGetService:
    """
    レポート作成対象一覧取得サービス
    """

    def __init__(self, context: BatchContext, logger):
        self.context = context
        self.logger = logger

    def get_report_target(self, report_type: str) -> List[TReportStorageInfo]:
        report_targets: list[TReportStorageInfo] = []

        # session = self.context.db_session
        with get_session() as session:
            report_repo = ReportStorageRepository(session)
            report_targets = report_repo.find_by_conditions(
                report_type=report_type,
                status=[ReportStatus.WORKING, ReportStatus.ERROR],
            )

            if not report_targets or len(report_targets) == 0:
                self.logger.warning("処理対象取得できないため、終了します。")

            return report_targets
