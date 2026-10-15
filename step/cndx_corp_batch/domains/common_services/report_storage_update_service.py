from typing import Optional

from cndx_corp_batch.common.constants import ReportStatus, ReportType
from cndx_corp_batch.domains.cn_karte.services.report_page_create_service import (
    ReportFileResult,
)
from cndx_corp_batch.domains.repository.treport_repository import (
    ReportStorageRepository,
)


class ReportStorageUpdateService:
    def __init__(self, session, repo: ReportStorageRepository, logger):
        self.session = session
        self.repo = repo
        self.logger = logger

    def update_from_result(
        self,
        result: ReportFileResult,
        upload_file_path: str,
        report_type: str,
        batch_id: str,
    ) -> list[str]:
        creation_id = result.creation_id
        try:
            if upload_file_path:
                self.repo.update_by_creation(
                    creation_id=creation_id,
                    report_type=report_type,
                    status=ReportStatus.DONE,
                    pdf_file_name=upload_file_path,
                    png_bytes=result.pdf_png_bytes,
                    batch_id=batch_id,
                )
            else:
                self.repo.update_by_creation(
                    creation_id=creation_id,
                    report_type=report_type,
                    status=ReportStatus.ERROR,
                    batch_id=batch_id,
                )
            self.session.flush()
            self.session.commit()
        except Exception:
            self.session.rollback()
            self.logger.exception(
                f"{report_type}のreport格納情報{creation_id}のステータス更新失敗しました。"
            )
            self.mark_error(creation_id, report_type, batch_id)

        return creation_id

    def update_from_results(
        self,
        results: list[ReportFileResult],
        upload_results: dict[str, Optional[str]],
        report_type: str,
        batch_id: str,
    ) -> list[str]:
        delete_creation_ids: list[str] = []

        for result in results:
            creation_id = result.creation_id
            try:
                upload_file_path = upload_results.get(creation_id)
                if upload_results.get(creation_id):
                    self.repo.update_by_creation(
                        creation_id=creation_id,
                        report_type=report_type,
                        status=ReportStatus.DONE,
                        pdf_file_name=upload_file_path,
                        png_bytes=result.pdf_png_bytes,
                        batch_id=batch_id,
                    )
                else:
                    self.repo.update_by_creation(
                        creation_id=creation_id,
                        report_type=report_type,
                        status=ReportStatus.ERROR,
                        batch_id=batch_id,
                    )
                # self.session.flush()
            except Exception:
                # self.session.rollback()
                self.logger.exception(
                    f"{report_type}のreport格納情報{creation_id}のステータス更新失敗しました。"
                )
                self.mark_error(creation_id, report_type, batch_id)
            finally:
                delete_creation_ids.append(creation_id)

        # self.session.commit()

        return delete_creation_ids

    def mark_error(self, creation_id: str, report_type: str, batch_id: str):
        try:
            self.repo.update_by_creation(
                creation_id=creation_id,
                report_type=report_type,
                status=ReportStatus.ERROR,
                batch_id=batch_id,
            )
            self.session.flush()
            self.repo.session.commit()
        except Exception:
            self.session.rollback()
            self.logger.exception(
                f"{report_type}のreport格納情報{creation_id}のステータス更新失敗しました。"
            )
