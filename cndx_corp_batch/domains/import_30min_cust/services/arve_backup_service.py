from datetime import date

from sqlalchemy import insert, select, text

from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.entity.t_arve_customer_info_entity import (
    TArveCustomerInfo,
)
from cndx_corp_batch.common.entity.t_historical_arve_customer_info_entity import (
    THistoricalArveCustomerInfo,
)
from cndx_corp_batch.common.query import load_sql_file


class ArveBackupService:
    """
    ARVEバックアップサービス
    """

    def __init__(self, logger):
        """
        Parameters:
            logger (_type_): _description_
        """
        self.logger = logger

    def execute(self, historical_ymd: date):
        """ARVEデータバックアップ実行

        Args:
            historical_ymd (date): 過去分ARVEお客さま情報年月
        """

        try:
            with get_session() as session:
                # 先月データバックアップ
                current_ym = int(historical_ymd.strftime("%Y%m"))

                original_columns = [c for c in TArveCustomerInfo.__table__.columns]

                stmt = insert(THistoricalArveCustomerInfo).from_select(
                    [THistoricalArveCustomerInfo.acquisition_year_month]
                    + original_columns,
                    select(current_ym, *original_columns),
                )

                session.execute(stmt)
                session.flush()

                # ARVEお客さま情報削除
                sql_query = load_sql_file("truncate_t_arve_customer_info.sql")
                session.execute(text(sql_query))
                session.commit()

        except Exception:
            self.logger.exception("先月データバックアップ失敗しました。")
