import os

from flask import abort, current_app

from cndx_corp_back.logic.report.cn_karte_list_component import (
    CnKarteListComponent,
)


class CnKarteListService:

    def get_cn_karte_list(self, request_dict: dict, user_context) -> list | None:
        logger = current_app.logger
        logger.debug(f"{os.path.basename(__file__)} get_cn_karte_list 開始")

        try:
            corporate_number = request_dict.get("corporate_number", "").strip()
            org_id = request_dict.get("org_id", "").strip()
            agreement_category = request_dict.get("agreement_category", "").strip()

            if not corporate_number or not org_id:
                logger.warning(
                    "法人番号または組織IDが未指定です。空リストを返却します。"
                )
                abort(400)

            result_list = CnKarteListComponent().execute(
                corporate_number, org_id, agreement_category, user_context
            )

            logger.debug(f"{os.path.basename(__file__)} get_cn_karte_list 終了")

            return result_list

        except Exception as e:
            logger.error(f"{os.path.basename(__file__)} 想定外エラー発生")
            abort(500)
