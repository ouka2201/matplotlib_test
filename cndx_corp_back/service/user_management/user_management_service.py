from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.user_management.user_insert_component import (
    UserInsertComponent,
)


class UserManagementService:

    @service
    def execute_user_insert(self, user_dto, logger=None):
        """
        ユーザ登録
        """

        if logger is None:
            logger = current_app.logger
        # コンポーネントを呼び出す
        return UserInsertComponent().insert_user(user_dto)
