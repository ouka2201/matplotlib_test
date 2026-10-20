from datetime import datetime

from cndx_corp_batch.common.constants import (
    ReportStatus,
    ReportType,
)
from cndx_corp_batch.common.logger import BatchLogger
from cndx_corp_batch.domains.repository.treport_repository import (
    ReportStorageRepository,
)


class MarkWorkingReportsErrorService:
    """
    WORKING 状態のレポートPDFを取得し、ERROR に更新する Service
    """

    def __init__(self, session, logger: BatchLogger):
        self.session = session
        self.logger = logger
        self.repo = ReportStorageRepository(session)

    def execute(self, report_type: ReportType) -> list[str]:
        # 作成中レポートを取得
        targets = self.repo.find_by_conditions(
            report_type=report_type,
            status=ReportStatus.WORKING,
        )

        if not targets:
            self.logger.warning(
                f"{report_type.name}の更新対象の作成中レポートはありません。"
            )
            return []

        creation_ids = [t.creation_id for t in targets]

        self.logger.info(
            f"作成中{report_type.name}レポートをERRORに更新します。対象件数：{len(creation_ids)}"
        )

        # ② ERROR へ更新
        for creation_id in creation_ids:
            try:
                self.repo.update_by_creation(
                    creation_id=creation_id,
                    report_type=report_type,
                    status=ReportStatus.ERROR,
                )
                self.session.commit()
            except Exception:
                self.session.rollback()
                self.logger.exception(
                    f"レポートERROR更新が失敗しました。{creation_ids}"
                )

        return creation_ids
