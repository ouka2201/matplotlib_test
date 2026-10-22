import os
from typing import Counter

import pandas as pd
from flask import abort, current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.common.validation import (
    allowed_characters_check,
    is_chara_code_ok,
    length_check,
    numeric_range_check,
    required_check,
)
from cndx_corp_back.logic.building_group_management.update_logic import (
    BuildingGroupLogic,
)
from cndx_corp_back.utils.utils import get_message


class BuildingGroupUpdateService:

    @service
    def upsert(self, request_dict: dict, logger=None):
        """
        建物グループ選択肢_更新処理
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        user_id = request_dict["userId"]
        group_names = []  # group名のlist
        self.err_list = []  # errorメッセージ詰め込み用のリスト
        # 入力チェック
        for group in request_dict["editedGroupData"]:
            group_names.append(group["group_name"])

            # グループ名の文字数チェック
            length_check(
                group["group_name"],
                "グループNo" + group["group_id"],
                self.err_list,
                min_length=None,
                max_length=30,
                msg_id=None,
            )

            for i in range(1, 8):
                # 選択肢の文字数チェック
                length_check(
                    group[f"select_item{i}"],
                    "グループNo" + group["group_id"] + "の" + f"選択肢{i}",
                    self.err_list,
                    min_length=None,
                    max_length=20,
                    msg_id=None,
                )

                # 改行、外字は許可しない
                allowed_characters_check(
                    group[f"select_item{i}"],
                    f"select_item{i}",
                    self.err_list,
                    allow_numeric=True,
                    allow_lowercase=True,
                    allow_uppercase=True,
                    allow_kana=True,
                    allow_space=True,
                    allow_symbols=True,
                    allow_newline=False,
                    allow_fullwidth_numeric=True,
                    allow_fullwidth_lowercase=True,
                    allow_fullwidth_uppercase=True,
                    allow_fullwidth_kana=True,
                    allow_fullwidth_space=True,
                    allow_fullwidth_symbols=True,
                    allow_external_chars=False,
                )
                if len(self.err_list) > 0:
                    abort(400, self.err_list)

            # 空白文字を削除し、dict=>listに変換
            checkList = list(filter(lambda a: a != "", list(group.values())[5:]))

            # 選択肢が入力されているか
            if group["group_name"] != "" and len(checkList) == 0:
                abort(
                    400,
                    get_message(
                        "GROUP_HAS_NO_SELECT_ITEM",
                        item_name=f"グループ {group["group_id"]}",
                    ),
                )

            # 選択肢の重複チェック
            if len(checkList) > 0:
                # 重複した値をlistに詰める
                duplicate_elements = [
                    item for item, count in Counter(checkList).items() if count > 1
                ]
                if len(duplicate_elements) > 0:
                    for item in duplicate_elements:
                        duplicate_key = ""
                        for k, v in group.items():
                            if v == item:
                                duplicate_key = duplicate_key + k + "と"
                        error_message = duplicate_key.replace("select_item", "選択肢")
                        abort(
                            400,
                            get_message(
                                "GROUP_MASTER_DUPLICATED",
                                item_name=f"{error_message[:-1]}",
                            ),
                        )

        # group名の重複チェック(既存の項目)
        resultList = BuildingGroupLogic.get_building_group(
            request_dict["editedGroupData"][0], logger=None
        )
        for result_dict in resultList:
            for req_dict in request_dict["editedGroupData"]:
                if (
                    req_dict["group_id"] != result_dict["group_id"]
                    and req_dict["group_name"] == result_dict["group_name"]
                    and req_dict["group_name"] != ""
                    and result_dict["group_name"] != ""
                ):
                    duplicate_group_text = (
                        "グループ"
                        + req_dict["group_id"]
                        + "とグループ"
                        + result_dict["group_id"]
                        + "のグループ名が"
                    )
                    abort(
                        400,
                        get_message(
                            "GROUP_MASTER_DUPLICATED",
                            item_name=f"{duplicate_group_text[:-1]}",
                        ),
                    )

        # group名の重複チェック(新規登録項目)
        duplicate_group_name = [
            item for item, count in Counter(group_names).items() if count > 1
        ]
        if len(duplicate_group_name) > 0:
            duplicate_group = ""
            for group in request_dict:
                for name in duplicate_group_name:
                    if name == group["group_name"]:
                        duplicate_group = (
                            duplicate_group + "グループ " + group["group_id"] + "と"
                        )
            abort(
                400,
                get_message(
                    "GROUP_MASTER_DUPLICATED", item_name=f"{duplicate_group[:-1]}"
                ),
            )

        # 登録処理
        for dict in request_dict["editedGroupData"]:
            BuildingGroupLogic.upsert_building_group(self, dict, user_id, logger=None)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return {"message": get_message("SUCCESS")}
