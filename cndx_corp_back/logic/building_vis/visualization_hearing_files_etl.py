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
from sqlalchemy import inspect, text
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common import constants_colums, constants_values
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.db_base_handler import BaseRepository
from cndx_corp_back.common.decorators import jwt_user_context_db, log_time, service
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
    normalize_blank,
    safe,
    safe_float,
    set_target_entity,
    split_code_name,
)
from cndx_corp_back.logic.building_vis.master_loader import MasterLoader
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent


class HearingInputFileParser:
    @jwt_user_context_db(refresh=False)
    # @log_time
    def __init__(
        self,
        *,
        input_file: FileStorage,
        logger: CorpLogger,
        session: scoped_session,
        org_id: str,
        user_id: str,
        request_dict: dict[str, any],
        user_context=None,
    ) -> None:

        self.input_file: FileStorage = input_file

        self.error_list: list[str] = []
        self.logger = logger
        self.session = session
        self.org_id = user_context.get("org_id")
        self.user_id = user_id
        self.request_dict = request_dict

        # 新規作成対象
        self.base_hearing_entity = TKashikaBusinessHearingData()
        self.hearing_entity_list = list[TKashikaBusinessHearingData]()
        self.fiscal_years = list[str]()
        self.tbuilding_list = list[TBuildingInfo]()
        self.year_building_dict: dict[str, list[TBuildingInfo]] = {}
        self.tcommon_vis_list = list[TEnergyStorageCommonForVisualization]()
        self.t_month_building_energy_list = list[TMonthlyBuildingEnergyAggregation]()
        self.t_month_corp_energy_list = list[TMonthlyCorporateEnergyAggregation]()
        self.t_year_building_energy_list = list[TAnnualBuildingEnergyAggregation]()
        self.t_year_corp_energy_list = list[TAnnualCorporateEnergyAggregation]()
        self.mbid_dict: dict[str, str] = {}

        self.company_entity = MCorporateDetailsInfo()
        self.cnapp_entity = TCnApplicationInfo()
        self.cnapp_entity_list = list[TCnApplicationInfo]()

        master_loader: MasterLoader = MasterLoader(self.session)
        self.nfcmst = master_loader.get_nfcmst()
        self.ccimst = master_loader.get_ccimst()
        self.bmmst = master_loader.get_bmmst()
        self.wdimst = master_loader.get_wdimst()
        self.hsmst = master_loader.get_hsmst()
        self.hsmst_daitai = self.hsmst[(self.hsmst["HEAT_SUPPLIER_CD"] == "H0999")]

        # 都道府県情報動的に指定する列名
        col_names = self.ccimst["EN_CODE_NAME"].str.upper().to_list()

        # 天気情報取り出す
        df_wdimst = self.wdimst[["TARGET_YEAR", "TARGET_MONTH"] + col_names]

        mapping = dict(
            zip(self.ccimst["EN_CODE_NAME"].str.upper(), self.ccimst["CODE"])
        )
        # 英字名から県コードへ変換
        df_wdimst = df_wdimst.rename(columns=mapping)

        # 重複名前の列削除
        dup_cols = df_wdimst.columns[df_wdimst.columns.duplicated()].unique()
        df_wdimst = df_wdimst.drop(columns=dup_cols)

        self.df_wdimst = df_wdimst
        self.update_bid_dict = {}

    # @log_time
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

    # @log_time
    def file_data_process_main(self, input_file: FileStorage):

        # エネルギーマッピングをコードマスタから取得
        energy_dict: dict[str, MCorpCodeInfo] = self._get_energy_mapping_str()
        deno_dict: dict[str, MCorpCodeInfo] = self._get_deno_mapping_str()
        pref_dict: dict[str, MCorpCodeInfo] = self._get_pref_mapping_str()

        weather_df = pd.read_sql(
            "SELECT * FROM db_corp.m_weather_data_info", self.session.connection()
        )
        weather_dict = {
            (row["target_year"], row["target_month"]): row.to_dict()
            for _, row in weather_df.iterrows()
        }

        # 処理対象シート名取得
        parse_sheet_names = [
            item["name"] for item in vis_constants.HEARING_SHEET_NAME_LIST
        ]

        # 処理対象シート名取得
        input_file_df = pd.ExcelFile(self.input_file)

        target_sheet_names = [
            sheet_name
            for sheet_name in (input_file_df.sheet_names)
            if sheet_name in parse_sheet_names
        ]

        # 年度取得
        # 証書・クレジット
        credit_sheet_df = pd.read_excel(
            input_file, sheet_name=vis_constants.SheetName.CREDITS_INFO.value, header=2
        )
        start_col = 6

        # データが入っている最後の列まで
        end_col = credit_sheet_df.columns.get_loc(
            credit_sheet_df.dropna(axis=1, how="all").columns[-1]
        )

        credit_sheet_df = credit_sheet_df.iloc[:, start_col : end_col - 1]
        credit_sheet_df.columns = [
            (
                col.strftime("%Y年%m月")
                if isinstance(col, (datetime, pd.Timestamp))
                else str(col)
            )
            for col in credit_sheet_df.columns
        ]

        self.fiscal_years: list[str] = _extract_fiscal_years_by_12months(
            credit_sheet_df.columns
        )

        for sheet_name in target_sheet_names:
            # DataFrame加工処理
            self.get_entity_from_sheet(
                input_file=input_file,
                sheet_name=sheet_name,
                request_dict=self.request_dict,
                energy_dict=energy_dict,
                deno_dict=deno_dict,
                pref_dict=pref_dict,
                weather_dict=weather_dict,
            )

        # 登録対象テーブルかぶっているため　コメントアウト
        # update_targets = []
        # insert_hearing_targets = []
        # for hearing_entity in self.hearing_entity_list:
        #     existing = self.session.query(TKashikaBusinessHearingData).filter_by(
        #         corp_number=hearing_entity.corp_number,
        #         agreement_category=hearing_entity.agreement_category,
        #         org_id=hearing_entity.org_id,
        #         building_id=hearing_entity.building_id,
        #         target_year_month=hearing_entity.target_year_month,
        #         data_category='1',
        #     ).first()

        #     if existing:

        #         # 全カラムをコピー（PKやIDなど除く場合は if 文追加）
        #         for column in TKashikaBusinessHearingData.__table__.columns:
        #             attr = column.name
        #             if attr not in ['created_at', 'created_by']:  # ←更新しない項目を除外
        #                 setattr(existing, attr, getattr(hearing_entity, attr))
        #         existing.updated_by = self.user_id
        #         update_targets.append(existing)
        #     else:
        #         # 登録対象
        #         hearing_entity.created_by = self.user_id
        #         insert_hearing_targets.append(hearing_entity)

        # 他社業種設定
        for cnapp in self.cnapp_entity_list:
            if cnapp.updated_by:
                company_industry_minor_code = cnapp.industry_class_detail_code
                company_benchmark_industry = cnapp.energy_benchmark_target_industry
                year_building_list = self.year_building_dict.get(cnapp.fiscal_year, [])
                bmmst_sub = self.bmmst[
                    (
                        self.bmmst["industry_class_detail_code"]
                        == company_industry_minor_code
                    )
                    & (self.bmmst["pulldown_code"] == company_benchmark_industry)
                ]
                if not bmmst_sub.empty and any(
                    b.gross_floor_area is not None for b in year_building_list
                ):
                    self._set_competitor_industry_co2_avg(
                        bmmst_sub=bmmst_sub,
                        cnapp_entity=cnapp,
                        year_building_list=year_building_list,
                    )

        # if len(self.hearing_entity_list) > 0:
        # self.session.add_all(insert_hearing_targets)
        self.session.add_all(self.tbuilding_list)
        self.session.add_all(self.tcommon_vis_list)
        self.session.add_all(self.t_month_building_energy_list)
        self.session.add_all(self.t_month_corp_energy_list)
        self.session.add_all(self.t_year_corp_energy_list)
        self.session.add_all(self.t_year_building_energy_list)

        # for hearing_entity in self.hearing_entity_list:
        #     self.session.merge(hearing_entity)
        self.session.commit()

        file_upload = FileTransferComponent()

        # フォルダ構成名取得
        target_path_dict = {
            "put_sub_path": "input_excel_files",
            "org_type": "vis",
            "file_type": "hearing_data",
            "corporate_number": self.request_dict.get("corporate_number"),
            "user_id": self.user_id,
            "upload_time": datetime.now().strftime("%Y%m%d%H%M%S"),
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
        energy_file_entity.file_type = "3"
        energy_file_entity.created_by = self.user_id

        self.session.add(energy_file_entity)
        self.session.commit()

        return

    # @log_time
    def set_corporate_info(
        self, *, cur_sheet_df: pd.DataFrame, request_dict: dict, org_id: str
    ) -> None:
        """企業関連情報設定

        Args:
            cur_sheet_df (pd.DataFrame): _description_
            session (scoped_session): _description_
            agreement_category (str): _description_
            org_id (str): _description_

        Returns:
            pd.DataFrame: _description_
        """
        # Requestから同意書と会社名取得
        agreement_category = request_dict.get("agreement_category", None)
        company_name = request_dict.get("company_name", None)
        corporate_number = request_dict.get("corporate_number", None)
        target_year = request_dict.get("target_year", None)

        # 1列3列を 項目：値の辞書にする
        info_dict = dict(zip(cur_sheet_df[1], cur_sheet_df[3]))

        company_sheet_info = vis_constants.HEARING_ITEM_NAMES.get(
            vis_constants.SheetName.COMPANY_INFO.value
        )

        # ヒアリングEntityデータ設定
        hearing_entity = self.base_hearing_entity

        # 企業名を取得してinput_supplier_nameとして使用
        self.ghg_system_company_name = info_dict[
            company_sheet_info.ghg_system_company_name
        ]
        self.hearing_company_name = info_dict[company_sheet_info.company_name]

        hearing_company_info = {
            "ghg_system_company_name": self.ghg_system_company_name,
            "company_industry_class_major_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_major_name]
            )[0],
            "company_industry_class_major_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_major_name]
            )[1],
            "company_industry_class_middle_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_middle_name]
            )[0],
            "company_industry_class_middle_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_middle_name]
            )[1],
            "company_industry_class_minor_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_minor_name]
            )[0],
            "company_industry_class_minor_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_minor_name]
            )[1],
            "company_industry_class_detail_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_detail_name]
            )[0],
            "company_industry_class_detail_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_detail_name]
            )[1],
            "company_energy_benchmark_target_industry": split_code_name(
                info_dict[company_sheet_info.company_energy_benchmark_target_industry]
            )[0],
            "company_energy_benchmark_indicator": info_dict[
                company_sheet_info.company_energy_benchmark_indicator
            ],
            "company_energy_benchmark_year": cur_sheet_df.at[10, 2][
                :4
            ],  # 年だけ抽出（例：'2025年' → '2025'）
            "input_supplier_name": self.hearing_company_name,  # 企業名をinput_supplier_nameに設定
        }

        set_target_entity(hearing_entity, hearing_company_info)

        # 拠点情報シートのデータを取得
        location_sheet_info = vis_constants.HEARING_ITEM_NAMES.get(
            vis_constants.SheetName.LOCATION_INFO.value
        )
        if location_sheet_info:
            # 拠点情報シートからデータを取得
            self.location_data = {}
            for excel_col, entity_field in location_sheet_info[
                "column_mapping"
            ].items():
                if excel_col in cur_sheet_df.columns:
                    self.location_data[entity_field] = (
                        cur_sheet_df[excel_col].iloc[0]
                        if len(cur_sheet_df) > 0
                        else None
                    )
        else:
            self.location_data = {}

        # 企業情報をtcommon_vis_listの各エンティティに設定
        self.tcommon_vis_company_info = {
            "company_industry_class_major_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_major_name]
            )[0],
            "company_industry_class_major_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_major_name]
            )[1],
            "company_industry_class_middle_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_middle_name]
            )[0],
            "company_industry_class_middle_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_middle_name]
            )[1],
            "company_industry_class_minor_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_minor_name]
            )[0],
            "company_industry_class_minor_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_minor_name]
            )[1],
            "company_industry_class_detail_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_detail_name]
            )[0],
            "company_industry_class_detail_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_detail_name]
            )[1],
            "company_energy_benchmark_target_industry": split_code_name(
                info_dict[company_sheet_info.company_energy_benchmark_target_industry]
            )[0],
            "company_energy_benchmark_indicator": info_dict[
                company_sheet_info.company_energy_benchmark_indicator
            ],
            "company_energy_benchmark_year": cur_sheet_df.at[10, 2][:4],
        }

        corp_base_entity = (
            self.session.query(MCorporateBasic)
            .filter(
                MCorporateBasic.corporate_number == corporate_number,
                MCorporateBasic.delete_flg != True,
            )
            .first()
        )
        # MCorporateBasicから企業名を取得
        self.corp_base_company_name = (
            corp_base_entity.company_name if corp_base_entity else None
        )
        self.address_prefecture = corp_base_entity.company_address_prefecture
        self.address_city = corp_base_entity.company_address_city

        # Mbuildingから拠点情報を取得
        # building_entity = (
        #     self.session.query(MBuilding)
        #     .filter(
        #         MBuilding.corporate_number == corporate_number,
        #         MBuilding.building_id == self.base_hearing_entity.building_id,
        #         MBuilding.delete_flg != True
        #     )
        #     .first()
        # )
        # self.building_address_prefecture = building_entity.building_address_prefecture if building_entity else None
        # self.building_address_city = building_entity.building_address_city if building_entity else None

        update_company_info = {
            "ghg_system_company_name": info_dict[
                company_sheet_info.ghg_system_company_name
            ],
            "industry_class_major_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_major_name]
            )[0],
            "industry_class_major_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_major_name]
            )[1],
            "industry_class_middle_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_middle_name]
            )[0],
            "industry_class_middle_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_middle_name]
            )[1],
            "industry_class_minor_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_minor_name]
            )[0],
            "industry_class_minor_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_minor_name]
            )[1],
            "industry_class_detail_code": split_code_name(
                info_dict[company_sheet_info.company_industry_class_detail_name]
            )[0],
            "industry_class_detail_name": split_code_name(
                info_dict[company_sheet_info.company_industry_class_detail_name]
            )[1],
            "energy_benchmark_target_industry": split_code_name(
                info_dict[company_sheet_info.company_energy_benchmark_target_industry]
            )[0],
            "energy_benchmark_indicator": info_dict[
                company_sheet_info.company_energy_benchmark_indicator
            ],
            "energy_benchmark_year": cur_sheet_df.at[10, 2][
                :4
            ],  # 年だけ抽出（例：'2025年' → '2025'）
            "address_prefecture": self.address_prefecture,
            "address_city": self.address_city,
            "entry_draft_flag": "0",
            "company_name": self.corp_base_company_name,
        }

        # 企業詳細情報更新
        exit_company_entity = (
            self.session.query(MCorporateDetailsInfo)
            .filter_by(
                corporate_number=corporate_number,
                agreement_category=agreement_category,
                # org_id=org_id,
            )
            .first()
        )

        set_target_entity(exit_company_entity, update_company_info)
        exit_company_entity.updated_by = self.user_id

        for target_year in self.fiscal_years:
            # CN実施更新
            cnapp_entity = (
                self.session.query(TCnApplicationInfo)
                .filter_by(
                    corporate_number=corporate_number,
                    agreement_category=agreement_category,
                    # org_id=org_id,
                    fiscal_year=str(target_year),
                    registration_seq=0,
                )
                .first()
            )

            if not cnapp_entity:
                cnapp_entity = TCnApplicationInfo(
                    corporate_number=corporate_number,
                    agreement_category=agreement_category,
                    org_id=org_id,
                    fiscal_year=str(target_year),
                    registration_seq=0,
                )
                self.session.add(cnapp_entity)
                cnapp_entity.created_by = self.user_id
            else:
                cnapp_entity.updated_by = self.user_id

            set_target_entity(cnapp_entity, update_company_info)
            benchmark_year = cnapp_entity.energy_benchmark_year
            if cnapp_entity.fiscal_year != str(benchmark_year):
                cnapp_entity.energy_benchmark_indicator = None
                cnapp_entity.energy_benchmark_year = None
            self.cnapp_entity_list.append(cnapp_entity)

    # @log_time
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

    # @log_time
    def _get_pref_mapping_str(self) -> dict[str, MCorpCodeInfo]:
        # コードマスタからエネルギーカテゴリ取得
        pref_repo = BaseRepository(self.session, model=MCorpCodeInfo)
        filters = {"code_type": "PREF"}
        pref_rows = pref_repo.find_all(**(filters or {}))

        # エネルギー名: record 取得
        pref_dict: dict[str, MCorpCodeInfo] = {
            pref_row.code: pref_row for pref_row in pref_rows
        }
        return pref_dict

    # @log_time
    def _get_deno_mapping_str(self) -> dict[str, MCorpCodeInfo]:
        # コードマスタからエネルギーカテゴリ取得
        code_repo = BaseRepository(self.session, model=MCorpCodeInfo)
        filters = {"code_type": "ENERGY_DENOMINATOR"}
        energy_denominator_rows = code_repo.find_all(**(filters or {}))

        # エネルギー名: record 取得
        energy_denominator_dict: dict[str, MCorpCodeInfo] = {
            deno_row.jp_code_name: deno_row for deno_row in energy_denominator_rows
        }
        return energy_denominator_dict

    # @log_time
    def _makeup_df(self, cur_sheet_df: pd.DataFrame) -> pd.DataFrame:

        cur_sheet_df = cur_sheet_df.applymap(normalize_blank)

        def convert_excel_serial_to_ym(val):
            """
            Excel日付シリアル値を 'YYYY年M月' に変換する。
            datetimeオブジェクト、数値、文字列日付、その他を適切に処理する。
            """
            try:
                # datetimeオブジェクトの場合
                if isinstance(val, datetime.datetime):
                    return f"{val.year}年{val.month}月"
                # 数値の場合（Excel日付シリアル値）
                elif isinstance(val, (int, float)):
                    # 数値が日付として有効かチェック（1900年以降、2100年以前）
                    if (
                        isinstance(val, int) and 1000 <= val <= 100000
                    ):  # 年月形式の可能性（例：202304）
                        # YYYYMM形式のintの場合
                        if len(str(val)) == 6:  # YYYYMM形式
                            year = val // 100
                            month = val % 100
                            if 1 <= month <= 12 and 1900 <= year <= 2100:
                                return f"{year}年{month}月"
                    # Excel日付シリアル値として処理
                    try:
                        date = pd.to_datetime(val, unit="d", origin="1899-12-30")
                        return f"{date.year}年{date.month}月"
                    except:
                        # Excel日付シリアル値として処理できない場合は、pandasの日付変換を試す
                        try:
                            date = pd.to_datetime(val, origin="1899-12-30", unit="D")
                            return f"{date.year}年{date.month}月"
                        except:
                            return str(val)
                # 文字列の場合
                elif isinstance(val, str):
                    # 既に年月形式の場合
                    if "年" in val and "月" in val:
                        return val  # 既に年月形式の場合はそのまま返す
                    # 日付文字列の場合（例："2023-04-01 00:00:00"）
                    try:
                        date = pd.to_datetime(val)
                        return f"{date.year}年{date.month}月"
                    except:
                        return val  # 日付として解析できない場合はそのまま返す
                # その他の場合は文字列として返す
                else:
                    return str(val)
            except Exception as e:
                return str(val)

        # ======== ここで先に変換 =========
        converted_columns = []
        for i, col in enumerate(cur_sheet_df.columns):
            converted = convert_excel_serial_to_ym(col)
            converted_columns.append(converted)
            # 変換が行われた場合または数値の場合はログ出力

        cur_sheet_df.columns = converted_columns

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

    def _get_benchmark_dict_bk(self, raw_df: pd.DataFrame):
        # --- ヘッダ部 ---
        benchmark_header_rows = raw_df.iloc[2:5, 20:40]

        benchmark_keys = benchmark_header_rows.iloc[0].tolist()  # ベンチマーク業種名
        benchmark_demons = benchmark_header_rows.iloc[1].tolist()  # ベンチマーク分母名
        benchmark_demon_units = benchmark_header_rows.iloc[
            2
        ].tolist()  # ベンチマーク単位名

        # --- データ部 ---
        # benchmark_data_rows = raw_df.iloc[5:, 20:40]

        # --- 格納用辞書 (業種ごとに複数分母対応) ---
        benchmark_dict = defaultdict(list)

        for col_idx, (industry, demon, unit) in enumerate(
            zip(benchmark_keys, benchmark_demons, benchmark_demon_units)
        ):
            # 列データを取得（空欄を除外）
            # col_values = [v for v in benchmark_data_rows.iloc[:, col_idx].tolist() if pd.notna(v)]

            # 1業種内に複数の分母群を格納
            benchmark_dict[industry].append(
                {
                    "denominator": demon,
                    "unit": unit,
                    # "values": col_values
                }
            )

        # defaultdict → dict に変換
        benchmark_dict = dict(benchmark_dict)

        return benchmark_dict

    def _get_update_hearing_location_entity(self, building_sheet_row: pd.Series):

        return {
            # お客さま情報
            "supply_point_number": building_sheet_row.supply_point_number,
            "ep_office_code": building_sheet_row.ep_office_code,
            "ep_customer_number": building_sheet_row.ep_customer_number,
            "gross_floor_area": building_sheet_row.gross_floor_area,
            "location_identifier_code": building_sheet_row.location_identifier_code,
            "location_identifier_name": building_sheet_row.location_identifier_name,
            # 産業分類
            "building_industry_class_major_code": split_code_name(
                building_sheet_row.building_industry_class_major_name
            )[0],
            "building_industry_class_major_name": split_code_name(
                building_sheet_row.building_industry_class_major_name
            )[1],
            "building_industry_class_middle_code": split_code_name(
                building_sheet_row.building_industry_class_middle_name
            )[0],
            "building_industry_class_middle_name": split_code_name(
                building_sheet_row.building_industry_class_middle_name
            )[1],
            "building_industry_class_minor_code": split_code_name(
                building_sheet_row.building_industry_class_minor_name
            )[0],
            "building_industry_class_minor_name": split_code_name(
                building_sheet_row.building_industry_class_minor_name
            )[1],
            "building_industry_class_detail_code": split_code_name(
                building_sheet_row.building_industry_class_detail_name
            )[0],
            "building_industry_class_detail_name": split_code_name(
                building_sheet_row.building_industry_class_detail_name
            )[1],
            # 省エネ法ベンチマーク指標
            "building_energy_benchmark_target_industry": (
                split_code_name(
                    building_sheet_row.building_energy_benchmark_target_industry
                )[0]
                if building_sheet_row.building_energy_benchmark_target_industry
                else ""
            ),
            "building_energy_benchmark_indicator": (
                building_sheet_row.building_energy_benchmark_indicator
                if building_sheet_row.building_energy_benchmark_indicator
                else 0
            ),
            # KPI情報
            "kpi_target_energy_saving_rate": (
                building_sheet_row.kpi_target_energy_saving_rate
                if building_sheet_row.kpi_target_energy_saving_rate
                else None
            ),
            "kpi_target_electrification_rate": (
                building_sheet_row.kpi_target_electrification_rate
                if building_sheet_row.kpi_target_electrification_rate
                else None
            ),
            "kpi_target_energy_creation": (
                building_sheet_row.kpi_target_energy_creation
                if building_sheet_row.kpi_target_energy_creation
                else None
            ),
            "kpi_target_renewable_network_rate": (
                building_sheet_row.kpi_target_renewable_network_rate
                if building_sheet_row.kpi_target_renewable_network_rate
                else None
            ),
        }

    # @log_time
    def _get_updated_builiding_dict(self, building_sheet_row: pd.Series):
        return {
            "site_industry_class_major_code": split_code_name(
                building_sheet_row.building_industry_class_major_name
            )[0],
            "site_industry_class_major_name": split_code_name(
                building_sheet_row.building_industry_class_major_name
            )[1],
            "site_industry_class_middle_code": split_code_name(
                building_sheet_row.building_industry_class_middle_name
            )[0],
            "site_industry_class_middle_name": split_code_name(
                building_sheet_row.building_industry_class_middle_name
            )[1],
            "site_industry_class_minor_code": split_code_name(
                building_sheet_row.building_industry_class_minor_name
            )[0],
            "site_industry_class_minor_name": split_code_name(
                building_sheet_row.building_industry_class_minor_name
            )[1],
            "site_industry_class_detail_code": split_code_name(
                building_sheet_row.building_industry_class_detail_name
            )[0],
            "site_industry_class_detail_name": split_code_name(
                building_sheet_row.building_industry_class_detail_name
            )[1],
            "site_energy_benchmark_target_industry": (
                split_code_name(
                    building_sheet_row.building_energy_benchmark_target_industry
                )[0]
                if building_sheet_row.building_energy_benchmark_target_industry
                else ""
            ),
            "site_energy_benchmark_indicator": (
                building_sheet_row.building_energy_benchmark_indicator
                if building_sheet_row.building_energy_benchmark_indicator
                else 0
            ),
            "site_energy_benchmark_year": None,  # 後でenergy_benchmark_yearから設定される
            "industry_class_major_code": split_code_name(
                building_sheet_row.building_industry_class_major_name
            )[0],
            "industry_class_major_name": split_code_name(
                building_sheet_row.building_industry_class_major_name
            )[1],
            "industry_class_middle_code": split_code_name(
                building_sheet_row.building_industry_class_middle_name
            )[0],
            "industry_class_middle_name": split_code_name(
                building_sheet_row.building_industry_class_middle_name
            )[1],
            "industry_class_minor_code": split_code_name(
                building_sheet_row.building_industry_class_minor_name
            )[0],
            "industry_class_minor_name": split_code_name(
                building_sheet_row.building_industry_class_minor_name
            )[1],
            "industry_class_detail_code": split_code_name(
                building_sheet_row.building_industry_class_detail_name
            )[0],
            "industry_class_detail_name": split_code_name(
                building_sheet_row.building_industry_class_detail_name
            )[1],
            "energy_benchmark_target_industry": (
                split_code_name(
                    building_sheet_row.building_energy_benchmark_target_industry
                )[0]
                if building_sheet_row.building_energy_benchmark_target_industry
                else ""
            ),
            "energy_benchmark_indicator": (
                building_sheet_row.building_energy_benchmark_indicator
                if building_sheet_row.building_energy_benchmark_indicator
                else 0
            ),
            # "supply_point_number": building_sheet_row.supply_point_number,
            "benchmark_denom": (
                building_sheet_row.benchmark_denom
                if building_sheet_row.benchmark_denom
                and building_sheet_row.benchmark_denom != "－"
                else None
            ),
            "benchmark_val": (
                building_sheet_row.benchmark_val
                if building_sheet_row.benchmark_val
                else None
            ),
        }

    def _get_company_info_for_building(
        self, building_id: str, input_file: FileStorage
    ) -> dict:
        """建物IDで紐づく拠点情報の産業分類とベンチマーク情報を取得

        Args:
            building_id (str): 建物ID
            input_file (FileStorage): エクセルファイル

        Returns:
            dict: 拠点情報辞書（産業分類とベンチマーク情報）
        """
        try:
            # 拠点情報シートから直接データを取得
            cur_sheet_df = pd.read_excel(
                input_file,
                sheet_name=vis_constants.SheetName.LOCATION_INFO.value,
                skiprows=5,
                header=None,
            )

            # ヘッダーを適用（拠点情報シートの処理と同じ）
            raw_df = pd.read_excel(
                input_file,
                sheet_name=vis_constants.SheetName.LOCATION_INFO.value,
                header=None,
                nrows=5,
            )
            headers = raw_df.iloc[3].copy()
            headers.iloc[9] = raw_df.iloc[4, 9]  # J列 大分類
            headers.iloc[10] = raw_df.iloc[4, 10]  # K列 中
            headers.iloc[11] = raw_df.iloc[4, 11]  # L列 小
            headers.iloc[12] = raw_df.iloc[4, 12]  # M列 細
            headers.iloc[13] = raw_df.iloc[1, 13]  # N列 原単位分母単位
            headers.iloc[14] = raw_df.iloc[1, 14]  # O列 原単位分母数値
            headers.iloc[18] = raw_df.iloc[2, 18]  # S列 ベンチマック業種

            cur_sheet_df.columns = headers
            cur_sheet_df = self._makeup_df(cur_sheet_df)
            cur_sheet_df = cur_sheet_df.rename(
                columns=vis_constants.sheet_mapping[
                    vis_constants.SheetName.LOCATION_INFO.value
                ]["column_mapping"]
            )
            cur_sheet_df.columns = cur_sheet_df.columns.str.lower()

            # 物件番号データなし、かつ物件番号が空、*(excel file上の最終行mark)のデータを除外する
            cur_sheet_df = cur_sheet_df[
                cur_sheet_df["location_identifier_code"].notna()
                & ~cur_sheet_df["location_identifier_code"]
                .astype(str)
                .str.strip()
                .isin(["", "*"])
            ]

            # 建物IDに該当する行を検索
            # building_idから法人番号部分を除去して拠点識別番号を取得
            # 例: "0000000000310tokyoA" -> "tokyoA"
            building_id_suffix = building_id[13:]  # 法人番号13桁を除去

            for _, row in cur_sheet_df.iterrows():
                if str(row["location_identifier_code"]) == building_id_suffix:

                    # 重複列名の問題を回避するため、ilocでアクセス
                    gross_floor_area_value = (
                        row.iloc[8] if len(row) > 8 else None
                    )  # 延床面積列
                    major_name_value = row.iloc[9] if len(row) > 9 else None  # 大分類列
                    middle_name_value = (
                        row.iloc[10] if len(row) > 10 else None
                    )  # 中分類列
                    minor_name_value = (
                        row.iloc[11] if len(row) > 11 else None
                    )  # 小分類列
                    detail_name_value = (
                        row.iloc[12] if len(row) > 12 else None
                    )  # 細分類列
                    benchmark_industry_value = (
                        row.iloc[18] if len(row) > 18 else None
                    )  # ベンチマーク業種列

                    # ベンチマーク年はT列（19列目）、5行目から取得
                    benchmark_year_value = None
                    try:
                        # 拠点情報シートの5行目T列（19列目）から年を取得
                        raw_df = pd.read_excel(
                            input_file,
                            sheet_name=vis_constants.SheetName.LOCATION_INFO.value,
                            header=None,
                            nrows=6,
                        )
                        if len(raw_df) > 4 and len(raw_df.columns) > 19:
                            year_str = str(
                                raw_df.at[4, 19]
                            )  # 5行目（0ベースで4）、T列（19列目）
                            benchmark_year_value = (
                                year_str[:4] if year_str and year_str != "nan" else None
                            )
                    except Exception as e:
                        self.logger.warning(f"ベンチマーク年取得エラー: {str(e)}")
                        benchmark_year_value = None

                    return {
                        "site_gross_floor_area": (
                            gross_floor_area_value
                            if not pd.isna(gross_floor_area_value)
                            else None
                        ),
                        # 拠点産業分類コード
                        "site_industry_class_major_code": split_code_name(
                            major_name_value
                        )[0],
                        "site_industry_class_middle_code": split_code_name(
                            middle_name_value
                        )[0],
                        "site_industry_class_minor_code": split_code_name(
                            minor_name_value
                        )[0],
                        "site_industry_class_detail_code": split_code_name(
                            detail_name_value
                        )[0],
                        # 拠点産業分類名称
                        "site_industry_class_major_name": split_code_name(
                            major_name_value
                        )[1],
                        "site_industry_class_middle_name": split_code_name(
                            middle_name_value
                        )[1],
                        "site_industry_class_minor_name": split_code_name(
                            minor_name_value
                        )[1],
                        "site_industry_class_detail_name": split_code_name(
                            detail_name_value
                        )[1],
                        # 拠点ベンチマーク情報
                        "site_energy_benchmark_target_industry": split_code_name(
                            benchmark_industry_value
                        )[0],
                        "site_energy_benchmark_indicator": split_code_name(
                            benchmark_industry_value
                        )[1],
                        "site_energy_benchmark_year": benchmark_year_value,
                    }

            # 該当する建物IDが見つからない場合
            self.logger.warning(
                f"拠点情報が見つかりません - building_id: {building_id}"
            )
            return {}
        except Exception as e:
            self.logger.error(
                f"拠点情報取得エラー - building_id: {building_id}, error: {str(e)}"
            )
            return {}

    def _update_vis_common_entity_with_location_info(
        self,
        corp_number: str,
        agreement_category: str,
        org_id: str,
        building_id: str,
        building_sheet_row: pd.Series,
        building_energy_benchmark_year: str,
    ):
        """拠点情報の産業分類とベンチマーク情報をTEnergyStorageCommonForVisualizationに登録・更新

        Args:
            corp_number (str): 法人番号
            agreement_category (str): 同意書取得区分
            org_id (str): 組織ID
            building_id (str): 拠点ID
            building_sheet_row (pd.Series): 拠点情報シートの行データ
            building_energy_benchmark_year (str): ベンチマーク指標年度
        """
        try:

            # 拠点情報処理時にMBuildingから住所情報を取得
            current_building_entity = (
                self.session.query(MBuilding)
                .filter(
                    MBuilding.corporate_number == corp_number,
                    MBuilding.building_id == building_id,
                    MBuilding.delete_flg != True,
                )
                .first()
            )

            # 拠点情報の産業分類とベンチマーク情報を辞書で準備
            location_info_dict = {
                # 拠点産業分類コード
                "site_industry_class_major_code": split_code_name(
                    building_sheet_row.building_industry_class_major_name
                )[0],
                "site_industry_class_middle_code": split_code_name(
                    building_sheet_row.building_industry_class_middle_name
                )[0],
                "site_industry_class_minor_code": split_code_name(
                    building_sheet_row.building_industry_class_minor_name
                )[0],
                "site_industry_class_detail_code": split_code_name(
                    building_sheet_row.building_industry_class_detail_name
                )[0],
                # 拠点産業分類名称
                "site_industry_class_major_name": split_code_name(
                    building_sheet_row.building_industry_class_major_name
                )[1],
                "site_industry_class_middle_name": split_code_name(
                    building_sheet_row.building_industry_class_middle_name
                )[1],
                "site_industry_class_minor_name": split_code_name(
                    building_sheet_row.building_industry_class_minor_name
                )[1],
                "site_industry_class_detail_name": split_code_name(
                    building_sheet_row.building_industry_class_detail_name
                )[1],
                # 拠点ベンチマーク情報
                "site_energy_benchmark_target_industry": split_code_name(
                    building_sheet_row.building_energy_benchmark_target_industry
                )[0],
                "site_energy_benchmark_indicator": split_code_name(
                    building_sheet_row.building_energy_benchmark_target_industry
                )[1],
                "site_energy_benchmark_year": building_energy_benchmark_year,
                # 拠点基本情報
                "location_identifier_code": building_sheet_row.location_identifier_code,
                "location_identifier_name": building_sheet_row.location_identifier_name,
                "site_gross_floor_area": (
                    building_sheet_row.gross_floor_area
                    if not pd.isna(building_sheet_row.gross_floor_area)
                    else None
                ),
                "site_address_prefecture": (
                    current_building_entity.building_address_prefecture
                    if current_building_entity
                    else None
                ),
                "site_address_city": building_sheet_row.building_address_city,
                "building_name": building_sheet_row.location_identifier_name,
                # 供給地点特定番号
                "supply_point_number": building_sheet_row.supply_point_number,
            }

            # 該当拠点の既存レコードを取得
            existing_vis_common_entities = (
                self.session.query(TEnergyStorageCommonForVisualization)
                .filter_by(
                    corporate_number=corp_number,
                    agreement_category=agreement_category,
                    # org_id=org_id,
                    building_id=building_id,
                )
                .all()
            )

            if existing_vis_common_entities and len(existing_vis_common_entities) > 0:
                # 既存レコードを更新
                for vis_common_entity in existing_vis_common_entities:

                    # 拠点情報を更新
                    for field, value in location_info_dict.items():
                        if hasattr(vis_common_entity, field):
                            setattr(vis_common_entity, field, value)
                    vis_common_entity.updated_by = self.user_id
            else:
                pass
        except Exception as e:
            self.logger.error(
                f"拠点情報更新エラー - building_id: {building_id}, error: {str(e)}"
            )
            self.logger.error(traceback.format_exc())
            raise e

    def _set_competitor_industry_co2_avg(
        self,
        bmmst_sub: pd.DataFrame,
        tbuilding_entity: TBuildingInfo = None,
        cnapp_entity: TCnApplicationInfo = None,
        year_building_list=None,
    ):
        if not bmmst_sub.empty:
            if cnapp_entity:
                areas = [
                    b.gross_floor_area
                    for b in year_building_list
                    if b.gross_floor_area is not None
                ]
                gross_floor_area = sum(areas) / len(areas) if areas else 0
            else:
                gross_floor_area = tbuilding_entity.gross_floor_area
            if gross_floor_area >= 10000:
                bmmst_sub_1 = bmmst_sub[
                    (bmmst_sub["total_floor_area_flag"] == "1")
                    & (bmmst_sub["target_total_floor_area_max"] == 0)
                ]
            else:
                bmmst_sub_1 = bmmst_sub[
                    (bmmst_sub["total_floor_area_flag"] == "1")
                    & (bmmst_sub["target_total_floor_area_min"] <= gross_floor_area)
                    & (bmmst_sub["target_total_floor_area_max"] >= gross_floor_area)
                ]

            if cnapp_entity:
                if not bmmst_sub_1.empty:
                    cnapp_entity.competitor_industry_co2_avg = bmmst_sub_1[
                        "competitor_industry_co2_avg"
                    ].iloc[0]
                    cnapp_entity.energy_saving_denominator = bmmst_sub_1[
                        "energy_saving_denominator"
                    ].iloc[0]
                else:
                    cnapp_entity.competitor_industry_co2_avg = bmmst_sub[
                        "competitor_industry_co2_avg"
                    ].iloc[0]
                    cnapp_entity.energy_saving_denominator = bmmst_sub[
                        "energy_saving_denominator"
                    ].iloc[0]
            else:
                if not bmmst_sub_1.empty:
                    tbuilding_entity.competitor_industry_co2_avg = bmmst_sub_1[
                        "competitor_industry_co2_avg"
                    ].iloc[0]
                    tbuilding_entity.energy_saving_denominator = bmmst_sub_1[
                        "energy_saving_denominator"
                    ].iloc[0]
                else:
                    tbuilding_entity.competitor_industry_co2_avg = bmmst_sub[
                        "competitor_industry_co2_avg"
                    ].iloc[0]
                    tbuilding_entity.energy_saving_denominator = bmmst_sub[
                        "energy_saving_denominator"
                    ].iloc[0]

    # @log_time
    def _get_benchmark_dict(self, raw_df: pd.DataFrame, rows_df: pd.DataFrame):
        from collections import defaultdict

        import pandas as pd

        # --- ヘッダ部 ---
        benchmark_header_rows = raw_df.iloc[2:5, 20:40]

        benchmark_keys = benchmark_header_rows.iloc[0].tolist()  # ベンチマーク業種名
        benchmark_demons = benchmark_header_rows.iloc[1].tolist()  # ベンチマーク分母名
        benchmark_demon_units = benchmark_header_rows.iloc[
            2
        ].tolist()  # ベンチマーク単位名

        # --- データ部 (別DataFrame rows_dfを利用) ---
        benchmark_data_rows = rows_df.iloc[:, 20:40]

        # --- 格納用辞書 (業種ごとに複数分母対応) ---
        benchmark_dict = defaultdict(list)

        for col_idx, (industry, demon, unit) in enumerate(
            zip(benchmark_keys, benchmark_demons, benchmark_demon_units)
        ):
            # 対応列の値リストを取得（NaN除外）
            if col_idx < benchmark_data_rows.shape[1]:
                col_values = [
                    0 if pd.isna(v) else v
                    for v in benchmark_data_rows.iloc[:, col_idx].tolist()
                    if str(v).strip() != "*"
                ]
            else:
                col_values = []

            benchmark_dict[industry].append(
                {"denominator": demon, "unit": unit, "values": col_values}
            )

        return dict(benchmark_dict)

    # @log_time
    def _set_location_info(
        self,
        input_file: FileStorage,
        sheet_name: str,
        corp_number: str,
        agreement_category: str,
        org_id: str,
        deno_dict: dict[str, MCorpCodeInfo],
    ):
        """物件情報読み込み

        Args:
            input_file (FileStorage): _description_
            sheet_name (str): _description_
            agreement_category (str): _description_
            org_id (str): _description_
            deno_dict (dict[str, MCorpCodeInfo]): _description_
        """

        # 拠点情報ヘッダ部読み込み（先頭から5行まで）
        raw_df = pd.read_excel(input_file, sheet_name=sheet_name, header=None, nrows=5)

        # 4行名をベースにヘッダーを作成
        headers = raw_df.iloc[3].copy()

        # 列ごとに特別なヘッダーを適用
        headers.iloc[9] = raw_df.iloc[4, 9]  # J列 大分類
        headers.iloc[10] = raw_df.iloc[4, 10]  # K列 中
        headers.iloc[11] = raw_df.iloc[4, 11]  # L列 小
        headers.iloc[12] = raw_df.iloc[4, 12]  # M列 細
        headers.iloc[13] = raw_df.iloc[1, 13]  # N列 原単位分母単位
        headers.iloc[14] = raw_df.iloc[1, 14]  # O列 原単位分母数値
        headers.iloc[18] = raw_df.iloc[2, 18]  # S列 ベンチマック業種

        # 原単位分母年度（O列5行目先頭4文字）
        unit_denominator_year = raw_df.iloc[4, 14][:4]
        # 指標年度（T列5行目先頭4文字）
        building_energy_benchmark_year = raw_df.iloc[4, 19][:4]

        # 拠点情報実データ部読み込み（先頭5行飛ばし）
        cur_sheet_df = pd.read_excel(
            input_file, sheet_name=sheet_name, skiprows=5, header=None
        )

        # ベンチマック関連情報取得
        benchmark_dict = self._get_benchmark_dict(raw_df, cur_sheet_df)

        # ヘッダーを適用
        cur_sheet_df.columns = headers

        # 生df加工
        cur_sheet_df = self._makeup_df(cur_sheet_df)

        # 必要な列だけ抽出して英語名にリネーム
        cur_sheet_df = cur_sheet_df.rename(
            columns=vis_constants.sheet_mapping[sheet_name]["column_mapping"]
        )
        cur_sheet_df.columns = cur_sheet_df.columns.str.lower()

        # 物件番号データなし、かつ物件番号が空、*(excel file上の最終行mark)のデータを除外する
        cur_sheet_df = cur_sheet_df[
            cur_sheet_df["location_identifier_code"].notna()
            & ~cur_sheet_df["location_identifier_code"]
            .astype(str)
            .str.strip()
            .isin(["", "*"])
        ]
        cur_sheet_df["corp_number"] = corp_number
        # 拠点ループ

        for fiscal_year in self.fiscal_years:
            self.year_building_dict[fiscal_year] = []
        for building_sheet_row in cur_sheet_df.itertuples():
            # 拠点ID
            building_id = corp_number + building_sheet_row.location_identifier_code

            # 建物マスタ更新
            exit_mbuilding_entity = (
                self.session.query(MBuilding)
                .filter_by(
                    corporate_number=corp_number,
                    agreement_category=agreement_category,
                    # org_id=org_id, # 組織IDは固定でTEP
                    building_id=building_id,
                )
                .first()
            )

            # 建物情報更新内容辞書
            update_building_info = {
                "energy_benchmark_year": building_energy_benchmark_year,
                "unit_denominator_year": unit_denominator_year,
                "supply_point_number": exit_mbuilding_entity.supply_point_number,
                "entry_draft_flag": "0",
                **self._get_updated_builiding_dict(building_sheet_row),
            }
            # site_energy_benchmark_yearを設定
            update_building_info["site_energy_benchmark_year"] = (
                building_energy_benchmark_year
            )

            for fiscal_year in self.fiscal_years:
                fiscal_year = str(fiscal_year)
                # 建物情報取得
                tbuilding_entity_list = (
                    self.session.query(TBuildingInfo)
                    .filter_by(
                        corporate_number=corp_number,
                        agreement_category=agreement_category,
                        building_id=building_id,
                        registration_seq=0,
                        fiscal_year=fiscal_year,
                    )
                    .all()
                )

                # ---- 既存レコードがある場合 ----
                if tbuilding_entity_list:

                    for tbuilding_entity in tbuilding_entity_list:
                        # 建物情報更新
                        set_target_entity(tbuilding_entity, update_building_info)
                        tbuilding_entity.updated_by = self.user_id

                        builiding_detail_code = split_code_name(
                            building_sheet_row.building_industry_class_detail_name
                        )[0]
                        building_benchmark_code = (
                            split_code_name(
                                building_sheet_row.building_energy_benchmark_target_industry
                            )[0]
                            if building_sheet_row.building_energy_benchmark_target_industry
                            else ""
                        )

                        bmmst_sub = self.bmmst[
                            (
                                self.bmmst["industry_class_detail_code"]
                                == builiding_detail_code
                            )
                            & (self.bmmst["pulldown_code"] == building_benchmark_code)
                        ]
                        if not bmmst_sub.empty and tbuilding_entity.gross_floor_area:
                            self._set_competitor_industry_co2_avg(
                                bmmst_sub=bmmst_sub, tbuilding_entity=tbuilding_entity
                            )

                        # energy_benchmark_year の範囲チェック
                        energy_benchmark_year = tbuilding_entity.energy_benchmark_year
                        if (
                            energy_benchmark_year
                            and energy_benchmark_year != fiscal_year
                        ):
                            tbuilding_entity.energy_benchmark_year = None
                            tbuilding_entity.energy_benchmark_indicator = None

                        self.tbuilding_list.append(tbuilding_entity)
                        self.year_building_dict[fiscal_year].append(tbuilding_entity)

                    # 年度のリストに格納
                    # self.year_building_dict[fiscal_year] = updated_list
                    continue

                # ---- 既存レコードが無い場合、1件新規作成 ----
                tbuilding_entity = TBuildingInfo(
                    corporate_number=corp_number,
                    agreement_category=agreement_category,
                    org_id=org_id,
                    building_id=building_id,
                    registration_seq=0,
                    fiscal_year=fiscal_year,
                )
                set_target_entity(tbuilding_entity, update_building_info)
                tbuilding_entity.created_by = self.user_id

                energy_benchmark_year = tbuilding_entity.energy_benchmark_year
                if energy_benchmark_year and energy_benchmark_year != fiscal_year:
                    tbuilding_entity.energy_benchmark_year = None
                    tbuilding_entity.energy_benchmark_indicator = None

                self.tbuilding_list.append(tbuilding_entity)

                # 新規でもリストで入れる
                self.year_building_dict[fiscal_year] = [tbuilding_entity]

            if building_sheet_row.building_energy_benchmark_target_industry:
                building_energy_benchmark_target_industry = split_code_name(
                    building_sheet_row.building_energy_benchmark_target_industry
                )
                if (
                    building_energy_benchmark_target_industry
                    and len(building_energy_benchmark_target_industry) > 1
                ):
                    benchmark_target_industry = (
                        building_energy_benchmark_target_industry[1]
                        if building_sheet_row.building_energy_benchmark_target_industry
                        else ""
                    )
                    exit_mbuilding_entity.energy_benchmark_target_industry_code = (
                        building_energy_benchmark_target_industry[0]
                    )
                    exit_mbuilding_entity.energy_benchmark_target_industry = (
                        benchmark_target_industry
                    )

                    bench_industry_array = benchmark_target_industry.split("/")
                    if bench_industry_array and len(bench_industry_array) > 1:
                        bench_industry_name = bench_industry_array[0]
                        if bench_industry_name in (
                            "通常コンビニエンスストア",
                            "小型コンビニエンスストア",
                        ):
                            bench_industry_name = "コンビニエンスストア業"
                        elif bench_industry_name == "食料品スーパー業":
                            bench_industry_name == "食品スーパー業"
                        benchmark_item = benchmark_dict.get(bench_industry_name)

                        if benchmark_item:  # Noneや空リストの場合はスキップ
                            # building_index は現在処理中のビル（行）番号（例：0, 1, 2 ...）
                            for idx, item in enumerate(benchmark_item, start=1):
                                denominator = item.get("denominator")
                                unit = item.get("unit")
                                values = item.get("values", [])

                                # NaNや*を除外済みなので安全
                                # building_index に対応する値を取得（範囲外なら0）
                                val = (
                                    values[building_sheet_row.Index]
                                    if building_sheet_row.Index < len(values)
                                    else 0
                                )

                                # 分母名に対応するコードを取得
                                deno_kbn = getattr(
                                    deno_dict.get(denominator, None), "code"
                                )

                                # エンティティへセット
                                setattr(
                                    exit_mbuilding_entity,
                                    f"benchmark_denom_kbn_{idx}",
                                    deno_kbn,
                                )
                                setattr(
                                    exit_mbuilding_entity,
                                    f"benchmark_denom_{idx}",
                                    denominator,
                                )
                                setattr(
                                    exit_mbuilding_entity,
                                    f"benchmark_denom_unit_{idx}",
                                    unit,
                                )
                                setattr(
                                    exit_mbuilding_entity, f"benchmark_val_{idx}", val
                                )

                                # 業種情報を設定
                                exit_mbuilding_entity.benchmark_indicator_industry = (
                                    bench_industry_name
                                )
                                exit_mbuilding_entity.benchmark_indicator_industry_kbn = vis_constants.benchmark_industry_dict.get(
                                    bench_industry_array[0], "NULL"
                                )
                            # for idx, (val, unit) in enumerate(benchmark_item, start=1):
                            #     deno_kbn = getattr(deno_dict.get(val, None), "code", "DEFAULT_CODE")

                            #     setattr(exit_mbuilding_entity, f"benchmark_denom_kbn_{idx}", deno_kbn)
                            #     setattr(exit_mbuilding_entity, f"benchmark_denom_{idx}", val)
                            #     setattr(exit_mbuilding_entity, f"benchmark_denom_unit_{idx}", unit)

                            #     setattr(exit_mbuilding_entity, f"benchmark_val_{idx}", unit)

                            #     exit_mbuilding_entity.benchmark_indicator_industry = bench_industry_array[0]
                            #     exit_mbuilding_entity.benchmark_indicator_industry_kbn = vis_constants.benchmark_industry_dict[bench_industry_array[0]]

            # KPI情報更新
            update_mbuilding_dict = {
                "kpi_target_energy_saving_rate": (
                    building_sheet_row.kpi_target_energy_saving_rate
                    if building_sheet_row.kpi_target_energy_saving_rate
                    else None
                ),
                "kpi_target_electrification_rate": (
                    building_sheet_row.kpi_target_electrification_rate
                    if building_sheet_row.kpi_target_electrification_rate
                    else None
                ),
                "kpi_target_energy_creation": (
                    building_sheet_row.kpi_target_energy_creation
                    if building_sheet_row.kpi_target_energy_creation
                    else None
                ),
                "kpi_target_renewable_network_rate": (
                    building_sheet_row.kpi_target_renewable_network_rate
                    if building_sheet_row.kpi_target_renewable_network_rate
                    else None
                ),
                "energy_benchmark_indicator": (
                    building_sheet_row.building_energy_benchmark_indicator
                    if building_sheet_row.building_energy_benchmark_indicator
                    else 0
                ),
                **update_building_info,
            }
            # update_building_info["supply_point_number"] = exit_mbuilding_entity.supply_point_number
            # update_mbuilding_dict["supply_point_number"] = exit_mbuilding_entity.supply_point_number

            if deno_dict.get(building_sheet_row.benchmark_denom, None):
                benchmark_denom_kbn = getattr(
                    deno_dict.get(building_sheet_row.benchmark_denom, None), "code"
                )
                exit_mbuilding_entity.benchmark_denom_kbn = benchmark_denom_kbn
            set_target_entity(exit_mbuilding_entity, update_mbuilding_dict)
            exit_mbuilding_entity.updated_by = self.user_id
            self.mbid_dict[building_id] = {
                "building_address_prefecture": exit_mbuilding_entity.building_address_prefecture,
                "building_address_city": exit_mbuilding_entity.building_address_city,
                "building_name": exit_mbuilding_entity.building_name,
                "location_identifier_name": exit_mbuilding_entity.location_identifier_name,
            }

            self.update_bid_dict[building_id] = update_building_info
            # 拠点情報はupdate_bid_dictに保存し、実際のTEnergyStorageCommonForVisualizationテーブルの更新は
            # 証書・クレジットシートの処理で行う（energy_codeとyear_monthを指定して特定のレコードのみ更新）

    # ======================================================
    # 拠点情報更新処理（共通化）
    # ======================================================
    from sqlalchemy import inspect

    def apply_site_info_to_common_vis(
        self, records: list[TEnergyStorageCommonForVisualization]
    ):
        """
        可視化共通テーブルのレコードに対して、準備済みの企業情報・拠点情報・
        ベンチマーク期間チェックを最新の状態に一括適用する。
        """
        for record in records:
            b_id = record.building_id

            # 企業情報の反映
            record.company_name = self.corp_base_company_name
            record.company_address_prefecture = self.address_prefecture
            record.company_address_city = self.address_city

            for field, value in self.tcommon_vis_company_info.items():
                if hasattr(record, field):
                    # 計算に関わるフィールドは誤更新防止のためスキップ
                    if field in [
                        "co2_adjusted_emissions_monthly",
                        "energy_usage_monthly",
                        "input_supplier_name",
                    ]:
                        continue
                    setattr(record, field, value)

            # 拠点情報の反映（住所・建物名等）
            if b_id in self.mbid_dict:
                record.site_address_prefecture = self.mbid_dict[b_id].get(
                    "building_address_prefecture"
                )
                record.site_address_city = self.mbid_dict[b_id].get(
                    "building_address_city"
                )
                record.building_name = self.mbid_dict[b_id].get(
                    "location_identifier_name"
                )
                record.location_identifier_name = self.mbid_dict[b_id].get(
                    "location_identifier_name"
                )
                val_code = self.mbid_dict[b_id].get("location_identifier_code")
                if val_code:
                    record.location_identifier_code = val_code

            # 追加の拠点属性反映（update_bid_dict）
            if b_id in self.update_bid_dict:
                for field, value in self.update_bid_dict[b_id].items():
                    if hasattr(record, field):
                        if field in [
                            "co2_adjusted_emissions_monthly",
                            "energy_usage_monthly",
                            "location_identifier_code",
                        ]:
                            continue
                        # または、値が None でない場合のみ更新する
                        if value is not None:
                            setattr(record, field, value)

            # ベンチマーク範囲チェック
            year_month = record.year_month
            if not year_month:
                continue

            for prefix in ["company", "site"]:
                bench_year_attr = f"{prefix}_energy_benchmark_year"
                bench_ind_attr = f"{prefix}_energy_benchmark_indicator"
                bench_year = getattr(record, bench_year_attr, None)
                if bench_year:
                    try:
                        start_ym = int(f"{bench_year}04")
                        end_ym = int(f"{int(bench_year) + 1}03")
                        if not (start_ym <= int(year_month) <= end_ym):
                            setattr(record, bench_ind_attr, None)
                            setattr(record, bench_year_attr, None)
                    except (ValueError, TypeError):
                        pass

    # @log_time
    def get_entity_from_sheet(
        self,
        *,
        input_file: FileStorage,
        sheet_name: str,
        request_dict: dict[str, any],
        energy_dict: dict[str, MCorpCodeInfo],
        deno_dict: dict[str, MCorpCodeInfo],
        pref_dict: dict[str, MCorpCodeInfo],
        weather_dict,
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

        # スキップ行数
        header_row_num, skip_row_num = (
            (None, 1)
            if sheet_name == vis_constants.SheetName.COMPANY_INFO.value
            else (None, 0)
        )

        # シート内容格納用DF
        cur_sheet_df = pd.DataFrame()
        if sheet_name == vis_constants.SheetName.COMPANY_INFO.value:
            # 情報シート読込
            get_row_num = 11
            cur_sheet_df = pd.read_excel(
                input_file,
                sheet_name=sheet_name,
                header=header_row_num,
                skiprows=skip_row_num,
                nrows=get_row_num,
                usecols=[1, 2, 3],  # 項目：値
            )

            # 企業情報DataFrame設定
            self.set_corporate_info(
                cur_sheet_df=cur_sheet_df, request_dict=request_dict, org_id=org_id
            )

        if sheet_name == vis_constants.SheetName.LOCATION_INFO.value:

            self._set_location_info(
                input_file,
                sheet_name,
                corp_number,
                agreement_category,
                org_id,
                deno_dict,
            )

        if sheet_name == vis_constants.SheetName.CREDITS_INFO.value:
            # ==============================
            # 事前一括取得（map化）
            # ==============================

            # MBuilding 一括取得
            mbuilding_list = (
                self.session.query(MBuilding)
                .filter(
                    MBuilding.corporate_number == corp_number,
                    MBuilding.agreement_category == agreement_category,
                    MBuilding.delete_flg == False,
                )
                .all()
            )

            mbuilding_map = {b.building_id: b for b in mbuilding_list}

            # 共通可視化 一括取得
            common_vis_list = (
                self.session.query(TEnergyStorageCommonForVisualization)
                .filter(
                    TEnergyStorageCommonForVisualization.corporate_number
                    == corp_number,
                    TEnergyStorageCommonForVisualization.agreement_category
                    == agreement_category,
                )
                .all()
            )

            common_vis_map = {
                (e.building_id, e.year_month, e.energy_code): e for e in common_vis_list
            }
            # common_vis_map の index map 化
            common_vis_by_year_month = defaultdict(list)
            common_vis_by_building = defaultdict(list)

            for (b_id, ym, _), entity in common_vis_map.items():
                common_vis_by_year_month[ym].append(entity)
                common_vis_by_building[b_id].append(entity)

            # 月次建物集計 一括取得
            monthly_building_list = (
                self.session.query(TMonthlyBuildingEnergyAggregation)
                .filter(
                    TMonthlyBuildingEnergyAggregation.corporate_number == corp_number,
                    TMonthlyBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyBuildingEnergyAggregation.org_id == org_id,
                    TMonthlyBuildingEnergyAggregation.registration_seq == 0,
                )
                .all()
            )

            monthly_building_map = {
                (e.building_id, e.energy_code, e.target_year_month): e
                for e in monthly_building_list
            }
            # 月次法人集計 一括取得
            t_year_building_energy_list_db = (
                self.session.query(TAnnualBuildingEnergyAggregation)
                .filter(
                    TAnnualBuildingEnergyAggregation.corporate_number == corp_number,
                    TAnnualBuildingEnergyAggregation.agreement_category
                    == agreement_category,
                    TAnnualBuildingEnergyAggregation.org_id == org_id,
                    TAnnualBuildingEnergyAggregation.registration_seq == 0,
                )
                .all()
            )

            t_year_building_energy_map = {
                (e.building_id, e.energy_code, e.fiscal_year): e
                for e in t_year_building_energy_list_db
            }

            # 建物情報 一括取得
            tbuilding_info_list = (
                self.session.query(TBuildingInfo)
                .filter(
                    TBuildingInfo.corporate_number == corp_number,
                    TBuildingInfo.agreement_category == agreement_category,
                    TBuildingInfo.registration_seq == 0,
                )
                .all()
            )

            tbuilding_info_map = {
                (e.building_id, e.fiscal_year): e for e in tbuilding_info_list
            }

            # 年次法人 一括取得
            t_year_corp_energy_list_db = (
                self.session.query(TAnnualCorporateEnergyAggregation)
                .filter(
                    TAnnualCorporateEnergyAggregation.corporate_number == corp_number,
                    TAnnualCorporateEnergyAggregation.agreement_category
                    == agreement_category,
                    TAnnualCorporateEnergyAggregation.org_id == org_id,
                    TAnnualCorporateEnergyAggregation.registration_seq == 0,
                )
                .all()
            )

            t_year_corp_energy_map = {
                (e.energy_code, e.fiscal_year): e for e in t_year_corp_energy_list_db
            }
            # 月次法人 一括取得
            t_month_corp_energy_list_db = (
                self.session.query(TMonthlyCorporateEnergyAggregation)
                .filter(
                    TMonthlyCorporateEnergyAggregation.corporate_number == corp_number,
                    TMonthlyCorporateEnergyAggregation.agreement_category
                    == agreement_category,
                    TMonthlyCorporateEnergyAggregation.org_id == org_id,
                    TMonthlyCorporateEnergyAggregation.registration_seq == 0,
                )
                .all()
            )

            t_month_corp_energy_map = {
                (e.energy_code, e.target_year_month): e
                for e in t_month_corp_energy_list_db
            }

            # 証書・クレジット
            cur_sheet_df = pd.read_excel(
                input_file, sheet_name=sheet_name, header=2, engine="openpyxl"
            )

            # 年月列を事前に特定して変換
            for i, col in enumerate(cur_sheet_df.columns):
                if isinstance(col, datetime):
                    # datetimeオブジェクトを年月形式に変換
                    new_col = f"{col.year}年{col.month}月"
                    cur_sheet_df = cur_sheet_df.rename(columns={col: new_col})
                elif isinstance(col, str) and re.match(r"\d{4}-\d{2}-\d{2}", col):
                    # 日付文字列を年月形式に変換
                    try:
                        date = pd.to_datetime(col)
                        new_col = f"{date.year}年{date.month}月"
                        cur_sheet_df = cur_sheet_df.rename(columns={col: new_col})
                    except:
                        pass

            # 生df加工（列名変換を含む）
            cur_sheet_df = self._makeup_df(cur_sheet_df)

            # 日本語名：英語名マッピング
            sheet_cfg = vis_constants.sheet_mapping[sheet_name]
            column_mapping = sheet_cfg["column_mapping"]

            # 必要な列だけ抽出して英語名にリネーム
            cur_sheet_df = cur_sheet_df.rename(columns=column_mapping)
            # 年月列は小文字変換しない（年月形式を保持）
            non_year_month_cols = [
                col
                for col in cur_sheet_df.columns
                if "年" not in str(col) or "月" not in str(col)
            ]

            # 年月列以外のみ小文字変換
            for col in non_year_month_cols:
                if col in cur_sheet_df.columns:
                    cur_sheet_df = cur_sheet_df.rename(columns={col: col.lower()})

            # NaNや空白・空文字を除外
            cur_sheet_df = cur_sheet_df[
                cur_sheet_df["location_identifier_code"].notna()
                & ~cur_sheet_df["location_identifier_code"]
                .astype(str)
                .str.strip()
                .isin(["", "*"])
            ]

            # 列名が存在するかチェックしてから設定
            if "location_identifier_name" in cur_sheet_df.columns:
                cur_sheet_df["building_name"] = cur_sheet_df["location_identifier_name"]

            # 月別集計値を取得する
            # certificate_credit_nameからenergy_codeを取得してDataFrameに追加
            def get_energy_code(certificate_credit_name):
                if (
                    pd.isna(certificate_credit_name)
                    or str(certificate_credit_name).strip() == ""
                ):
                    return None
                energy_info = energy_dict.get(
                    str(certificate_credit_name).strip(), None
                )
                if energy_info:
                    return getattr(energy_info, "code", None)
                return None

            cur_sheet_df["corp_number"] = corp_number
            cur_sheet_df["energy_code"] = cur_sheet_df["certificate_credit_name"].apply(
                get_energy_code
            )

            # energy_codeがNoneの行は除外
            cur_sheet_df = cur_sheet_df[cur_sheet_df["energy_code"].notna()]

            # 建物、年月、エネルギーコードでグループ化
            id_vars = ["corp_number", "location_identifier_code", "energy_code"]
            year_month_dict: dict[tuple, dict] = _get_year_month_val_dict(
                cur_sheet_df, id_vars
            )

            if cur_sheet_df.empty:

                for key, val in self.update_bid_dict.items():

                    # key の 13 文字目以降（法人番号切り捨て）
                    location_identifier_code = key[13:] if len(key) > 13 else ""

                    # 建物ID構築
                    building_id = corp_number + location_identifier_code

                    # MBuildingから建物名、拠点名、拠点IDを取得
                    mbuilding_entity = mbuilding_map.get(building_id)

                    if mbuilding_entity:
                        building_name = (
                            mbuilding_entity.location_identifier_name
                        )  # 建物名（MBuildingから取得）
                        location_identifier_name = (
                            mbuilding_entity.location_identifier_name
                        )  # 拠点名（MBuildingから取得）
                        location_identifier_code = (
                            mbuilding_entity.location_identifier_code
                        )  # 拠点ID（MBuildingから取得）

                    # 該当企業・拠点情報シートのbuilding_id・年月・energy_codeのレコードを取得（拠点情報更新用）
                    # 共通可視化テーブルの該当拠点の全レコード（全年月）を取得して更新
                    target_records = common_vis_by_building.get(building_id, [])
                    self.apply_site_info_to_common_vis(target_records)

            else:
                tco2_to_kwh_map = {
                    "非化石証書（FIT）[t-CO2]": "非化石証書（FIT）[kWh]",
                    "非化石証書（非FIT・再エネ指定）[t-CO2]": "非化石証書（非FIT・再エネ指定）[kWh]",
                    "非化石証書（非FIT・再エネ指定なし）[t-CO2]": "非化石証書（非FIT・再エネ指定なし）[kWh]",
                }
                # 合算結果を一時保存する辞書 {(corp, location, credit_name, year_month): value}
                merged_credit_values = {}
                # 今回のシートに記載がある「拠点IDと年月の組み合わせ」を保持
                target_site_ym_set = set()
                # 更新対象となるレコードを保持するリスト
                updated_entities_in_this_sheet = []
                for credit_sheet_row in cur_sheet_df.itertuples():
                    # 建物ID構築
                    building_id = (
                        corp_number + credit_sheet_row.location_identifier_code
                    )

                    # MBuildingから建物名、拠点名、拠点IDを取得
                    mbuilding_entity = mbuilding_map.get(building_id)

                    if mbuilding_entity:
                        building_name = (
                            mbuilding_entity.location_identifier_name
                        )  # 建物名（MBuildingから取得）
                        location_identifier_name = (
                            mbuilding_entity.location_identifier_name
                        )  # 拠点名（MBuildingから取得）
                        location_identifier_code = (
                            mbuilding_entity.location_identifier_code
                        )  # 拠点ID（MBuildingから取得）

                    # 既に前シートで詰め込んだentityにデータ更新
                    credit_str = credit_sheet_row.certificate_credit_name
                    # hearing_entity.certificate_credit_name=credit_str
                    match = re.search(r"[［\[]([^\]］]*)[］\]]", credit_str)
                    if match:
                        credit_unit = match.group(1)
                        credit_name = credit_str[: match.start()]
                    else:
                        credit_unit = None
                        credit_name = credit_str

                    # 証書用エネルギーコード取得
                    energy_code = getattr(
                        energy_dict.get(credit_sheet_row.certificate_credit_name, None),
                        "code",
                        None,
                    )
                    if not energy_code:
                        continue

                    location_key = (
                        corp_number,
                        credit_sheet_row.location_identifier_code,
                        energy_code,
                    )

                    if location_key not in year_month_dict:
                        continue

                    value_dict = year_month_dict[location_key]

                    for year_month, use_value in value_dict.items():
                        # シートに記載がある拠点と年月を登録（電気等の更新判定に使用）
                        target_site_ym_set.add((building_id, year_month))
                        # 使用量が空、None、または無効な値の場合はスキップ
                        if (
                            pd.isna(use_value)
                            or use_value == ""
                            or str(use_value).strip() in ["", "*"]
                        ):
                            continue

                        # t-CO2→kWh換算
                        # energy_year = year_month[:4]
                        # emission_coef_month = energy_year + '04'
                        # #月の年ごとに係数情報取得
                        # if year_month < emission_coef_month:
                        #     emission_coef_year = energy_year
                        # else:
                        #     emission_coef_year = int(energy_year) + 1
                        # nfcmst_sub = self.nfcmst[self.nfcmst['REPORT_YEAR'] == int(emission_coef_year)] # TODO requestから取得してきたtarget_yearのチェック追加
                        # nfcmst_sub = nfcmst_sub[nfcmst_sub['FOSSIL_FREE_CERT_TYPE_ID'] == "1"]
                        # if nfcmst_sub.empty:
                        #     nfcmst_sub = self.nfcmst.loc[self.nfcmst['REPORT_YEAR'].idxmax()]
                        #     if nfcmst_sub['FOSSIL_FREE_CERT_TYPE_ID'] == "1":
                        #         nfcmst_sub = nfcmst_sub
                        # # 対象証書が t-CO2 の場合は kWh換算
                        # if credit_str in tco2_to_kwh_map:
                        #     use_value = round(use_value / float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]), 4)
                        #     target_credit_name = tco2_to_kwh_map[credit_str]
                        # else:
                        #     target_credit_name = credit_str

                        # key = (corp_number, location_identifier_code, target_credit_name, year_month)

                        # # 合算
                        # merged_credit_values[key] = merged_credit_values.get(key, 0) + use_value

                        # energy_codeは既に取得済み（上記で取得）

                        # 共通エネルギー
                        # 該当企業・年月のすべてのレコードを取得（企業情報更新用）
                        all_records = common_vis_by_year_month.get(year_month, [])

                        # 拠点情報シートで設定されたbuilding_idのリストを取得

                        # 新規作成の場合は証書・クレジットシートのbuilding_idを使用
                        common_vis_entity = common_vis_map.get(
                            (building_id, year_month, energy_code)
                        )

                        if not common_vis_entity:
                            # 新規作成時に NOT NULL 制約のある項目をすべて埋める
                            common_vis_entity = TEnergyStorageCommonForVisualization(
                                corporate_number=corp_number,
                                agreement_category=agreement_category,
                                org_id=org_id,
                                building_id=building_id,
                                energy_code=energy_code,
                                year_month=year_month,
                                energy_name=credit_name,
                                input_supplier_name=self.hearing_company_name,
                                location_identifier_code=credit_sheet_row.location_identifier_code,
                                created_by=self.user_id,
                                updated_by=None,
                            )
                            self.tcommon_vis_list.append(common_vis_entity)
                            common_vis_map[(building_id, year_month, energy_code)] = (
                                common_vis_entity
                            )
                        else:
                            # 既存レコードは共通処理で updated_by が入るため、ここでは更新しない
                            pass

                        compare_entity_with_model(
                            TEnergyStorageCommonForVisualization, common_vis_entity
                        )

                        energy_year = year_month[:4]
                        energy_month = year_month[4:6]
                        # emission_coef_month = energy_year + '04'
                        # #月の年ごとに係数情報取得
                        # if year_month < emission_coef_month:
                        #     emission_coef_year = energy_year
                        # else:
                        #     emission_coef_year = int(energy_year) + 1

                        emission_coef_year = (int(energy_year) - 1) + (
                            int(energy_month) >= 4
                        )

                        update_monthly_energy_info = {
                            # 登録値
                            "energy_category_name": credit_name,
                            # "energy_unit_original": credit_unit,
                            # "energy_unit_for_law": credit_unit,
                            # "energy_unit_for_report": credit_unit,
                            "energy_name_for_coefficient_matching": credit_str,
                            "heat_conversion_coefficient": 0,
                            "entry_draft_flag": "0",
                        }

                        # 検索用エネルギーコード
                        if energy_code in (
                            "9900011002",
                            "9900011003",
                            "9900011004",
                            "9900011013",
                        ):
                            energy_code = energy_code.replace("11", "10")

                        tbuilding_month_entity = monthly_building_map.get(
                            (building_id, energy_code, year_month)
                        )

                        if not tbuilding_month_entity:
                            tbuilding_month_entity = TMonthlyBuildingEnergyAggregation(
                                corporate_number=corp_number,
                                agreement_category=agreement_category,
                                org_id=org_id,
                                building_id=building_id,
                                energy_code=energy_code,
                                target_year_month=year_month,
                                registration_seq=0,
                                supplier_reg_no="0",
                            )
                            tbuilding_month_entity.created_by = self.user_id
                            compare_entity_with_model(
                                TMonthlyBuildingEnergyAggregation,
                                tbuilding_month_entity,
                            )
                            self.t_month_building_energy_list.append(
                                tbuilding_month_entity
                            )
                            # map に登録
                            monthly_building_map[
                                (building_id, energy_code, year_month)
                            ] = tbuilding_month_entity
                        else:
                            # 既存レコードもリストに追加（重複チェック付き）
                            if (
                                tbuilding_month_entity
                                not in self.t_month_building_energy_list
                            ):
                                compare_entity_with_model(
                                    TMonthlyBuildingEnergyAggregation,
                                    tbuilding_month_entity,
                                )
                                self.t_month_building_energy_list.append(
                                    tbuilding_month_entity
                                )
                            tbuilding_month_entity.updated_by = self.user_id

                        tbuilding_month_entity.fiscal_year = str(emission_coef_year)
                        # ①② 月次建物集計のbuilding_nameをMBuilding.location_identifier_nameから設定
                        if mbuilding_entity:
                            tbuilding_month_entity.building_name = (
                                mbuilding_entity.location_identifier_name
                            )
                        else:
                            # MBuildingが見つからない場合はmbid_dictから取得（フォールバック）
                            tbuilding_month_entity.building_name = self.mbid_dict[
                                building_id
                            ]["location_identifier_name"]
                        set_target_entity(
                            tbuilding_month_entity, update_monthly_energy_info
                        )

                        # 建物情報取得
                        fiscal_year = year_month[:4]
                        tbuilding_entity = tbuilding_info_map.get(
                            (building_id, fiscal_year)
                        )

                        tbuilding_gross_area = 0
                        if tbuilding_entity:
                            tbuilding_gross_area = (
                                tbuilding_entity.gross_floor_area
                                if tbuilding_entity.gross_floor_area
                                else 0
                            )

                        # 企業気温
                        corp_pref = getattr(
                            pref_dict.get(self.address_prefecture, None),
                            "en_code_name",
                            "hokkaido",
                        )
                        # 拠点気温
                        building_pref = getattr(
                            pref_dict.get(
                                self.mbid_dict[building_id][
                                    "building_address_prefecture"
                                ],
                                None,
                            ),
                            "en_code_name",
                            "hokkaido",
                        )

                        temp_year = year_month[:4]
                        temp_month = str(int(year_month[4:]))

                        def to_two_decimal_str(v):
                            if v is None:
                                return None
                            d = Decimal(str(v)).quantize(
                                Decimal("0.00"), rounding=ROUND_HALF_UP
                            )
                            return format(d, ".2f")  # 小数点以下2桁固定の文字列に変換

                        temp_corp = to_two_decimal_str(
                            (weather_dict.get((temp_year, temp_month)) or {}).get(
                                corp_pref
                            )
                        )
                        temp_building = to_two_decimal_str(
                            (weather_dict.get((temp_year, temp_month)) or {}).get(
                                building_pref
                            )
                        )
                        tbuilding_month_entity.temperature_corp = temp_corp
                        tbuilding_month_entity.temperature_building = temp_building

                        self.set_credit_info(
                            tbuilding_month_entity,
                            emission_coef_year,
                            energy_code,
                            use_value,
                            float(tbuilding_gross_area),
                            credit_unit,
                        )

                        # 実際に計算処理が行われたレコードをリストに保存
                        if common_vis_entity not in updated_entities_in_this_sheet:
                            updated_entities_in_this_sheet.append(common_vis_entity)

                        common_vis_entity.credit_certificate_name = (
                            tbuilding_month_entity.energy_name_for_coefficient_matching
                        )
                        common_vis_entity.credit_certificate_unit = credit_unit
                        common_vis_entity.energy_usage_monthly = (
                            tbuilding_month_entity.energy_quantity
                        )
                        common_vis_entity.co2_adjusted_emissions_monthly = (
                            tbuilding_month_entity.co2_adjusted_emissions
                        )
                        common_vis_entity.credit_certificate_purchase_energy_amount = (
                            tbuilding_month_entity.credit_certificate_purchase_energy_amount
                        )
                        common_vis_entity.credit_certificate_purchase_tco2_amount = (
                            tbuilding_month_entity.credit_certificate_purchase_tco2_amount
                        )

                # ----------------------------------------------------------------
                # 全ての計算終了後、今回のシート処理で実際に対象となった
                # (building_id, year_month, energy_code) のみを更新対象とする
                # ----------------------------------------------------------------
                target_records_to_update = []
                # 今回処理した common_vis_entity のみ対象にする
                if updated_entities_in_this_sheet:
                    target_records_to_update.extend(updated_entities_in_this_sheet)

                # 2. 今回新規作成したレコードを追加
                if self.tcommon_vis_list:
                    target_records_to_update.extend(self.tcommon_vis_list)

                # 3. 一括適用
                if target_records_to_update:
                    # 重複を除去（念のため）
                    unique_targets = list(dict.fromkeys(target_records_to_update))
                    self.apply_site_info_to_common_vis(unique_targets)
                    for record in unique_targets:
                        record.updated_by = self.user_id

                t_month_corp_energy_list = set_corp_month_entity_list(
                    self.t_month_building_energy_list, self.nfcmst
                )
                for src_entity in t_month_corp_energy_list:
                    map_key = (
                        src_entity["energy_code"],
                        src_entity["target_year_month"],
                    )
                    tmonth_corp_entity = t_month_corp_energy_map.get(map_key)

                    if not tmonth_corp_entity:
                        tmonth_corp_entity = TMonthlyCorporateEnergyAggregation(
                            corporate_number=corp_number,
                            agreement_category=agreement_category,
                            org_id=org_id,
                            energy_code=src_entity["energy_code"],
                            target_year_month=src_entity["target_year_month"],
                            registration_seq=0,
                        )
                        tmonth_corp_entity.created_by = self.user_id
                        compare_entity_with_model(
                            TMonthlyCorporateEnergyAggregation, tmonth_corp_entity
                        )
                        self.t_month_corp_energy_list.append(tmonth_corp_entity)
                        # map に登録
                        t_month_corp_energy_map[map_key] = tmonth_corp_entity

                    else:
                        tmonth_corp_entity.updated_by = self.user_id

                    # ③ 法人月次のfiscal_yearを月次建物と同一ロジックで付与（4月始まり）
                    ym = str(src_entity["target_year_month"])
                    y = int(ym[:4])
                    m = int(ym[4:])
                    fis_year = (y - 1) + (m >= 4)
                    tmonth_corp_entity.fiscal_year = str(fis_year)

                    # 集計結果（src_entity）の値を new_entity に反映
                    for attr, value in src_entity.items():
                        setattr(tmonth_corp_entity, attr, value)

                t_year_building_energy_list = set_building_year_entity_list(
                    self.t_month_building_energy_list
                )
                for src_entity in t_year_building_energy_list:
                    fiscal_year = str(src_entity["fiscal_year"])
                    map_key = (
                        src_entity["building_id"],
                        src_entity["energy_code"],
                        fiscal_year,
                    )
                    year_building_entity = t_year_building_energy_map.get(map_key)

                    if not year_building_entity:
                        year_building_entity = TAnnualBuildingEnergyAggregation(
                            corporate_number=corp_number,
                            agreement_category=agreement_category,
                            org_id=org_id,
                            building_id=src_entity["building_id"],
                            energy_code=src_entity["energy_code"],
                            target_year=str(src_entity["fiscal_year"]),
                            fiscal_year=str(src_entity["fiscal_year"]),
                            registration_seq=0,
                            supplier_reg_no="0",
                        )
                        year_building_entity.created_by = self.user_id
                        compare_entity_with_model(
                            TAnnualBuildingEnergyAggregation, year_building_entity
                        )
                        self.t_year_building_energy_list.append(year_building_entity)
                        # map に登録
                        t_year_building_energy_map[map_key] = year_building_entity

                    else:
                        # 既存レコードもリストに追加（重複チェック付き）
                        if year_building_entity not in self.t_year_building_energy_list:
                            compare_entity_with_model(
                                TAnnualBuildingEnergyAggregation, year_building_entity
                            )
                            self.t_year_building_energy_list.append(
                                year_building_entity
                            )
                        year_building_entity.updated_by = self.user_id

                    # ①② 年次建物集計のbuilding_nameをMBuilding.location_identifier_nameから設定
                    b_id = src_entity["building_id"]
                    # MBuildingから取得
                    year_mbuilding_entity = mbuilding_map.get(b_id)

                    if year_mbuilding_entity:
                        year_building_entity.building_name = (
                            year_mbuilding_entity.location_identifier_name
                        )
                    else:
                        # MBuildingが見つからない場合はmbid_dictから取得（フォールバック）
                        year_building_entity.building_name = self.mbid_dict[b_id][
                            "location_identifier_name"
                        ]

                    # 集計結果（src_entity）の値を new_entity に反映
                    for attr, value in src_entity.items():
                        setattr(year_building_entity, attr, value)

                t_year_corp_energy_list = set_corp_year_entity_list(
                    self.t_year_building_energy_list, self.nfcmst
                )
                for src_entity in t_year_corp_energy_list:
                    fiscal_year = str(src_entity["fiscal_year"])
                    map_key = (src_entity["energy_code"], fiscal_year)
                    year_corp_entity = t_year_corp_energy_map.get(map_key)

                    if not year_corp_entity:
                        year_corp_entity = TAnnualCorporateEnergyAggregation(
                            corporate_number=corp_number,
                            agreement_category=agreement_category,
                            org_id=org_id,
                            energy_code=src_entity["energy_code"],
                            target_year=str(src_entity["fiscal_year"]),
                            fiscal_year=str(src_entity["fiscal_year"]),
                            registration_seq=0,
                        )
                        year_corp_entity.created_by = self.user_id
                        compare_entity_with_model(
                            TAnnualCorporateEnergyAggregation, year_corp_entity
                        )
                        self.t_year_corp_energy_list.append(year_corp_entity)
                        # map に登録
                        t_year_corp_energy_map[map_key] = year_corp_entity

                    else:
                        # 既存レコードもリストに追加（重複チェック付き）
                        if year_corp_entity not in self.t_year_corp_energy_list:
                            compare_entity_with_model(
                                TAnnualCorporateEnergyAggregation, year_corp_entity
                            )
                            self.t_year_corp_energy_list.append(year_corp_entity)
                        year_corp_entity.updated_by = self.user_id

                    # 集計結果（src_entity）の値を new_entity に反映
                    for attr, value in src_entity.items():
                        setattr(year_corp_entity, attr, value)

    def set_credit_info(
        self,
        t_month_building_energy_entity: TMonthlyBuildingEnergyAggregation,
        emission_coef_year,
        energy_code,
        use_value,
        tbuilding_gross_area,
        credit_unit,
    ):
        def get_closest_year(df, target_year):
            # REPORT_YEAR を int に変換
            years = df["REPORT_YEAR"].astype(int)
            # 絶対値の差が最も小さい年を選ぶ
            closest_year = years.iloc[(years - target_year).abs().argsort().iloc[0]]
            return int(closest_year)
            # return str(closest_year)

        # nfcmst_sub = self.nfcmst[self.nfcmst['REPORT_YEAR'] == str(emission_coef_year + 1)]
        # if nfcmst_sub.empty:
        #     max_year = self.nfcmst['REPORT_YEAR'].max()
        #     nfcmst_sub = self.nfcmst[self.nfcmst['REPORT_YEAR'] == max_year]

        target_year = int(emission_coef_year) + 1
        # target_year = emission_coef_year + 1

        self.nfcmst["REPORT_YEAR"] = self.nfcmst["REPORT_YEAR"].astype(int)
        # まず同じ年を探す
        nfcmst_sub = self.nfcmst[
            self.nfcmst["REPORT_YEAR"]
            == int(target_year)
            # self.nfcmst['REPORT_YEAR'] == str(target_year)
        ]

        # 見つからなければ最も近い年を使う
        if nfcmst_sub.empty:
            closest_year = get_closest_year(
                self.nfcmst[self.nfcmst["FOSSIL_FREE_CERT_TYPE_ID"] == "1"], target_year
            )
            nfcmst_sub = self.nfcmst[self.nfcmst["REPORT_YEAR"] == closest_year]

        if energy_code == "9900010002":
            nfcmst_sub = nfcmst_sub[nfcmst_sub["FOSSIL_FREE_CERT_TYPE_ID"] == "1"]
        elif energy_code == "9900010003":
            nfcmst_sub = nfcmst_sub[nfcmst_sub["FOSSIL_FREE_CERT_TYPE_ID"] == "2"]
        elif energy_code == "9900010004":
            nfcmst_sub = nfcmst_sub[nfcmst_sub["FOSSIL_FREE_CERT_TYPE_ID"] == "3"]
        else:
            nfcmst_sub = nfcmst_sub[nfcmst_sub["FOSSIL_FREE_CERT_TYPE_ID"] == "1"]

        # 電力の場合
        if energy_code.startswith("9900010") and credit_unit != "t-CO2":
            if credit_unit == "MWh":
                co2EmissionCoefficient = (
                    float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]) * use_value * 1000
                )

                t_month_building_energy_entity.energy_quantity_for_law = float(
                    use_value
                )
                t_month_building_energy_entity.energy_quantity_for_report = float(
                    use_value * 1000
                )
                t_month_building_energy_entity.energy_quantity = use_value
            else:
                if energy_code in ("9900010013"):
                    co2EmissionCoefficient = (
                        float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]) * use_value
                    )
                else:
                    co2EmissionCoefficient = (
                        float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"])
                        * float(nfcmst_sub["CORRECTION_RATE"])
                        * use_value
                    )
                t_month_building_energy_entity.energy_quantity_for_law = float(
                    use_value / 1000
                )
                t_month_building_energy_entity.energy_quantity = (
                    t_month_building_energy_entity.energy_quantity_for_report
                ) = use_value

            t_month_building_energy_entity.energy_unit_for_law = "千KWh"
            t_month_building_energy_entity.energy_unit_original = (
                t_month_building_energy_entity.energy_unit_for_report
            ) = "kWh"

            t_month_building_energy_entity.co2_adjusted_emissions_zeb = (
                t_month_building_energy_entity.energy_quantity_for_report * 0.000551
                if t_month_building_energy_entity.energy_quantity_for_report is not None
                else 0.0
            )

        # CO2の場合
        elif (
            (
                energy_code.startswith("9900011")
                and energy_code not in vis_constants.heat_credit
            )
            or energy_code.startswith("9900010")
            and credit_unit == "t-CO2"
        ):
            # CO2値の付与
            co2EmissionCoefficient = use_value
            t_month_building_energy_entity.energy_unit_for_law = "千KWh"
            t_month_building_energy_entity.energy_unit_original = (
                t_month_building_energy_entity.energy_unit_for_report
            ) = "kWh"

            if energy_code not in vis_constants.no_elec_credit:
                t_month_building_energy_entity.energy_quantity_for_law = (
                    use_value / float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"]) / 1000
                )
                t_month_building_energy_entity.energy_quantity = (
                    t_month_building_energy_entity.energy_quantity_for_report
                ) = use_value / float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"])

            t_month_building_energy_entity.co2_adjusted_emissions_zeb = (
                t_month_building_energy_entity.energy_quantity_for_report * 0.000551
                if t_month_building_energy_entity.energy_quantity_for_report is not None
                else 0.0
            )

        # 熱の使用量変換
        elif energy_code in vis_constants.heat_credit:
            # CO2値の付与
            co2EmissionCoefficient = use_value
            self.hsmst_daitai["REPORT_YEAR"] = self.hsmst_daitai["REPORT_YEAR"].astype(
                int
            )
            available_years = self.hsmst_daitai["REPORT_YEAR"].unique()

            # emission_coef_year が存在しない場合 → 最も近い年度に差し替え
            if emission_coef_year not in available_years:
                available_years = np.asarray(available_years, dtype=int)
                emission_coef_year = int(emission_coef_year)

                nearest_year = available_years[
                    np.abs(available_years - emission_coef_year).argmin()
                ]
            else:
                nearest_year = emission_coef_year

            # 最終的に nearest_year を使って値を取得
            heat_adjusted_emission_factor = self.hsmst_daitai.loc[
                self.hsmst_daitai["REPORT_YEAR"] == nearest_year,
                "ADJUSTED_EMISSION_FACTOR",
            ].iloc[0]

            t_month_building_energy_entity.energy_quantity_for_law = round(
                use_value / float(heat_adjusted_emission_factor), 4
            )
            t_month_building_energy_entity.energy_unit_original = (
                t_month_building_energy_entity.energy_unit_for_report
            ) = t_month_building_energy_entity.energy_unit_for_law = "GJ"

            t_month_building_energy_entity.energy_quantity = (
                t_month_building_energy_entity.energy_quantity_for_report
            ) = round(use_value / float(heat_adjusted_emission_factor), 4)

            t_month_building_energy_entity.co2_adjusted_emissions_zeb = (
                t_month_building_energy_entity.energy_quantity_for_report * 0.06
                if t_month_building_energy_entity.energy_quantity_for_report is not None
                else 0.0
            )

        # t_month_building_energy_entity.energy_unit_original = t_month_building_energy_entity.energy_unit_for_report= credit_unit
        if credit_unit == "MWh":
            t_month_building_energy_entity.energy_unit_for_report = "KWh"
            t_month_building_energy_entity.energy_unit_original = "MWh"
        t_month_building_energy_entity.credit_certificate_unit = credit_unit

        t_month_building_energy_entity.co2_adjusted_emissions = co2EmissionCoefficient

        if not tbuilding_gross_area and co2EmissionCoefficient:
            # Co2調整後排出量原単位
            t_month_building_energy_entity.co2_adjusted_emissions_area_unit = (
                (co2EmissionCoefficient / tbuilding_gross_area)
                if (
                    tbuilding_gross_area is not None
                    and tbuilding_gross_area > 0
                    and co2EmissionCoefficient is not None
                )
                else None
            )

        t_month_building_energy_entity.credit_certificate_purchase_tco2_amount = (
            co2EmissionCoefficient
        )
        t_month_building_energy_entity.credit_certificate_purchase_energy_amount = (
            t_month_building_energy_entity.energy_quantity
            if credit_unit != "MWh"
            else t_month_building_energy_entity.energy_quantity_for_report
        )


def _get_year_month_val_dict(
    cur_sheet_df: pd.DataFrame, id_vars: list[str]
) -> dict[str, str]:
    """年月ごとの値を取得する

    Args:
        cur_sheet_df (pd.DataFrame): _description_

    Returns:
        dict[str, FileStorage]: _description_
    """

    def normalize_to_year_month(col_name: str) -> str:
        """列名が日付形式なら 'YYYY年M月' に統一"""
        s = str(col_name)
        # すでに「YYYY年M月」ならそのまま
        if re.match(r"^\d{4}年\d{1,2}月$", s):
            return s
        # '2024-12-01' や '2024/12/01' などの日付形式なら変換
        try:
            dt = pd.to_datetime(s, errors="raise")
            # OS依存しないゼロ削除対応
            ym = dt.strftime("%Y年%m月").replace("年0", "年").replace("月0", "月")
            return ym
        except Exception:
            return s  # 変換できないものはそのまま返す

    # DataFrame列名の一括変換
    cur_sheet_df.columns = [
        normalize_to_year_month(col) for col in cur_sheet_df.columns
    ]
    # 年月列だけ抽出
    year_month_cols = [
        col for col in cur_sheet_df.columns if re.match(r"^\d{4}年\d{1,2}月$", str(col))
    ]

    year_month_df = cur_sheet_df.melt(
        id_vars=id_vars,
        value_vars=year_month_cols,  # 年月の列だけ指定
        var_name="年月",
        value_name="value",
    )

    year_month_df = year_month_df[
        year_month_df["value"].replace(["", " ", "*"], np.nan).notna()
    ]

    year_month_df = year_month_df[
        year_month_df["value"].notna() & (year_month_df["value"] != "")
    ]

    # DB登録値はyyyyMMのため、フォーマット変換する
    year_month_df["年月"] = year_month_df["年月"].apply(convert_year_month)

    # "id" と "category" の複数列で groupby
    grouped = year_month_df.groupby(id_vars)

    # 各グループごとに年月→value の辞書を作成
    # 同じ年月に複数の値がある場合は合計する
    year_month_dict = {}
    for key_tuple, group in grouped:
        # 年月でさらにグループ化して、各年月の値を合計
        year_month_grouped = group.groupby("年月")["value"].sum()
        year_month_dict[key_tuple] = year_month_grouped.to_dict()

    return year_month_dict


def _get_ym_int(ym):
    """YYYYMM形式, YYYY年M月, Timestamp を整数 YYYYMM に変換"""
    if ym == "*":
        return
    if isinstance(ym, pd.Timestamp):
        return ym.year * 100 + ym.month
    if isinstance(ym, str):
        if re.match(r"\d{6}$", ym):
            return int(ym)
        m = re.match(r"^(\d{4})年(\d{1,2})月$", ym)
        if m:
            return int(m.group(1)) * 100 + int(m.group(2))
    raise ValueError(f"年月形式不正: {ym}")


# @log_time
def _extract_fiscal_years_by_12months(columns):
    """Excelなど様々な年月形式から4月〜翌年3月の年度を抽出"""
    fiscal_years = set()

    # サポートする日付／年月フォーマット候補
    date_formats = [
        "%Y%m",
        "%Y/%m",
        "%Y/%m/%d",
        "%Y-%m",
        "%Y-%m-%d",
        "%Y年%m月",
        "%Y年%m月%d日",
    ]

    for col in columns:
        col_str = str(col).strip()
        if col_str.endswith("*") or not col_str:
            continue

        # 数値（例: 202404）→文字列化
        if re.fullmatch(r"\d{6}", col_str):
            col_str = col_str

        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(col_str, fmt)
                break
            except ValueError:
                continue

        # パースできなければスキップ
        if not parsed_date:
            continue

        # 4月〜翌年3月で年度を判断
        fiscal_year = (
            parsed_date.year if parsed_date.month >= 4 else parsed_date.year - 1
        )
        fiscal_years.add(str(fiscal_year))

    return sorted(fiscal_years)


def set_corp_month_entity_list(
    t_building_month_entity_list: list[TMonthlyBuildingEnergyAggregation], nfcmst
):
    # groupby のキー項目（dataframe の groupby のキー列と対応）
    group_keys = (
        "energy_code",
        "energy_category_name",
        "energy_unit_for_law",
        # 'energy_unit_for_report',
        "target_year_month",
        "heat_conversion_coefficient",
        "co2_adjusted_emission_factor",
        # 'credit_certificate_unit',
        # 'energy_name_for_coefficient_matching'
    )

    # sum 対象の数値項目
    sum_fields = [
        "energy_quantity",
        "energy_quantity_for_law",
        "energy_quantity_for_report",
        # 'energy_usage_area_unit',
        "co2_adjusted_emissions_area_unit",
        "co2_adjusted_emissions",
        "credit_certificate_purchase_energy_amount",
        "credit_certificate_purchase_tco2_amount",
    ]

    building_year_entity_list = groupby_sum(
        t_building_month_entity_list, group_keys, sum_fields, nfcmst  # ormのリスト
    )

    return building_year_entity_list


def set_building_year_entity_list(
    t_building_month_entity_list: list[TMonthlyBuildingEnergyAggregation],
):
    group_keys_office = [
        "fiscal_year",
        "energy_code",
        "building_name",
        "energy_category_name",
        "energy_unit_original",
        "energy_unit_for_law",
        "energy_unit_for_report",
        "building_id",
        "energy_name_for_coefficient_matching",
        "supplier_name",
        "supply_conditions",
        "credit_certificate_unit",
    ]

    sum_fields_common = [
        "energy_quantity",
        "energy_quantity_for_law",
        "energy_quantity_for_report",
        "energy_usage_area_unit",
        "co2_adjusted_emissions_area_unit",
        "co2_adjusted_emissions",
        "credit_certificate_purchase_energy_amount",
        "credit_certificate_purchase_tco2_amount",
    ]

    building_year_entity_list = groupby_sum(
        t_building_month_entity_list,  # ormのリスト
        group_keys_office,
        sum_fields_common,
    )

    return building_year_entity_list


def set_corp_year_entity_list(
    t_building_year_entity_list: list[TAnnualBuildingEnergyAggregation], nfcmst
):

    group_keys_corporate_yearly = [
        "fiscal_year",
        "energy_code",
        "energy_category_name",
        # "energy_unit_original",
        "energy_unit_for_law",
        # "energy_unit_for_report",
        "supplier_name",
        "supply_conditions",
        # "credit_certificate_unit"
    ]
    sum_fields_corporate_yearly = [
        "energy_quantity",
        "energy_quantity_for_law",
        "energy_quantity_for_report",
        "energy_usage_area_unit",
        "co2_adjusted_emissions_area_unit",
        "co2_adjusted_emissions",
        "credit_certificate_purchase_energy_amount",
        "credit_certificate_purchase_tco2_amount",
    ]

    corpo_year_grouped_list = groupby_sum(
        t_building_year_entity_list,
        group_keys_corporate_yearly,
        sum_fields_corporate_yearly,
        nfcmst,
    )

    return corpo_year_grouped_list


def groupby_sum(entity_list, group_keys, sum_fields, nfcmst=None):
    """
    ORMエンティティのリストを groupby & sum して辞書リストで返す
    t-CO2 の場合は energy_quantity を NATIONAL_AVERAGE_FACTOR で換算する
    """

    grouped_data = defaultdict(lambda: {f: 0 for f in sum_fields})

    # target_year を別で保持
    target_year_map = {}
    nfcmst_sub = None
    for entity in entity_list:
        key = tuple(getattr(entity, k) for k in group_keys)
        if nfcmst is not None and not nfcmst.empty:
            nfcmst_sub = nfcmst[
                nfcmst["REPORT_YEAR"]
                == str(int(getattr(entity, "fiscal_year", None)) + 1)
            ]
            nfcmst_sub = nfcmst_sub[nfcmst_sub["FOSSIL_FREE_CERT_TYPE_ID"] == "1"]
            if nfcmst_sub.empty:
                nfcmst_sub = nfcmst.loc[nfcmst["REPORT_YEAR"].idxmax()]
                if nfcmst_sub["FOSSIL_FREE_CERT_TYPE_ID"] == "1":
                    nfcmst_sub = nfcmst_sub

        for f in sum_fields:
            v = safe_float(getattr(entity, f, 0)) or 0

            if nfcmst_sub is not None and not nfcmst_sub.empty:
                # ★ 変換ロジック：t-CO2 → エネルギー量換算
                if (
                    f == "energy_quantity"
                    and getattr(entity, "energy_unit_original", "") == "t-CO2"
                ):
                    try:
                        factor = float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"])
                        v = v / factor
                    except Exception:
                        # factor が不正などの場合は そのまま v を使う
                        pass
                if (
                    f == "energy_quantity_for_report"
                    and getattr(entity, "energy_unit_for_report", "") == "t-CO2"
                ):
                    try:
                        factor = float(nfcmst_sub["NATIONAL_AVERAGE_FACTOR"])
                        v = v / factor
                    except Exception:
                        # factor が不正などの場合は そのまま v を使う
                        pass

            grouped_data[key][f] += v

        # target_year の記録
        if key not in target_year_map:
            target_year_month = getattr(entity, "target_year_month", None)
            target_year = getattr(entity, "target_year", None)
            if target_year_month:
                target_year_map[key] = target_year_month[:4]
            if target_year:
                target_year_map[key] = target_year

    result_list = []
    for key, sums in grouped_data.items():
        record = dict(zip(group_keys, key))
        record.update(sums)
        result_list.append(record)

    return result_list


def groupby_sum_bk(entity_list, group_keys, sum_fields):
    """
    ORMエンティティのリストを groupby & sum して辞書リストで返す
    """

    grouped_data = defaultdict(lambda: {f: 0 for f in sum_fields})

    # target_year を別で保持
    target_year_map = {}

    for i, entity in enumerate(entity_list):
        key = tuple(getattr(entity, k) for k in group_keys)
        for f in sum_fields:
            grouped_data[key][f] += safe_float(getattr(entity, f, 0)) or 0
        # 同じキーなら1回だけ登録
        if key not in target_year_map:
            target_year_month = getattr(entity, "target_year_month", None)
            target_year = getattr(entity, "target_year", None)
            if target_year_month:  # Noneや空文字でなければ
                target_year_map[key] = target_year_month[:4]
            if target_year:
                target_year_map[key] = target_year

    result_list = []
    for key, sums in grouped_data.items():
        record = dict(zip(group_keys, key))
        record.update(sums)
        # record["target_year"] = target_year_map.get(key)
        result_list.append(record)

    return result_list


def groupby_sum_to_entity(template_entity, entity_list, group_keys, sum_fields):
    from collections import defaultdict

    grouped_data = defaultdict(lambda: {f: 0 for f in sum_fields})

    for entity in entity_list:
        key = tuple(getattr(entity, k) for k in group_keys)
        for f in sum_fields:
            grouped_data[key][f] += getattr(entity, f, 0)

    entity_result_list = []
    for key_values, sums in grouped_data.items():
        # 固定値はtemplate_entityからコピー
        new_entity = type(template_entity)()
        for attr, value in template_entity.__dict__.items():
            if not attr.startswith("_sa_instance_state"):
                setattr(new_entity, attr, value)
        # groupキーとsum結果を上書き
        for k, v in zip(group_keys, key_values):
            setattr(new_entity, k, v)
        for f, v in sums.items():
            setattr(new_entity, f, v)

        entity_result_list.append(new_entity)

    return entity_result_list


def get_field_precision_and_scale(model_class, field_name):
    """从SQLAlchemy模型中取得字段的precision和scale"""
    mapper = inspect(model_class)
    col = mapper.columns.get(field_name)
    if col is None:
        raise ValueError(
            f"モデル {model_class.__name__} に {field_name} 列が存在しません。"
        )
    col_type = col.type
    precision = getattr(col_type, "precision", None)
    scale = getattr(col_type, "scale", None)
    return precision, scale


def validate_field_against_model(model_class, entity, field_name):
    """比较模型定义的precision与实体字段值"""
    precision, scale = get_field_precision_and_scale(model_class, field_name)
    if precision is None:
        # 数值型でない場合などはスキップ
        return

    value = getattr(entity, field_name, None)
    if value is None:
        return

    value = Decimal(str(value))
    integer_part = str(value).split(".")[0]
    allowed_integer_digits = precision - (scale or 0)

    if len(integer_part) > allowed_integer_digits:
        error_msg = (
            f"{model_class.__tablename__}.{field_name} の整数部が "
            f"{allowed_integer_digits} 桁を超えています。"
            f"（現在 {len(integer_part)} 桁, 値={value}）"
        )

        abort(400, description=f"桁を超えています。詳細：{error_msg}")


def compare_entity_with_model(model_class, entity):
    # 対象フィールドを指定
    if model_class == TMonthlyBuildingEnergyAggregation:
        fields = [
            "energy_quantity_for_law",
            "energy_usage_area_unit",
            "energy_quantity",
            "energy_quantity_for_report",
            "co2_base_emissions",
            "co2_adjusted_emissions",
            "co2_adjusted_emissions_zeb",
            "co2_adjusted_emissions_avg",
            "co2_adjusted_emissions_area_unit",
            "credit_certificate_purchase_energy_amount",
            "credit_certificate_purchase_tco2_amount",
        ]
    elif model_class == TMonthlyCorporateEnergyAggregation:
        fields = [
            "energy_quantity_for_law",
            "energy_usage_area_unit",
            "energy_quantity",
            "energy_quantity_for_report",
            "co2_base_emissions",
            "co2_adjusted_emissions",
            "co2_adjusted_emissions_area_unit",
            "credit_certificate_purchase_energy_amount",
            "credit_certificate_purchase_tco2_amount",
        ]
    elif model_class == TAnnualBuildingEnergyAggregation:
        fields = [
            "energy_quantity_for_law",
            "energy_quantity_for_report",
            "energy_quantity",
            "co2_adjusted_emissions",
            "credit_certificate_purchase_energy_amount",
            "credit_certificate_purchase_tco2_amount",
        ]
    elif model_class == TAnnualCorporateEnergyAggregation:
        fields = [
            "energy_quantity_for_law",
            "energy_quantity_for_report",
            "energy_quantity",
            "co2_adjusted_emissions",
            "credit_certificate_purchase_energy_amount",
            "credit_certificate_purchase_tco2_amount",
        ]
    elif model_class == TEnergyStorageCommonForVisualization:
        fields = [
            "energy_usage_monthly",
            "co2_base_emissions",
            "co2_adjusted_emissions_monthly",
            "credit_certificate_purchase_energy_amount",
            "credit_certificate_purchase_tco2_amount",
        ]
    else:
        None

    for field in fields:
        if hasattr(entity, field):
            validate_field_against_model(model_class, entity, field)
