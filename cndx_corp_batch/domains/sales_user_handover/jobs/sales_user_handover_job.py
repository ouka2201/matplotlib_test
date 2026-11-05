"""営業担当者引継バッチの対象取得と法人ごとの引継処理を行う。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.common.time import get_current_time
from cndx_corp_batch.domains.sales_user_handover.constants import (
    HANDOVER_DATA_QUERY_FILES,
    HANDOVER_STATUS_DONE,
    HANDOVER_STATUS_ERROR,
    HANDOVER_STATUS_PLANNED,
)
from cndx_corp_batch.jobs.base import BaseJob


class SalesUserHandoverJob(BaseJob):
    """営業担当者引継バッチ（BLMMGMGHANDOVER）を実行する。

    予定日が実行日と一致する引継情報を法人ごとに処理し、担当者情報、
    必要に応じて過去データと引継実施ステータスを更新する。
    """

    def __init__(self, context: BatchContext, batch_date: date | None = None) -> None:
        """実行日を決め、引継処理で使う SQL を読み込む。

        Args:
            context: バッチの設定やロガーを保持する実行コンテキスト。
            batch_date: 処理対象の日付。省略時は現在の日付を使う。
        """
        super().__init__(context)
        self.batch_date = batch_date or get_current_time().date()
        self.batch_date_text = self.batch_date.strftime("%Y%m%d")
        self.select_targets = text(
            load_sql_file("select_sales_user_handover_targets.sql")
        )
        self.select_source_staff = text(
            load_sql_file("select_handover_source_staff.sql")
        )
        self.select_destination_staff = text(
            load_sql_file("select_handover_destination_staff.sql")
        )
        self.update_staff = text(load_sql_file("update_handover_staff.sql"))
        self.delete_source_staff = text(
            load_sql_file("delete_handover_source_staff.sql")
        )
        self.delete_invalid_target = text(
            load_sql_file("delete_invalid_sales_user_handover.sql")
        )
        self.check_data = text(load_sql_file("check_handover_data.sql"))
        self.update_status = text(
            load_sql_file("update_sales_user_handover_status.sql")
        )
        self.update_data_queries = {
            key: text(load_sql_file(file_name))
            for key, file_name in HANDOVER_DATA_QUERY_FILES.items()
        }

    def execute(self) -> int:
        """実行日が予定日となっている引継情報を法人ごとに処理する。

        Returns:
            処理した引継情報の件数。
        """
        targets = self._get_targets()
        self.logger.info("担当者引継ぎ対象取得完了。件数=%s", len(targets))

        processed = 0
        for target in targets:
            self._process_target(target)
            processed += 1

        self.logger.info("担当者引継ぎ実行バッチ完了。処理件数=%s", processed)
        return processed

    def _get_targets(self) -> list[Mapping[str, object]]:
        """実行日が予定日で、ステータスが「予定」の引継情報を取得する。

        Returns:
            処理対象の引継情報。
        """
        with get_session() as session:
            return list(
                session.execute(
                    self.select_targets,
                    {
                        "batch_date": self.batch_date_text,
                        "handover_status": HANDOVER_STATUS_PLANNED,
                    },
                )
                .mappings()
                .all()
            )

    def _process_target(self, target: Mapping[str, object]) -> None:
        """一件の引継情報について担当者と必要な過去データを更新する。

        元・先の担当者がともに不在なら引継情報を削除する。処理中に例外が
        発生した場合は変更を巻き戻し、別トランザクションで登録エラーを記録する。

        Args:
            target: 処理対象の引継情報。

        Raises:
            Exception: 引継処理中に発生した例外を、エラー記録後に再送出する。
        """
        params = self._target_params(target)
        try:
            with get_session() as session:
                if self._source_staff_exists(session, params):
                    if params["handover_from_user_id"] != params[
                        "handover_to_user_id"
                    ] and self._destination_staff_exists(session, params):
                        session.execute(self.delete_source_staff, params)
                        self.logger.info(
                            "引継先担当者が登録済みのため引継元担当者を削除しました。"
                            "法人番号=%s",
                            params["corporate_number"],
                        )
                    else:
                        session.execute(self.update_staff, params)
                elif not self._destination_staff_exists(session, params):
                    session.execute(self.delete_invalid_target, params)
                    self.logger.warning(
                        "引継元・引継先担当者が存在しないため対象の引継情報を削除し、"
                        "当該法人の処理を終了します。法人番号=%s",
                        params["corporate_number"],
                    )
                    return
                # 元が不在でも同じ法人に先がいれば、過去データ引継ぎ判定へ進む。

                if not target.get("report_data_flg"):
                    self._update_status(session, params, HANDOVER_STATUS_DONE)
                    return

                data_flags = self._check_data_exists(session, params)
                if not data_flags.get("building"):
                    self._update_status(session, params, HANDOVER_STATUS_ERROR)
                    self.logger.error(
                        "建物マスタに引継元データがないため登録エラーにしました。"
                        "法人番号=%s",
                        params["corporate_number"],
                    )
                    return

                for key, query in self.update_data_queries.items():
                    if data_flags.get(key):
                        session.execute(query, params)
                self._update_status(session, params, HANDOVER_STATUS_DONE)
        except Exception:
            # 設計書の例外処理：処理中のトランザクションをロールバックし、
            # エラー状態だけを別トランザクションで記録してバッチを終了する。
            self._record_error_status(params)
            self.logger.exception(
                "担当者引継ぎ処理で例外が発生しました。"
                "法人番号=%s、引継元組織ID=%s、引継先組織ID=%s",
                params["corporate_number"],
                params["handover_from_org_id"],
                params["handover_to_org_id"],
            )
            raise

    def _source_staff_exists(
        self, session: Session, params: Mapping[str, object]
    ) -> bool:
        """対象法人に引継元担当者が登録されているか確認する。

        Args:
            session: 引継処理に使うデータベースセッション。
            params: 法人番号と引継元・引継先の識別子。

        Returns:
            引継元担当者が登録されている場合は ``True``。
        """
        return session.execute(self.select_source_staff, params).first() is not None

    def _destination_staff_exists(
        self, session: Session, params: Mapping[str, object]
    ) -> bool:
        """対象法人に引継先担当者が登録されているか確認する。

        Args:
            session: 引継処理に使うデータベースセッション。
            params: 法人番号と引継元・引継先の識別子。

        Returns:
            引継先担当者が登録されている場合は ``True``。
        """
        return (
            session.execute(self.select_destination_staff, params).first() is not None
        )

    def _check_data_exists(
        self, session: Session, params: Mapping[str, object]
    ) -> Mapping[str, object]:
        """引継元の過去データが各テーブルにあるか確認する。

        Args:
            session: 引継処理に使うデータベースセッション。
            params: 法人番号と引継元・引継先の識別子。

        Returns:
            テーブルごとの存在判定。該当行がなければ空の辞書。
        """
        row = session.execute(self.check_data, params).mappings().first()
        return row or {}

    def _update_status(
        self, session: Session, params: Mapping[str, object], status: str
    ) -> None:
        """引継情報のステータスと実施日時を更新する。

        Args:
            session: 更新に使うデータベースセッション。
            params: 更新対象を特定する法人番号と引継元・引継先の識別子。
            status: 設定する引継実施ステータス。
        """
        session.execute(
            self.update_status,
            {
                **params,
                "handover_status": status,
                "planned_status": HANDOVER_STATUS_PLANNED,
            },
        )

    def _record_error_status(self, params: Mapping[str, object]) -> None:
        """別トランザクションで登録エラーを記録する。

        記録にも失敗した場合は例外をログに残す。

        Args:
            params: 更新対象を特定する法人番号と引継元・引継先の識別子。
        """
        try:
            with get_session() as session:
                self._update_status(session, params, HANDOVER_STATUS_ERROR)
        except Exception:
            self.logger.exception(
                "引継実施ステータスの登録エラー更新に失敗しました。法人番号=%s、"
                "引継元組織ID=%s、引継先組織ID=%s",
                params["corporate_number"],
                params["handover_from_org_id"],
                params["handover_to_org_id"],
            )

    def _target_params(self, target: Mapping[str, object]) -> dict[str, object]:
        """引継情報から各 SQL に共通するパラメータを組み立てる。

        Args:
            target: 処理対象の引継情報。

        Returns:
            法人番号、引継元・引継先の識別子、実行日を含む辞書。
        """
        return {
            "corporate_number": target["corporate_number"],
            "handover_from_org_id": target["handover_from_org_id"],
            "handover_from_user_id": target["handover_from_user_id"],
            "handover_to_org_id": target["handover_to_org_id"],
            "handover_to_user_id": target["handover_to_user_id"],
            "batch_date": self.batch_date_text,
        }
