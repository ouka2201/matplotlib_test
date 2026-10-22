import os
from datetime import datetime

import numpy as np
import pandas as pd
from flask import abort, current_app
from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import aliased

from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_user_entity import MUser
from cndx_corp_back.utils.utils import get_message


class UserInfoLogoutLogic:
    @component
    def introduction(self, request_dict, session, user_id, logger=None):
        """
        ユーザー一括失効処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            user_ids = [u["user_id"] for u in request_dict.get("users", [])]
            if not user_ids:
                abort(400, description=get_message("NOT_CORRECT", data="ユーザーID"))

            logger.info(f"強制ログアウト対象ユーザー: {user_ids}")

            system_user = user_id

            update_values = {
                "user_status": "4",
                "updated_by": system_user,
            }

            formatted_ids = ", ".join([f"'{uid}'" for uid in user_ids])

            logger.info(
                "実行SQL(UPDATE): "
                f"UPDATE m_user "
                f"SET user_status = '4', updated_by = '{system_user}' "
                f"WHERE user_id IN ({formatted_ids});"
            )

            # 更新実行
            update_count = (
                session.query(MUser)
                .filter(MUser.user_id.in_(user_ids))
                .update(update_values, synchronize_session=False)
            )

            logger.info(f"更新件数: {update_count}")

            logger.info(f"{os.path.basename(__file__)}処理終了。")

            return {"success": "ok"}

        except Exception as e:
            logger.error(f"{os.path.basename(__file__)}の処理が失敗しました。")
            raise
