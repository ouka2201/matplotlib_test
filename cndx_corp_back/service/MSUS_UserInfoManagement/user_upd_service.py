import os

from flask import current_app
from pydantic import ValidationError

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSUS_UserInfoManagement.user_upd_logic import (
    UserUpdLogic,
)


class UserUpdService:

    @service
    def execute_user_upd(request_data, user_id, logger=None):
        """
        ユーザ更新
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        with get_scoped_session() as session:
            try:
                # コンポーネントを呼び出す
                result = UserUpdLogic().upd_user(request_data, user_id, session)
            except ValidationError as e:
                raise e
            except Exception as e:
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return result
