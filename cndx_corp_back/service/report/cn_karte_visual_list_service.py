import os

from flask import abort, current_app

from cndx_corp_back.logic.report.cn_karte_visual_list_component import (
    CnKarteVisualListComponent,
)


class CnKarteVisualListService:
    def get_cn_karte_visual_list(self, request_dict: dict, user_context) -> list | None:
        logger = current_app.logger
        logger.debug(f"{os.path.basename(__file__)} get_cn_karte_visual_list 開始")

        try:
            corporate_number = request_dict.get("corporate_number", "").strip()
            org_id = request_dict.get("org_id", "").strip()

            if not corporate_number or not org_id:
                logger.warning(
                    "法人番号または組織IDが未指定です。空リストを返却します。"
                )
                abort(400)

            result_list = CnKarteVisualListComponent().execute(
                request_dict, user_context
            )

            logger.debug(f"{os.path.basename(__file__)} get_cn_karte_visual_list 終了")

            return result_list

        except Exception as e:
            logger.error(f"{os.path.basename(__file__)} 想定外エラー発生: {e}")
            abort(500)
