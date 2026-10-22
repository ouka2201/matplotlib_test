import os

from flask import current_app

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.MSOG_corprationMstOperation.corpration_basic_inquiry_component import (
    CorprationBasicInquiryComponent,
)
from cndx_corp_back.logic.MSOG_corprationMstOperation.search_agreement_org_logic import (
    SearchAgreementOrgLogic,
)


class CorprationBasicInquiryService:

    @service
    def get_corpration_building_info(
        self, request_dict: dict, user_id, user_role, logger=None
    ):
        """
        企業建物情報取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 不要なパラメータを除外
        # ファイル転送 comp を呼出
        return CorprationBasicInquiryComponent().execute(
            request_dict, user_id, user_role
        )

    @service
    def search_agreement_org(self, request_dict: dict, logger=None):
        """
        利用者組織情報から org_id,org_name 取得
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 同意書未取得の場合
        if request_dict.get("agreement_category") == "00":
            # 未取得用ロジックで返す
            results = SearchAgreementOrgLogic.build_results(self)
        else:
            # それ以外の場合 テーブルからSELECT
            with get_scoped_session() as session:
                results = SearchAgreementOrgLogic.get_agreement_org(
                    self, session, request_dict
                )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return results
