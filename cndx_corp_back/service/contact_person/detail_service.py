import os
from datetime import datetime

import pandas as pd
from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.contact_person.contact_person_logic import ContactPersonLogic


class ContactPersonDetailService:

    @service
    def get_contact_pserson_info(
        self,
        dict_request_data: dict,
        login_user_id=None,
        role_id=None,
        org_type_code=None,
        org_id=None,
        logger=None,
    ):
        """
        担当者設定画面の初期表示で必要な、会社情報および、担当者情報を取得する
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        corporateNumber = dict_request_data["corporate_number"]

        # SQL処理（お客様情報取得）
        result = ContactPersonLogic.getCompanyInfo(
            self, dict_request_data, login_user_id, role_id, org_type_code, org_id
        )

        # SQL処理（担当者一覧取得）
        personList = ContactPersonLogic.getContactPersonList(
            self, corporateNumber, org_type_code
        )

        # 時間のフォーマット変換(TODO:必要に応じて共通化する)
        for person in personList:
            date_str = person["consent_receipt_date"]
            before_format = "%Y%m%d"
            after_format = "%Y/%m/%d"
            if date_str:
                date_obj = datetime.strptime(date_str, before_format)
                new_date_str = date_obj.strftime(after_format)
                person["consent_receipt_date"] = new_date_str

        result.append(personList)
        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result
