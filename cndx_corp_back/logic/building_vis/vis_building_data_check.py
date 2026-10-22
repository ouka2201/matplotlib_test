import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Counter

import openpyxl
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common.decorators import component
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.logic.building_vis import building_vis_constants as vis_constants
from cndx_corp_back.logic.building_vis.vis_file_check import VisFileCheck


@component
class VisBuilidingDataCheck(VisFileCheck):
    def __init__(
        self,
        input_file: FileStorage,
        logger: CorpLogger,
        session: scoped_session,
        org_id: str,
        user_id: str,
        request_dict: dict[str, any],
    ) -> None:
        super().__init__(input_file, logger, session, org_id, user_id, request_dict)

    def execute(self):
        wb = openpyxl.load_workbook(self.input_file.stream, data_only=True)

        # 必須シートチェック
        self.check_required_sheet(wb, vis_constants.building_required_sheet_names)

        if len(self.format_errors) > 1:
            # フォーマットチェックエラー
            return self.format_errors

        ws_beshi = wb["別紙"]
        ws_aggree = wb["同意書"]

        # 必須列チェック
        headers = [
            "会社名",
            "法人番号",
            "物件番号",
            "物件名",
            "所在地",
            "所在地",
            "供給地点特定番号",
            "店所番号",
            "お客さま番号",
        ]
        self.check_required_headers(ws_beshi, headers, start_col="B", start_row=3)

        # セル値チェック
        self.check_cell(ws_aggree, "C24", "会社名")

        if len(self.format_errors) > 1:
            # フォーマットチェックエラー
            return self.format_errors

        # 企業名チェック
        file_company_name = ws_aggree["D25"].value

        if not file_company_name:
            self.data_errors.append("企業名が入力されていません。")

        # 物件番号、物件名必須チェック
        ws_beshi_max_row = self._get_effective_max_row(ws_beshi)
        for row in range(ws_beshi_max_row, 3, -1):
            if ws_beshi[f"{"F"}{row}"].value not in (None, ""):
                ws_beshi_max_row = row
                break
        for row in range(4, ws_beshi_max_row + 1):
            # F〜I列のどれかに値があるか確認
            if any(ws_beshi[f"{col}{row}"].value for col in ["G", "H", "I"]):
                missing_cells = []
                for col in ["D", "E", "F"]:
                    if ws_beshi[f"{col}{row}"].value in (None, ""):
                        missing_cells.append(f"{col}{row}")

                    if col == "F":
                        f_value = ws_beshi[f"F{row}"].value
                        if f_value not in (None, ""):
                            if f_value not in vis_constants.pref_check_list:
                                self.data_errors.append(
                                    f"{ws_beshi.title}!F{row} の値 '{f_value}' は不正です。\n"
                                    f" 都道府県はプルダウンから選択しなおしてください。"
                                )

                if missing_cells:
                    msg = f"{ws_beshi.title}!{missing_cells} が入力されていません。"
                    self.data_errors.append(msg)

        # 供給地点特定番号、ep店番、epお客さま番号数字だけcheck

        # カラム桁数チェック
        self.check_column_length(
            ws_beshi, col="D", length=100, start_row=4, not_fixed_check_flg=True
        )
        self.check_column_length(
            ws_beshi, col="E", length=50, start_row=4, not_fixed_check_flg=True
        )
        self.check_column_length(
            ws_beshi, col="G", length=100, start_row=4, not_fixed_check_flg=True
        )
        # self.check_column_length(ws_beshi, col="C", length=13, start_row=4)
        self.check_column_length(
            ws_beshi, col="H", length=22, start_row=4, only_num=True
        )
        self.check_column_length(
            ws_beshi, col="I", length=3, start_row=4, only_num=True
        )
        self.check_column_length(
            ws_beshi, col="J", length=13, start_row=4, only_num=True
        )

        if len(self.data_errors) > 1:
            # フォーマットチェックエラー
            return self.data_errors

        # self.check_decimal_precision(
        #     ws_aggree,
        #     start_col_letter="D",
        #     max_precision=25,
        #     max_scale=3,
        #     min_row=6)

        # 拠点重複チェック
        location_cd_list = self.get_location_cd_list(
            ws_beshi, start_row=4, start_col_letter="D", dup_check_flg=True
        )

        # counter = Counter(location_cd_list)
        # duplicates_building = [item for item, count in counter.items() if count > 1]

        if len(location_cd_list) > 0:
            dup_msg = "\n ".join(
                [f"(行{row}: {val})" for row, val in location_cd_list.items()]
            )
            self.data_errors.append(f"以下の物件番号が重複しています: \n{dup_msg}")
            # データチェックエラー
            return self.data_errors

        self.check_company_name(file_company_name=file_company_name)

        if len(self.check_file_company_name) > 1:
            # フォーマットチェックエラー
            return self.check_file_company_name

        return file_company_name
