import os

import pandas as pd
from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.contact_person.delete_logic import ContactPersonDeleteLogic
from cndx_corp_back.logic.contact_person.update_insert_logic import (
    ContactPersonUpdateLogic,
)
from cndx_corp_back.utils.utils import get_message


class ContactPersonUpdateService:

    @service
    def person_update(self, request_dict: dict, login_user_id=None, logger=None):
        """
        企業情報更新
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 担当者リストと法人番号・ログインユーザIDを切り離す
        df_request = pd.DataFrame(request_dict)
        df_staff_list = pd.DataFrame(df_request["stafflist"].to_dict()).transpose()
        # 追加・更新処理呼び出し
        dict_target = ContactPersonUpdateLogic.update(
            self, request_dict["corporate_number"], login_user_id, df_staff_list
        )

        # 画面で上書きした元データは削除
        ContactPersonDeleteLogic.delete(self, dict_target, login_user_id=login_user_id)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return {"message": get_message("SUCCESS")}
