import json
import os

from flask import Response, current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.building import building_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.building.building_group_service import BuildingGroupService
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

REQUIRED_KEYS = ["corporate_number", "agreement_category", "org_id", "building_id"]


class BuildingGroupAPI(MethodView):
    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):
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

        # 各フィールドの型チェック
        for field, expected_type in FIELD_TYPE_RULES.items():
            if field in dict_request_data:
                value = dict_request_data[field]

                if value is None:
                    continue

                if isinstance(value, str):
                    value = value.strip()
                    dict_request_data[field] = value

                if field == "benchmark_val":
                    if value == "":
                        continue

                    try:
                        float(value)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"{field} の形式が不正です。数値として解釈できません: {value}"
                        )
                        return (
                            Response(
                                json.dumps(
                                    {
                                        "message": f"{field} は数値形式で指定してください。"
                                    },
                                    ensure_ascii=False,
                                ),
                                content_type="application/json; charset=utf-8",
                            ),
                            400,
                        )
                else:
                    if not isinstance(value, expected_type):
                        logger.warning(
                            f"{field} の型が不正です。期待: {expected_type.__name__}, 実際: {type(value).__name__}"
                        )
                        return (
                            Response(
                                json.dumps(
                                    {"message": f"{field} の形式が正しくありません。"},
                                    ensure_ascii=False,
                                ),
                                content_type="application/json; charset=utf-8",
                            ),
                            400,
                        )

        user_id = user_context.get("user_id")
        try:
            # Service呼び出し：建物情報更新（単体）
            res = BuildingGroupService().update_single_building(
                dict_request_data, user_id
            )
        except Exception as e:
            logger.error("建物情報更新時に例外発生：" + str(e))
            return (
                Response(
                    json.dumps(
                        {"message": get_message("FAILED", data="建物情報の更新")},
                        ensure_ascii=False,
                    ),
                    content_type="application/json; charset=utf-8",
                ),
                500,
            )

        logger.info(f"{os.path.basename(__file__)}：建物情報更新処理終了。")
        return jsonify(res), 200


# APIルーティング登録：URLは /api/building/info
building_bp.add_url_rule(
    "/info",
    view_func=BuildingGroupAPI.as_view("update_building_info"),
    methods=["POST"],
)
