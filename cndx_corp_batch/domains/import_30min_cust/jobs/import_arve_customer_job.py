from sqlalchemy import insert, text

from cndx_corp_batch.common.api_client import ApiClient
from cndx_corp_batch.common.context import BatchContext
from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.dto.arve_customer_info_dto import (
    ArveCustomerInfoResponseDto,
)
from cndx_corp_batch.common.entity.t_arve_customer_info_entity import (
    TArveCustomerInfo,
)
from cndx_corp_batch.common.query import load_sql_file
from cndx_corp_batch.jobs.base import BaseJob


class ImportArveCustomerJob(BaseJob):
    """ARVEお客さま情報登録JOB

    Args:
        BaseJob (BaseJob)
    """

    def __init__(self, context: BatchContext):
        """
        Parameters:
            context (BatchContext): バッチコンテキスト
        """
        super().__init__(context)
        self.context = context
        # APIクライアントセットアップ
        self.client = ApiClient(
            self.context.config.arve,
        )

    def execute(self):
        """ARVEお客さま情報登録実行"""
        logger = self.logger

        logger.info("ARVEお客さま情報登録開始。")

        # ARVEお客さま情報取得API取得
        res = self.client.get_all_pages()

        if len(res) == 0:
            logger.warning("ARVEお客様情報の取得結果が0件のため登録を行いませんでした")
            return

        # DTOに格納
        arve_custs = [ArveCustomerInfoResponseDto(**item) for item in res]

        # Entityに変換
        arve_customer_infos = [item.to_dict() for item in arve_custs]

        try:

            with get_session() as session:
                self.logger.info("ARVEお客さま情報登録")
                # ARVEお客さま情報登録
                session.execute(insert(TArveCustomerInfo), arve_customer_infos)
                session.flush()

                self.logger.info("組織ID紐づけ")

                # 組織ID紐づけ
                sql_query = load_sql_file("org_id_link_t_arve_customer_info.sql")
                session.execute(text(sql_query))
                session.commit()

        except Exception:
            self.logger.exception("ARVEお客さま情報登録失敗しました。")

        logger.info("ARVEお客さま情報登録終了。")
