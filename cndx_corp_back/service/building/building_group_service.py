import math
import os
import traceback

from flask import abort, current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.building.building_group_logic import BuildingGroupLogic
from cndx_corp_back.utils.number_utils import (
    format_decimal_with_scale,
    normalize_decimal_string,
)
from cndx_corp_back.utils.utils import get_message


class BuildingGroupService:
    # グループ設定
    allowed_group_keys = {"group1", "group2", "group3", "group4", "group5"}

    # =============================
    # グループ一括更新
    # =============================
    @service
    def update_group_fields(self, dto, logger=None):
        logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}：建物グループ更新処理開始。")

        building_ids = dto.building_ids
        group_fields = dto.group_fields
        updated_by = dto.updated_by

        if not building_ids or not isinstance(building_ids, list):
            abort(
                400,
                get_message(
                    "REQUIRED_TYPE", item_name="building_ids", data_type="リスト形式"
                ),
            )
        if not group_fields or not isinstance(group_fields, dict):
            abort(
                400,
                get_message(
                    "REQUIRED_TYPE", item_name="group_fields", data_type="辞書形式"
                ),
            )

        # 許可されたグループキーのみフィルタリング
        valid_group_fields = {
            k: v for k, v in group_fields.items() if k in self.allowed_group_keys
        }
        if not valid_group_fields:
            abort(400, get_message("GROUP_NONE"))

        logic = BuildingGroupLogic()
        try:
            result = logic.update_groups(building_ids, valid_group_fields, updated_by)
        except Exception as e:
            logger.error(
                f"{os.path.basename(__file__)}：建物グループ更新処理で例外発生。\n{traceback.format_exc()}"
            )
            abort(400, description=str(e))

        logger.info(f"{os.path.basename(__file__)}：建物グループ更新処理終了。")
        return result

    # =============================
    # 建物情報 単体更新処理（建物情報編集→登録）
    # =============================
    @service
    def update_single_building(self, request_data, user_id, logger=None):
        logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}：建物情報単体更新処理開始。")

        corporate_number = request_data.get("corporate_number")
        agreement_category = request_data.get("agreement_category")
        org_id = request_data.get("org_id")
        building_id = request_data.get("building_id")
        updated_by = user_id

        if not (corporate_number and agreement_category and org_id and building_id):
            abort(
                400,
                get_message(
                    "REQUIRED",
                    "corporate_number, agreement_category, org_id, building_id",
                ),
            )

        keys = {
            "b_corporate_number": corporate_number,
            "b_agreement_category": agreement_category,
            "b_org_id": org_id,
            "b_building_id": building_id,
        }

        update_fields = {}
        for k, v in request_data.items():
            if k not in {
                "corporate_number",
                "agreement_category",
                "org_id",
                "building_id",
                "updated_by",
            }:
                if v == "":  # 空文字处理
                    update_fields[k] = None
                elif isinstance(v, float) and math.isnan(v):  # NaN处理
                    update_fields[k] = None
                else:
                    if k == "benchmark_val":
                        update_fields[k] = normalize_decimal_string(v)
                    elif k == "benchmark_denom":
                        update_fields[k] = format_decimal_with_scale(v, 3)
                    else:
                        update_fields[k] = v

        if not update_fields:
            abort(400, get_message("NOT_FOUND", item_name="更新対象の項目"))

        logic = BuildingGroupLogic()
        try:
            logic.update_single_building(keys, update_fields, updated_by)
        except Exception as e:
            logger.error(
                f"{os.path.basename(__file__)}：単体建物更新エラー。\n{traceback.format_exc()}"
            )
            abort(500, description=str(e))

        logger.info(f"{os.path.basename(__file__)}：建物情報単体更新処理終了。")
        return {"message": get_message("UPDATE", field="建物情報")}
