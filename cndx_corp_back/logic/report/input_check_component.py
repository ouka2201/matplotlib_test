import os

from flask import current_app

from cndx_corp_back.common.decorators import component
from cndx_corp_back.common.validation import (
    integer_format_check,
    length_check,
    newline_check,
    required_check,
)


# TODO 廃棄
class InputCheckComponent:

    @component
    def check_for_create(self, request_dict, message_list: list, logger=None):
        """
        レポート作成用入力チェック
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # チェック処理
        item_nm = "法人番号"
        corporate_number = request_dict["corporate_number"]
        if required_check(corporate_number, item_nm, message_list):
            length_check(corporate_number, item_nm, message_list, 13, 13)
            integer_format_check(corporate_number, item_nm, message_list)
            newline_check(corporate_number, item_nm, message_list)

        item_nm = "対象年度"
        fiscal_year = request_dict["fiscal_year"]
        if required_check(fiscal_year, item_nm, message_list):
            length_check(fiscal_year, item_nm, message_list, 4, 4)
            integer_format_check(fiscal_year, item_nm, message_list)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
