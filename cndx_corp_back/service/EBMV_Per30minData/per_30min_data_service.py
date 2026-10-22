import os

from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.EBMV_Per30minData.per_30min_data_component import (
    Per30minDataComponent,
)


class Per30minDataService:

    @service
    def get_per_30min_data_list(
        self,
        request_dict: dict,
        org_type_code=None,
        login_org_id=None,
        user_id=None,
        role_id=None,
        logger=None,
    ):
        """
        建物IDを元に30分値登録状況を取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 処理開始")

        return Per30minDataComponent().execute(
            request_dict, org_type_code, login_org_id, user_id, role_id
        )
