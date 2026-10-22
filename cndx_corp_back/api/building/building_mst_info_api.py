import json
import os

from flask import Response, current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.building import building_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.building.building_mst_service import (
    BuildingMstService,
)
from cndx_corp_back.utils.utils import get_message

# from flask_jwt_extended import jwt_required


FIELD_TYPE_RULES = {
    "corporate_number": str,
    "agreement_category": str,
    "org_id": str,
    "building_id": str,
    "building_name": str,
    "building_address_prefecture": str,
    "building_address_city": str,
    "industry_class_detail_code": str,
    "industry_class_detail_name": str,
    "benchmark_denom": str,
    "benchmark_val": str,
    "group1": str,
    "group2": str,
    "group3": str,
    "group4": str,
    "group5": str,
    "updated_by": str,
}

REQUIRED_KEYS = ["corporate_number", "agreement_code", "org_id", "building_id"]


class BuildingMstInfoAPI(MethodView):

    @controller
    def get(self, dict_request_data, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}：建物情報更新処理開始。")

        # 必須項目の存在チェック
        for key in REQUIRED_KEYS:
            if key not in dict_request_data:
                logger.warning(f"{key} がリクエストに存在しません。")
                return (
                    Response(
                        json.dumps(
                            {"message": f"{key} は必須項目です。"}, ensure_ascii=False
                        ),
                        content_type="application/json; charset=utf-8",
                    ),
                    400,
                )

            # try:
            # Service呼び出し：建物情報更新（単体）
        res = BuildingMstService().get_building_mst_info(dict_request_data)
        # except Exception as e:
        #     logger.error("建物情報更新時に例外発生：" + str(e))
        #     return Response(
        #         json.dumps({"message": get_message("FAILED", data="建物情報の更新")}, ensure_ascii=False),
        #         content_type="application/json; charset=utf-8"
        #     ), 500

        logger.info(f"{os.path.basename(__file__)}：建物情報更新処理終了。")
        return jsonify({"result": res}), 200


# APIルーティング登録：URLは /api/building/info
building_bp.add_url_rule(
    "/basic_info",
    view_func=BuildingMstInfoAPI.as_view("get_building_mst_info"),
    methods=["GET"],
)
