from sqlalchemy import text

from cndx_corp_batch.common.db import get_session
from cndx_corp_batch.common.query import load_sql_file


class GetZipReportUsersService:
    def __init__(self, logger):
        """
        Parameters:
            logger: ロガー
        """
        self.logger = logger

    def execute(self, target_year_month: str):
        """zip化対象取得

        Args:
            target_year_month (string): 対象年月

        Returns:
            List: zip化対象リスト
        """

        params = {"target_year_month": target_year_month}
        with get_session() as session:
            sql_query = load_sql_file("get_zip_report_users.sql")
            result = session.execute(text(sql_query), params)

        # ログ出力
        logger = self.logger
        logger.info("zip化対象取得完了")

        return result
