from sqlalchemy.dialects.postgresql import insert as pg_insert

from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.entity.t_30min_import_mng_entity import (
    T30minImportMng,
)
from cndx_corp_batch.common.time import get_current_time
from cndx_corp_batch.common.utils import get_sysuser


class T30minImportMngService:
    """30分値取込管理サービス

    Args:
        BaseJob (BaseJob)
    """

    def __init__(self, logger):
        """
        Parameters:
            logger: ロガー
        """
        self.logger = logger

    def execute(self, chunks, target_date, status):
        """通常更新

        Args:
            chunks (list[str]): 供給地点特定番号リスト
            target_date (date): レポート作成対象年月
            status (str): 状態
        """
        try:

            with get_session() as session:
                # 30分値取込管理状態のUPSERT
                self.execute_with_session(session, chunks, target_date, status)
                # session.execute(insert(T30minImportMng), ep_30min_import_mng)
                session.commit()

        except Exception:
            raise

    def execute_with_session(self, session, chunks, target_date, status):
        """セッション指定で更新

        Args:
            session (Session): 指定セッション
            chunks (list[str]): 供給地点特定番号リスト
            target_date (date): レポート作成対象年月
            status (str): 状態
        """

        # Entityに変換
        ep_30min_import_mng = self._make_insert_data(chunks, target_date, status)
        try:
            # 30分値取込管理状態
            # 過去にエラーで登録されている場合があるため、UPSERTを行う
            stmt = pg_insert(T30minImportMng).values(ep_30min_import_mng)
            # # 主キーと作成・更新日時以外を自動でマッピング
            update_cols = {
                col.name: getattr(stmt.excluded, col.name)
                for col in T30minImportMng.__table__.columns
                if not col.primary_key
                and col.name
                not in ("created_by", "created_at", "updated_by", "updated_at")
            }
            update_cols["updated_by"] = get_sysuser()
            update_cols["updated_at"] = get_current_time().strftime("%Y/%m/%d %H:%M:%S")
            # UPSERT用のfunction（ON CONFLICT DO UPDATE）を組み立て
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=[
                    "supply_point_number",
                    "target_year_month",
                ],
                set_=update_cols,
            )
            session.execute(upsert_stmt)
            session.flush()

        except Exception:
            self.logger.exception("30分値取込管理状態登録失敗しました。")
            raise

    def _make_insert_data(self, chunks, target_date, status):
        """登録データ作成

        Args:
            chunks (list[str]): 供給地点特定番号リスト
            target_date (date): レポート作成対象年月
            status (str): 状態

        Returns:
            list: 登録データ
        """
        return [
            {
                "supply_point_number": item,
                "target_year_month": target_date.strftime("%Y%m"),
                "create_status": status,
                "error_message": "",
                "linked_error_message": "",
                "created_by": get_sysuser(),
            }
            for item in chunks
        ]
