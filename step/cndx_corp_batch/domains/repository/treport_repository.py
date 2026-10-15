# domains/report/repository.py
import getpass
from datetime import datetime
from typing import List

from sqlalchemy import asc
from sqlalchemy.orm import Session

from cndx_corp_batch.common.constants import ReportStatus, ReportType
from cndx_corp_batch.common.entity.t_report_storage_info_entity import (
    TReportStorageInfo,
)


class ReportStorageRepository:

    def __init__(self, session: Session):
        self.session = session

    # def find_by_conditions(
    #     self,
    #     report_type: ReportType,
    #     status: ReportStatus,
    #     include_deleted: bool = False,
    # ) -> list[TReportStorageInfo]:
    #     """
    #     作成中の電力見える化レポート対象を取得する
    #     """

    #     q = self.session.query(TReportStorageInfo).filter(
    #         TReportStorageInfo.report_classify == report_type.value,
    #         TReportStorageInfo.report_status == status.value,
    #     )

    #     if not include_deleted:
    #         q = q.filter(TReportStorageInfo.delete_flg.is_(False))

    #     return q.all()
    def find_by_conditions(
        self,
        report_type: ReportType,
        status: ReportStatus | list[ReportStatus],
        include_deleted: bool = False,
    ) -> list[TReportStorageInfo]:
        """
        作成中（またはエラー）の電力見える化レポート対象を取得する
        """
        # status が単一値の場合はリストに変換
        statuses = (
            [status.value]
            if isinstance(status, ReportStatus)
            else [s.value for s in status]
        )

        q = self.session.query(TReportStorageInfo).filter(
            TReportStorageInfo.report_classify == report_type.value,
            TReportStorageInfo.report_status.in_(statuses),
        )

        # 削除フラグの判定を復元
        if not include_deleted:
            q = q.filter(TReportStorageInfo.delete_flg.is_(False))

        return q.order_by(asc(TReportStorageInfo.created_at)).all()

    def find_working_by_creation_ids(
        self,
        target_ids: List[str],
    ) -> list[TReportStorageInfo]:
        """
        作成中の電力見える化レポート対象を取得する
        """
        return (
            self.session.query(TReportStorageInfo)
            .filter(
                TReportStorageInfo.creation_id.in_(target_ids),
            )
            .all()
        )

    def update_by_creation(
        self,
        *,
        creation_id: str,
        report_type: ReportType,
        status: ReportStatus,
        pdf_file_name: str = None,
        png_bytes=None,
        batch_id: str = None
    ) -> int:
        """
        creation_id + report_classify でステータス更新
        戻り値: 更新件数
        """
        query = self.session.query(TReportStorageInfo).filter(
            TReportStorageInfo.creation_id == creation_id,
            TReportStorageInfo.report_classify == report_type.value,
            TReportStorageInfo.delete_flg.is_(False),
        )

        # status が error の場合のみ、現在 status=working のものに限定
        if status == ReportStatus.ERROR:
            query = query.filter(
                TReportStorageInfo.report_status == ReportStatus.WORKING.value
            )

        update_values = {
            TReportStorageInfo.report_status: status.value,
            TReportStorageInfo.updated_at: datetime.now(),
            TReportStorageInfo.updated_by: getpass.getuser(),
            TReportStorageInfo.batch_id: batch_id,
        }

        if pdf_file_name is not None:
            update_values[TReportStorageInfo.report_save_path] = pdf_file_name

        if png_bytes is not None:
            update_values[TReportStorageInfo.png_bytes] = png_bytes

        return query.update(
            update_values,
            synchronize_session=False,
        )
