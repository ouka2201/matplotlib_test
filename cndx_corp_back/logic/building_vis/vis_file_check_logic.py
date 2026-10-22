import copy
import math
import os
import re
import time
import traceback
from collections import defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import NamedTuple

import numpy as np
import pandas as pd
from common import utils
from dateutil.relativedelta import relativedelta
from flask import abort
from logic.building_vis.vis_building_data_check import ExcelFileCheck
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common import constants_colums, constants_values
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.db_base_handler import BaseRepository
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_competitor_industry import MCompetitorIndustry
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import MCorporateDetailsInfo
from cndx_corp_back.entity.t_annual_building_energy_aggregation_entity import (
    TAnnualBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_annual_corporate_energy_aggregation_entity import (
    TAnnualCorporateEnergyAggregation,
)
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_energy_storage_common_for_visualization import (
    TEnergyStorageCommonForVisualization,
)
from cndx_corp_back.entity.t_file import TFile
from cndx_corp_back.entity.t_kashika_business_hearing_data import (
    TKashikaBusinessHearingData,
)
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_monthly_corporate_energy_aggregation_entity import (
    TMonthlyCorporateEnergyAggregation,
)
from cndx_corp_back.entity.t_monthly_unit_denominator import TMonthlyUnitDenominator
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.logic.building_vis import building_vis_constants as vis_constants
from cndx_corp_back.logic.building_vis.building_vis_utils import (
    convert_year_month,
    df_to_repo,
    safe,
    set_target_entity,
    split_code_name,
)
from cndx_corp_back.logic.building_vis.file_validator import FileValidation
from cndx_corp_back.logic.building_vis.master_loader import MasterLoader
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent


class VisFileCheckLogic:
    def __init__(
        self,
        *,
        input_file: FileStorage,
        logger: CorpLogger,
        session: scoped_session,
        org_id: str,
        user_id: str,
        request_dict: dict[str, any],
    ) -> None:

        self.input_file: FileStorage = input_file

        self.error_list: list[str] = []
        self.logger = logger
        self.session = session
        self.org_id = org_id
        self.user_id = user_id
        self.request_dict = request_dict

        # self.tbuilding_list = list[TBuildingInfo]() # 対象外

        # 新規作成対象
        self.mbuliding_list = list[MBuilding]()
        self.company_name = None

    def main(self) -> dict[str, pd.DataFrame]:

        # 登録対象データ格納用辞書
        register_df_dic: dict[str, pd.DataFrame] = defaultdict(pd.DataFrame)
        try:
            # Excelファイル解析
            register_df_dic = self.file_data_process_main(self.input_file)
            ""
            return register_df_dic
        except Exception as e:
            self.logger.error("ファイルETL処理失敗しました。")
            self.logger.error(traceback.format_exc())
            raise e

    def file_data_process_main(self, input_file: FileStorage):

        self.logger.info(f"★処理対象ファイル名：{input_file.filename}")

        file_check = ExcelFileCheck()
        file_check.check_excel(input_file)
        if len(file_check.errors) > 0:
            for msg, coord in file_check.errors:
                self.logger.debug(f"[ERROR] {msg} (at {coord})")

        # 処理対象シート名取得
        parse_sheet_names = [
            item["name"] for item in vis_constants.BUILDING_SHEET_NAME_LIST
        ]

        # 処理対象シート名取得
        input_file_df = pd.ExcelFile(self.input_file)
        target_sheet_names = [
            sheet_name
            for sheet_name in (input_file_df.sheet_names)
            if sheet_name in parse_sheet_names
        ]

        # チェック用インスタンス
        validator = FileValidation(input_file=input_file)
        validator.error_list = validator.check_required_sheet(
            target_sheet_names, vis_constants.building_required_sheet_names
        )

        if len(validator.error_list) > 0:
            abort("400", validator.error_list)

        for sheet_name in target_sheet_names:
            # DataFrame加工処理
            self.get_entity_from_sheet(
                input_file=input_file,
                sheet_name=sheet_name,
                request_dict=self.request_dict,
                validator=validator,
            )

        if len(validator.error_list) == 0:
            file_upload = FileTransferComponent()

            # フォルダ構成名取得
            target_path_dict = {
                "put_sub_path": "input_excel_files",
                "org_type": "vis",
                "file_type": "building_data",
            }
            upload_target_path = file_upload.get_upload_path(
                target_path_dict=target_path_dict
            )
            # ファイル転送 comp を呼出
            FileTransferComponent().excute(
                input_file=input_file, upload_target_path=upload_target_path
            )

            energy_file_entity = TFile()
            energy_file_entity.file_name = input_file.filename
            energy_file_entity.file_path = os.path.join(
                upload_target_path, input_file.filename
            )
            energy_file_entity.file_type = "1"  # TODO

            self.session.add(energy_file_entity)
            self.session.commit()

        return

    def _get_energy_mapping_str(self) -> dict[str, MCorpCodeInfo]:
        # コードマスタからエネルギーカテゴリ取得
        code_repo = BaseRepository(self.session, model=MCorpCodeInfo)
        filters = {"code_type": "energy_category"}
        energy_category_rows = code_repo.find_all(**(filters or {}))

        # コードマスタからエネルギーコード取得 TODO コードマスタ構造変更 カテゴリとコード一行管理
        filters = {"code_type": "ENERGY"}
        energy_rows = code_repo.find_all(**(filters or {}))

        # エネルギー名: record 取得
        energy_dict: dict[str, MCorpCodeInfo] = {
            energy_row.jp_code_name: energy_row for energy_row in energy_rows
        }
        return energy_dict

    def makeup_df(self, cur_sheet_df: pd.DataFrame) -> pd.DataFrame:
        # cur_sheet_df.columns = [
        #     '_'.join(map(str, col)).strip()
        #     for col in cur_sheet_df.columns
        # ]

        # 不要な列を除外（Unnamed または 空文字）
        # Unnamed（無名）列をスキップ
        cur_sheet_df = cur_sheet_df.loc[
            :,
            ~cur_sheet_df.columns.to_frame()
            .apply(lambda x: x.astype(str).str.contains("Unnamed|^$", na=False))
            .any(axis=1),
        ]

        for col in cur_sheet_df.columns:
            # 文字列項目のnanを空白に変換
            if pd.api.types.is_object_dtype(
                cur_sheet_df[col]
            ) or pd.api.types.is_string_dtype(cur_sheet_df[col]):
                cur_sheet_df[col] = cur_sheet_df[col].fillna("")
            # 数字項目の桁数保持

            if pd.api.types.is_numeric_dtype(cur_sheet_df[col]):
                cur_sheet_df[col] = cur_sheet_df[col].fillna(0)

        # ヘッダの改行を削除する 延床面積\r\n m2とか
        cur_sheet_df.columns = cur_sheet_df.columns.str.replace(
            r"[\r\n]+", "", regex=True
        ).str.strip()

        return cur_sheet_df

    def get_entity_from_sheet(
        self,
        *,
        input_file: FileStorage,
        sheet_name: str,
        request_dict: dict[str, any],
        validator: FileValidation,
    ):
        """シート毎データ処理

        Args:
            file_path (str): ファイル名
            sheet_name (str): シート名
            corporate_df (pd.DataFrame): _description_

        Returns:
            pd.DataFrame: df共通処理
        """
        # Requestから組織ID取得
        org_id = self.org_id
        user_id = self.user_id

        # Requestから同意書と会社名取得
        agreement_category = request_dict.get("agreement_category", None)
        corp_number = request_dict.get("corporate_number", None)

        # シート内容格納用DF
        cur_sheet_df = pd.DataFrame()
        if sheet_name == vis_constants.BuildingSheetName.AGGREMENT_DOC.value:
            # 情報シート読込
            cur_sheet_df = pd.read_excel(input_file, sheet_name=sheet_name)
            # 会社名取得
            self.company_name = cur_sheet_df.iloc[23, 3]

        if sheet_name == vis_constants.BuildingSheetName.ATTACHMENT.value:
            # 情報シート以外シート読込
            cur_sheet_df = pd.read_excel(
                input_file,
                sheet_name=sheet_name,
                skiprows=2,
                index_col=0,  # A列目は空のため、Unnamed: 0対応
                dtype=str,
            )
            # 生df加工
            cur_sheet_df = self.makeup_df(cur_sheet_df)

            # 日本語名：英語名マッピング
            sheet_cfg = vis_constants.building_sheet_mapping[sheet_name]
            column_mapping = sheet_cfg["column_mapping"]

            # 必要な列だけ抽出して英語名にリネーム
            cur_sheet_df = cur_sheet_df.rename(columns=column_mapping)
            cur_sheet_df.columns = cur_sheet_df.columns.str.lower()
            # NaN（None 含む）の行を削除
            cur_sheet_df = cur_sheet_df.dropna(subset=["location_identifier_code"])

            cur_sheet_df.to_csv(f"building.csv", index=False)
            for building_sheet_row in cur_sheet_df.itertuples():
                # location_identifier_code = str(
                #     int(building_sheet_row.location_identifier_code)) \
                #     if building_sheet_row.location_identifier_code.is_integer() else str(building_sheet_row.location_identifier_code)
                building_id = corp_number + building_sheet_row.location_identifier_code
                building_info = {
                    # 主キー
                    # "corp_number": corp_number,
                    # "agreement_category": agreement_category,
                    # "org_id": org_id,
                    # "building_id": building_id,
                    # 拠点情報
                    "location_identifier_code": building_sheet_row.location_identifier_code,
                    "location_identifier_name": building_sheet_row.location_identifier_name,
                    "building_address_prefecture": building_sheet_row.building_address_prefecture,
                    "building_address_city": building_sheet_row.building_address_city,
                    "supply_point_number": building_sheet_row.supply_point_number,
                    "ep_office_code": building_sheet_row.ep_office_code,
                    "ep_customer_number": building_sheet_row.ep_customer_number,
                }

                # 建物マスタ更新
                mbuilding_entity = (
                    self.session.query(MBuilding)
                    .filter_by(
                        corporate_number=corp_number,
                        agreement_category=agreement_category,
                        org_id=org_id,
                        building_id=building_id,
                    )
                    .first()
                )
                if not mbuilding_entity:
                    mbuilding_entity = MBuilding(
                        corporate_number=corp_number,
                        agreement_category=agreement_category,
                        org_id=org_id,
                        building_id=building_id,
                        created_by=user_id,
                    )
                    self.session.add(mbuilding_entity)
                # else:
                #     mbuilding_entity.updated_by = user_id

                set_target_entity(mbuilding_entity, building_info)
