from __future__ import annotations

from datetime import date
from typing import Mapping

from sqlalchemy import text

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import get_current_time
from cndx_corp_batch.jobs.base import BaseJob


HANDOVER_STATUS_PLANNED = "1"
HANDOVER_STATUS_DONE = "0"
HANDOVER_STATUS_ERROR = "3"

_DATA_UPDATE_SQL = {
    "monthly_building": """
        UPDATE db_corp.t_monthly_building_energy_aggregation
        SET org_id = :handover_to_org_id
        WHERE corporate_number = :corporate_number
          AND org_id = :handover_from_org_id
    """,
    "annual_building": """
        UPDATE db_corp.t_annual_building_energy_aggregation
        SET org_id = :handover_to_org_id
        WHERE corporate_number = :corporate_number
          AND org_id = :handover_from_org_id
    """,
    "monthly_corporate": """
        UPDATE db_corp.t_monthly_corporate_energy_aggregation
        SET org_id = :handover_to_org_id
        WHERE corporate_number = :corporate_number
          AND org_id = :handover_from_org_id
    """,
    "annual_corporate": """
        UPDATE db_corp.t_annual_corporate_energy_aggregation
        SET org_id = :handover_to_org_id
        WHERE corporate_number = :corporate_number
          AND org_id = :handover_from_org_id
    """,
    "report_storage": """
        UPDATE db_corp.t_report_storage_info
        SET org_id = :handover_to_org_id
        WHERE corporate_number = :corporate_number
          AND org_id = :handover_from_org_id
    """,
    "building": """
        UPDATE db_corp.m_building
        SET agreement_org = :handover_to_org_id
        WHERE corporate_number = :corporate_number
          AND agreement_org = :handover_from_org_id
    """,
    "cn_application": """
        UPDATE db_corp.t_cn_application_info
        SET org_id = :handover_to_org_id
        WHERE corporate_number = :corporate_number
          AND org_id = :handover_from_org_id
    """,
    "building_info": """
        UPDATE db_corp.t_building_info
        SET org_id = :handover_to_org_id
        WHERE corporate_number = :corporate_number
          AND org_id = :handover_from_org_id
    """,
}


class SalesUserHandoverJob(BaseJob):
    """担当者引継ぎ実行バッチ（BLMMGMGHANDOVER）。

    対象法人を順次処理し、引継元担当者の確認、担当者情報の更新、
    過去データの組織ID更新、引継情報の完了更新を行う。
    """

    def __init__(self, context: BatchContext, batch_date: date | None = None):
        super().__init__(context)
        self.batch_date = batch_date or get_current_time().date()
        self.batch_date_text = self.batch_date.strftime("%Y%m%d")
        self.select_targets = text(load_sql_file("select_sales_user_handover_targets.sql"))
        self.select_source_staff = text(load_sql_file("select_handover_source_staff.sql"))
        self.select_destination_staff = text(
            load_sql_file("select_handover_destination_staff.sql")
        )
        self.update_staff = text(load_sql_file("update_handover_staff.sql"))
        self.delete_source_staff = text(load_sql_file("delete_handover_source_staff.sql"))
        self.delete_invalid_target = text(
            load_sql_file("delete_invalid_sales_user_handover.sql")
        )
        self.check_data = text(load_sql_file("check_handover_data.sql"))
        self.update_status = text(load_sql_file("update_sales_user_handover_status.sql"))

    def execute(self) -> int:
        """対象を取得し、法人番号単位で設計書の処理を順番に実行する。"""
        targets = self._get_targets()
        self.logger.info("担当者引継ぎ対象取得完了。件数=%s", len(targets))

        processed = 0
        for target in targets:
            self._process_target(target)
            processed += 1

        self.logger.info("担当者引継ぎ実行バッチ完了。処理件数=%s", processed)
        return processed

    def _get_targets(self) -> list[Mapping[str, object]]:
        with get_session() as session:
            return list(
                session.execute(
                    self.select_targets,
                    {"batch_date": self.batch_date_text},
                ).mappings().all()
            )

    def _process_target(self, target: Mapping[str, object]) -> None:
        params = self._target_params(target)
        try:
            with get_session() as session:
                if not self._source_staff_exists(session, params):
                    session.execute(self.delete_invalid_target, params)
                    self.logger.warning(
                        "引継元担当者が存在しないため引継情報を削除しました。法人番号=%s",
                        params["corporate_number"],
                    )
                    return

                if (
                    params["handover_from_user_id"] != params["handover_to_user_id"]
                    and self._destination_staff_exists(session, params)
                ):
                    session.execute(self.delete_source_staff, params)
                    self.logger.info(
                        "引継先担当者が登録済みのため引継元担当者を削除しました。法人番号=%s",
                        params["corporate_number"],
                    )
                else:
                    session.execute(self.update_staff, params)

                if not self._as_bool(target.get("report_data_flg")):
                    self._update_status(session, params, HANDOVER_STATUS_DONE)
                    return

                data_flags = self._check_data_exists(session, params)
                if not self._as_bool(data_flags.get("building")):
                    self._update_status(session, params, HANDOVER_STATUS_ERROR)
                    self.logger.error(
                        "建物マスタに引継元データがないため登録エラーにしました。法人番号=%s",
                        params["corporate_number"],
                    )
                    return

                for key, sql in _DATA_UPDATE_SQL.items():
                    if self._as_bool(data_flags.get(key)):
                        session.execute(text(sql), params)
                self._update_status(session, params, HANDOVER_STATUS_DONE)
        except Exception:
            # 設計書の例外処理：処理中のトランザクションをロールバックし、
            # エラー状態だけを別トランザクションで記録してバッチを終了する。
            self._record_error_status(params)
            self.logger.exception(
                "担当者引継ぎ処理で例外が発生しました。法人番号=%s",
                params["corporate_number"],
            )
            raise

    def _source_staff_exists(self, session, params: Mapping[str, object]) -> bool:
        return (
            session.execute(self.select_source_staff, params).first() is not None
        )

    def _destination_staff_exists(self, session, params: Mapping[str, object]) -> bool:
        return (
            session.execute(self.select_destination_staff, params).first() is not None
        )

    def _check_data_exists(self, session, params: Mapping[str, object]) -> Mapping[str, object]:
        row = session.execute(self.check_data, params).mappings().first()
        return row or {}

    def _update_status(self, session, params: Mapping[str, object], status: str) -> None:
        session.execute(
            self.update_status,
            {**params, "handover_status": status},
        )

    def _record_error_status(self, params: Mapping[str, object]) -> None:
        try:
            with get_session() as session:
                self._update_status(session, params, HANDOVER_STATUS_ERROR)
        except Exception:
            self.logger.exception(
                "引継実施ステータスの登録エラー更新に失敗しました。法人番号=%s",
                params["corporate_number"],
            )

    def _target_params(self, target: Mapping[str, object]) -> dict[str, object]:
        return {
            "corporate_number": target["corporate_number"],
            "handover_from_org_id": target["handover_from_org_id"],
            "handover_from_user_id": target["handover_from_user_id"],
            "handover_to_org_id": target["handover_to_org_id"],
            "handover_to_user_id": target["handover_to_user_id"],
            "batch_date": self.batch_date_text,
        }

    @staticmethod
    def _as_bool(value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "t", "yes", "y"}
        return bool(value)
