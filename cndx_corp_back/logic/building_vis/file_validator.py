from typing import ClassVar

import pandas as pd
from flask import abort
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common import constants_colums
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.db_base_handler import BaseRepository
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.logic.building_vis import building_vis_constants as vis_constants
from cndx_corp_back.logic.building_vis.building_vis_constants import (
    SHEET_KEYWORDS,
    SHEET_NAME_LIST,
    SheetName,
)


class FileValidation:

    # マスタ存在チェック対象
    _MASTER_MODEL_MAP: ClassVar[dict[str, BaseRepository]] = {
        "m_building": MBuilding,
        "m_corporate_basic": MCorporateBasic,
    }

    def __init__(self, *, input_file: FileStorage) -> None:
        self.input_file: FileStorage = input_file
        self.error_list: list[str] = []

    def check_required_sheet(
        self, target_sheet_names: list[str], required_sheet_names: tuple[str]
    ):

        # シート存在チェック
        not_exist_sheet_list: list = []
        for sheet_name in required_sheet_names:
            if sheet_name not in target_sheet_names:
                not_exist_sheet_list.append(sheet_name)
        if len(not_exist_sheet_list) > 0:
            self.error_list.append(
                f"「{','.join(not_exist_sheet_list)}」が存在していません。"
            )
        return self.error_list

    def check_corporate_info(
        self,
        *,
        cur_sheet_df: pd.DataFrame,
        request_dict: dict,
        org_id: str,
    ) -> pd.DataFrame:
        """_summary_

        Args:
            cur_sheet_df (pd.DataFrame): _description_
            session (scoped_session): _description_
            agreement_category (str): _description_
            org_id (str): _description_

        Returns:
            pd.DataFrame: _description_
        """
        # Requestから会社名取得
        company_name = request_dict.get("company_name", None)

        # 1列2列を 項目：値の辞書にする
        info_dict = dict(zip(cur_sheet_df[1], cur_sheet_df[2]))

        # 企業名
        sheet_company_name = info_dict[
            vis_constants.SHEET_KEYWORDS.get(
                vis_constants.SheetName.INFO.value
            ).company_name
        ]

        # 企業存在チェック
        is_company_exist = self.check_exist_data(
            "m_corporate_basic", {"company_name": sheet_company_name}
        )
        if not is_company_exist:
            self.error_list.append(f"存在しない会社名。{sheet_company_name}")
            return

        # 画面とシート上企業名のチェック
        if sheet_company_name != company_name:
            self.error_list.append(f"入力ファイルの企業名と不一致です。\
                シート上企業名：{sheet_company_name}, 画面上企業名：{company_name}")
            return

    def check_exist_data(self, target_table_name: str, filters: dict[str, any]) -> bool:
        """マスタ存在チェック

        Args:
            target_table_name (str): チェック対象テーブル

        Raises:
            ValueError: _description_

        Returns:
            bool: False:存在しない
        """
        model = self._MASTER_MODEL_MAP.get(target_table_name)
        if not model:
            raise ValueError(f"存在しないマスタ: {target_table_name}")

        with get_scoped_session() as session:
            repo = BaseRepository(session, model)
            is_exist: bool = repo.exists_by(**filters)

        return is_exist

    def check_required_column(
        target_df: pd.DataFrame, headers: list[str], year_month_list: list[str]
    ) -> bool:
        """
        df に必要な列がすべて含まれているか判定する

        Args:
            df: 対象の DataFrame
            headers: 必須の列名リスト
            year_month_list: 年月列名リスト

        Returns:
            bool: すべて含まれていれば True、足りなければ False
        """
        required_columns = set(headers + year_month_list)
        return required_columns.issubset(target_df.columns)

    def validate_headers_in_order(
        df: pd.DataFrame, required_headers: list[str]
    ) -> bool:
        """
        必須カラムが順番通りに含まれているかチェック

        Args:
            df: DataFrame
            required_headers: 順序を守るべき必須カラムリスト

        Returns:
            bool: 正しければ True
        """
        columns = list(df.columns)

        idx = 0
        for col in columns:
            if col == required_headers[idx]:
                idx += 1
                if idx == len(required_headers):
                    # 全て見つけた
                    return True
        # 途中で全て見つからなかった
        return False

    def validate_columns_order(
        df: pd.DataFrame, year_month_list: list[str], year_month_start_col: int
    ) -> bool:
        """
        カラム順序と開始位置をチェックする

        Args:
            df: DataFrame
            headers: 先頭に並ぶべきヘッダ
            year_month_list: 年月列
            year_month_start_col: 年月列が始まるインデックス（0-origin）

        Returns:
            bool: 全て条件を満たしていれば True
        """
        columns = list(df.columns)

        # 年月部分チェック
        actual_year_months = columns[year_month_start_col:]
        if actual_year_months != year_month_list:
            print(f"年月列が一致しません: {actual_year_months} != {year_month_list}")
            return False

        return True


def col_idx_to_excel(col_idx: int) -> str:
    """
    0-based の列番号を Excel の列名 (A, B, C... AA, AB...) に変換
    """
    letters = ""
    col_idx += 1  # 1-based に変換
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def check_cell_value(
    df: pd.DataFrame, row_idx: int, col_idx: int, target: str, error_list: list
) -> bool:
    """
    DataFrame の特定セルを比較し、一致しなければエラー位置を error_list に追加

    Parameters
    ----------
    df : pd.DataFrame
    row_idx : int
        行番号 (iloc ベース, 0スタート)
    col_idx : int
        列番号 (iloc ベース, 0スタート)
    target : str
        比較対象の文字列
    error_list : list
        エラーセルの位置を格納するリスト (例: ["C5", "A2"])

    Returns
    -------
    bool
        一致すれば True, 不一致または範囲外なら False
    """
    try:
        cell_value = df.iloc[row_idx, col_idx]
    except IndexError:
        cell_ref = f"{col_idx_to_excel(col_idx)}{row_idx+1}"
        error_list.append(cell_ref)
        return False

    if str(cell_value) != str(target):
        cell_ref = f"{col_idx_to_excel(col_idx)}{row_idx+1}"
        error_list.append(cell_ref)
        return False

    return True
