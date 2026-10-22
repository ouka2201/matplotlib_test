import os
from datetime import datetime, timedelta

from flask import abort, current_app

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.utils.dto_utils import include
from cndx_corp_back.utils.utils import get_message

allowed_key_get = {
    "bank_name",
    "corporation_name",
    "fiscal_year",
    "creation_date_from",
    "creation_date_to",
    "report_status",
    "branch_name",
}


class StatusManageService:
    """
    レポートステータス管理サービス
    """

    @service
    def get_report_info(self, request_dict: dict, logger=None):
        """レポート情報取得"""

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 不要なパラメータを除外
        request_dict = include(request_dict, allowed_key_get)

        with get_scoped_session() as session:

            query_filters = []

            query_filters.append(
                TReportStorageInfo.delete_flg == False
            )  # 削除フラグが False のもののみ対象

            for key, value in request_dict.items():
                if key == "fiscal_year" or key == "report_status":  # 完全一致のパターン
                    if value:  # TODO util で空文字除去か
                        query_filters.append(getattr(TReportStorageInfo, key) == value)
                elif key == "creation_date_from":
                    if value:
                        try:
                            date_from = datetime.strptime(value, "%Y-%m-%d")
                        except Exception as e:
                            abort(400, get_message("NOT_CORRECT", field="日付形式"))

                        query_filters.append(TReportStorageInfo.created_at >= date_from)
                elif key == "creation_date_to":

                    if value:
                        try:
                            date_to = datetime.strptime(value, "%Y-%m-%d")
                        except Exception as e:
                            abort(400, get_message("NOT_CORRECT", field="日付形式"))

                        date_to = date_to + timedelta(days=1)

                        query_filters.append(TReportStorageInfo.created_at <= date_to)
                else:
                    if value:
                        query_filters.append(
                            getattr(TReportStorageInfo, key).like(f"%{value}%")
                        )

            report_info_res = (
                session.query(TReportStorageInfo).filter(*query_filters).all()
            )

            # null 除外して dict に変換
            # report_info_list = [
            #     {k: v for k, v in r_info.to_dict().items() if v is not None}
            #     for r_info in report_info_res
            # ]
            report_info_list = [r_info.to_dict() for r_info in report_info_res]

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return report_info_list

    @service
    def post_report_info(self, logger=None):
        """レポート情報更新"""

        pass
