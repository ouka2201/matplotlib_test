import os
from datetime import datetime

import pandas as pd
from flask import current_app
from sqlalchemy import bindparam, func, literal_column, or_, select

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.entity.t_announcements_entity import TAnnouncements


class AnnouncementsInfoService:

    @service
    def get_announcements_info(self, request_dict: dict, logger=None):
        """
        お知らせ情報取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 不要なパラメータを除外

        with get_scoped_session() as session:
            stmt = (
                select(
                    func.to_char(TAnnouncements.start_date, "YYYY/MM/DD").label(
                        "start_date"
                    ),
                    TAnnouncements.title,
                    TAnnouncements.message1,
                    TAnnouncements.message2,
                    TAnnouncements.message3,
                )
                .where(
                    # 終了日が NULL か、date 以上
                    or_(
                        TAnnouncements.end_date.is_(None),
                        TAnnouncements.end_date >= bindparam("date"),
                    ),
                    # 開始日が date 以下
                    TAnnouncements.start_date <= bindparam("date"),
                    # 削除フラグ
                    TAnnouncements.delete_flg.is_(False),
                )
                .order_by(TAnnouncements.start_date.desc())
            )

            login_date = datetime.today()
            request_date = login_date.strftime("%Y/%m/%d")
            df_result = pd.read_sql(
                stmt, session.connection(), params={"date": request_date}
            )

            logger.debug(f"実行SQL: {stmt} ")
            logger.debug(f"データ: {df_result} ")

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return df_result.to_dict(orient="records")
