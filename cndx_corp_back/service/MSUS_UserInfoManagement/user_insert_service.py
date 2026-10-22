import os

from flask import current_app
from pydantic import ValidationError

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSUS_UserInfoManagement.user_insert_logic import (
    UserInsertLogic,
)


class UserInsertService:

    @service
    def execute_user_insert(request_data, user_id, login_org_type_code, logger=None):
        """
        ユーザ登録
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        with get_scoped_session() as session:
            # コンポーネントを呼び出す
            try:
                result = UserInsertLogic().insert_user(
                    request_data, user_id, login_org_type_code, session
                )
            except ValidationError as e:
                raise e
            except Exception as e:
                raise

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return result
