import math
import os
import platform
import re
import string
import time
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from http.client import HTTPException
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar, Dict, NamedTuple, Optional

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from flask import abort, current_app
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common import constants_colums, constants_values, utils
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.db_base_handler import BaseRepository
from cndx_corp_back.common.decorators import (
    jwt_user_context_db,
    log_time,
    service,
)
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_city_gas_heating_value_entity import MCityGasHeatingValue
from cndx_corp_back.entity.m_competitor_industry import MCompetitorIndustry
from cndx_corp_back.entity.m_corp_code_info_entity import MCorpCodeInfo
from cndx_corp_back.entity.m_corporate_basic_entity import MCorporateBasic
from cndx_corp_back.entity.m_corporate_details_info_entity import (
    MCorporateDetailsInfo,
)
from cndx_corp_back.entity.m_user_organization_info_entity import (
    MUserOrganizationInfo,
)
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_file import TFile
from cndx_corp_back.entity.t_monthly_building_energy_aggregation_entity import (
    TMonthlyBuildingEnergyAggregation,
)
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.logic.building_vis import building_vis_constants as vis_constants
from cndx_corp_back.logic.building_vis import (
    master_loader,
)

# from cndx_corp_back.logic.building_vis.building_vis_constants import vis_constants.SHEET_KEYWORDS, vis_constants.SheetName
from cndx_corp_back.logic.building_vis.building_vis_utils import (
    convert_year_month,
    df_to_repo,
    normalize_blank,
    safe,
)
from cndx_corp_back.logic.building_vis.file_validator import FileValidation
from cndx_corp_back.logic.building_vis.insert_vis_inputdata import (
    insert_input_table_data,
)
from cndx_corp_back.logic.building_vis.master_loader import MasterLoader
from cndx_corp_back.logic.building_vis.register_vis_aggregation_Info_component import (
    register_energy_aggregation_info,
)
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent


# 情報シート処理返却値
class CorporateResult(NamedTuple):
    corporate_df: pd.DataFrame
    corporate_number: str
    base_year_month: str


class InputFileParser:
    @jwt_user_context_db(refresh=False)
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
    ):

        self.input_file: FileStorage = input_file

        self.basic_df: pd.DataFrame = pd.DataFrame()
        self.corporate_df = pd.DataFrame(columns=constants_colums.corporate_column)
        self.building_df = pd.DataFrame(columns=constants_colums.building_column)
        self.energy_df = pd.DataFrame(columns=constants_colums.energy_column)
        self.site_gross_floor_area_df = pd.DataFrame()

        self.error_list: list[str] = []
        self.logger = logger
        self.session = session
        self.org_id = user_context.get("org_id")
        self.user_id = user_id
        self.request_dict = request_dict
        self.fiscal_years: list[str] = []
        self.fiscal_dict: dict[str, str] = {}
        self.year_month_list: list[str] = []
        master_loader: MasterLoader = MasterLoader(self.session)
        self.ccimst = master_loader.get_ccimst()
        self.bmmst = master_loader.get_bmmst()
        self.cnapp_entity = TCnApplicationInfo()
        self.tbuilding_entity_list: list[TBuildingInfo] = []

    # @log_time
    def main(self) -> dict[str, pd.DataFrame]:

        # 登録対象データ格納用辞書
        register_df_dic: dict[str, pd.DataFrame] = defaultdict(pd.DataFrame)
        try:
            # Excelファイル解析
            register_df_dic = self.file_data_process_main(self.input_file)

            # TDH登録処理
            if register_df_dic is None or len(register_df_dic) <= 0:
                self.logger.error(
                    "処理する対象データは取得されていないため、処理を中止する。"
                )
                return

            insert_input_table_data(
                self.bmmst,
                self.building_df["gross_floor_area"].mean(),
                self.session,
                register_df_dic["basic_df"],
                self.request_dict.get("agreement_category"),
                org_id=self.org_id,
                user_id=self.user_id,
                fiscal_years=self.fiscal_years,
                year_month_list=self.year_month_list,
                vis_company_name=self.vis_company_name,
            )

            # 集計データ登録
            for key in ["basic_df", "corporate_df", "building_df", "energy_df"]:
                df = register_df_dic[key]
                df = df.fillna("").infer_objects(copy=False)
                df.columns = df.columns.str.upper()
                register_df_dic[key] = df

            register_energy_aggregation_info(
                self.session,
                register_df_dic["basic_df"],
                register_df_dic["corporate_df"],
                register_df_dic["building_df"],
                register_df_dic["energy_df"],
                self.fiscal_years,
                self.logger,
            )
        except HTTPException:
            raise
        except Exception:
            raise

    # @log_time
    def file_data_process_main(self, input_file: FileStorage):

        self.logger.info(f"★処理対象ファイル名：{input_file.filename}")

        # abort(400, self.error_list)

        # エネルギーマッピングをコードマスタから取得
        energy_dict: dict[str, MCorpCodeInfo] = self._get_energy_mapping_str()

        # 処理対象シート名取得
        parse_sheet_names = [item["name"] for item in vis_constants.SHEET_NAME_LIST]

        # 処理対象シート名取得
        input_file_df = pd.ExcelFile(self.input_file)
        target_sheet_names = [
            sheet_name
            for sheet_name in (input_file_df.sheet_names)
            if sheet_name in parse_sheet_names
        ]

        # 情報シート以外シート読込
        unit_sheet_name = vis_constants.SheetName.UNIT_INFO.value
        unit_sheet_df = pd.read_excel(
            input_file,
            sheet_name=unit_sheet_name,
            skiprows=4,
            index_col=0,  # A列目は空のため、Unnamed: 0対応
        )

        # 生df加工
        unit_sheet_df = self.makeup_df(unit_sheet_df)

        # 日本語名：英語名マッピング
        sheet_cfg = vis_constants.sheet_mapping[unit_sheet_name]
        column_mapping = sheet_cfg["column_mapping"]

        # 必要な列だけ抽出して英語名にリネーム
        unit_sheet_df = unit_sheet_df.rename(columns=column_mapping)
        unit_sheet_df.columns = unit_sheet_df.columns.str.lower()
        unit_sheet_df = unit_sheet_df[unit_sheet_df["unit_deno_name"] == "延床面積"]
        # 月別集計値を取得する
        self.site_gross_floor_area_df = _get_year_month_val_dict(unit_sheet_df)

        for sheet_name in target_sheet_names:
            # DataFrame加工処理
            self.get_df_from_sheet(
                input_file=input_file,
                sheet_name=sheet_name,
                request_dict=self.request_dict,
                energy_dict=energy_dict,
            )

        file_upload = FileTransferComponent()

        # フォルダ構成名取得
        target_path_dict = {
            "put_sub_path": "input_excel_files",
            "org_type": "vis",
            "file_type": "energy_data",
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
        energy_file_entity.file_type = "2"
        energy_file_entity.created_by = self.user_id

        self.session.add(energy_file_entity)

        code_type_map = self._get_code_mapping_str()
        office_code_dict: dict[str, MCorpCodeInfo] = {
            row.jp_code_name: row
            for code_type in ("OFFICE_CODE", "HEAT_OFFICE_CODE")
            for row in code_type_map.get(code_type, [])
        }
        city_gas_code_map = self._get_city_gas_heating_value_mapping()

        # office_code_dict の code を簡単に取れるように map を用意
        supplier_map = {
            k: getattr(v, "code", None) for k, v in office_code_dict.items()
        }

        city_gas_supplier_map = {
            row.city_gas_supplier_nm: row.city_gas_supplier_cd
            for row in city_gas_code_map
        }

        self.set_energy_name(self.energy_df)
        self.transfer_energy_data(self.energy_df, supplier_map, city_gas_supplier_map)

        def choose_supplier(group):
            vals = group["supplier_reg_no"].dropna().unique().tolist()
            if not vals:
                return pd.Series(
                    {
                        "supplier_reg_no": None,
                        "supplier_name": None,
                        "supply_menu_no": None,
                        "supply_menu": None,
                    }
                )

            # REENE以外を優先
            non_reene = [v for v in vals if v != "REENE" and v != "SCOPE"]
            if non_reene:
                chosen = non_reene[0]
            elif "REENE" in vals:
                chosen = "REENE"
            elif "SCOPE" in vals:
                chosen = "SCOPE"
            else:
                chosen = None

            # 該当行（最初の一致1件）を取得
            match = (
                group[group["supplier_reg_no"] == chosen].iloc[0] if chosen else None
            )

            return pd.Series(
                {
                    "supplier_reg_no": chosen,
                    "supplier_name": (
                        match["supplier_name"] if match is not None else None
                    ),
                    "supply_menu_no": (
                        match["supply_menu_no"] if match is not None else None
                    ),
                    "supply_menu": match["supply_menu"] if match is not None else None,
                }
            )

        heat_office_code_dict: dict[str, str] = {
            row.code: row.jp_code_name
            for row in code_type_map.get("HEAT_OFFICE_CODE", [])
        }

        for tbuilding in self.tbuilding_entity_list:
            bid = tbuilding.building_id

            # 該当建物のエネルギーデータ抽出
            building_energy_df = self.energy_df[self.energy_df["building_id"] == bid]

            # --- 電気（energy_code が 02 で始まる）
            electricity_df = building_energy_df[
                building_energy_df["energy_code"].str.startswith("02")
            ]

            if not electricity_df.empty:
                electricity_result = choose_supplier(electricity_df)
                tbuilding.electricity_supplier_no = electricity_result.supplier_reg_no
                tbuilding.electricity_supplier_name = electricity_result.supplier_name
                tbuilding.electricity_contract_menu = electricity_result.supply_menu

            # --- 都市ガス（energy_code が 01 で始まる）
            gas_df = building_energy_df[
                building_energy_df["energy_code"].str.startswith("01")
            ]
            if not gas_df.empty:
                gas_result = choose_supplier(gas_df)
                tbuilding.city_gas_supplier_name = gas_result.supplier_name
                tbuilding.city_gas_supplier_no = gas_result.supplier_reg_no

            # --- 熱供給（energy_code が 03 で始まる）
            heat_df = building_energy_df[
                building_energy_df["energy_code"].str.startswith("03")
            ]
            if not heat_df.empty:
                heat_result = choose_supplier(heat_df)
                if heat_result.supplier_name == "DHC（MJ）":
                    heat_result.supplier_reg_no = "H0008A"
                elif heat_result.supplier_name == "DHC（Mcal）":
                    heat_result.supplier_reg_no = "H0008B"
                tbuilding.heat_supplier_name = heat_office_code_dict.get(
                    heat_result.supplier_reg_no
                )
                tbuilding.heat_supplier_no = heat_result.supplier_reg_no
                tbuilding.heat_contract_menu = heat_result.supply_menu

        self.energy_df = self.energy_df.merge(
            self.site_gross_floor_area_df[
                ["location_identifier_code", "year_month", "site_gross_floor_area"]
            ],
            on=["location_identifier_code", "year_month"],
            how="left",  # energy_dfをベースにする場合
        )

        # ========== 電気 ==========
        elec_df = self.energy_df.query("energy_name_jp == '電気'").copy()

        # building_id ごとに supplier_name → code をマップ化
        elec_supplier_map = dict(
            zip(
                elec_df["building_id"],
                elec_df["supplier_name"].map(lambda s: supplier_map.get(s)),
            )
        )
        # building_id ごとに supply_menu → code をマップ化
        elec_menu_map = dict(
            zip(
                elec_df["building_id"],
                elec_df["supply_menu"].map(lambda s: supplier_map.get(s)),
            )
        )

        # building_df に反映
        self.building_df["electric_company_reg_no"] = self.building_df[
            "building_id"
        ].map(elec_supplier_map)
        self.building_df["menu_no"] = self.building_df["building_id"].map(elec_menu_map)

        # ========== 熱系（冷水・温水・産業用以外の蒸気） ==========
        heat_df = self.energy_df.query(
            "energy_name_jp in ('冷水', '温水', '産業用以外の蒸気')"
        ).copy()

        heat_supplier_map = dict(
            zip(
                heat_df["building_id"],
                heat_df["supplier_name"].map(lambda s: supplier_map.get(s)),
            )
        )

        self.building_df["heat_supply_reg_no"] = self.building_df["building_id"].map(
            heat_supplier_map
        )

        # self.energy_df = self.energy_df[self.energy_df["energy_code"] != "0000000000"]
        new_energy_mask = self.energy_df["energy_code"] == "0000000000"

        self.energy_df.loc[new_energy_mask, ["supplier_name", "energy_name"]] = (
            self.energy_df.loc[
                new_energy_mask, ["input_supplier_name", "energy_name_jp"]
            ].values
        )
        self.energy_df.to_csv(f"energy_df.csv", index=False)

        corporate_repeated_df = pd.concat(
            [self.corporate_df] * len(self.building_df), ignore_index=True
        )

        # 両方とも index をリセットして 0,1,2… に揃える
        corporate_repeated_df.reset_index(drop=True, inplace=True)
        self.building_df.reset_index(drop=True, inplace=True)

        basic_df = pd.concat([corporate_repeated_df, self.building_df], axis=1)
        basic_df = basic_df.loc[:, ~basic_df.columns.duplicated()]
        basic_df["CREATED_BY"] = self.user_id
        basic_df["ENTRY_DRAFT_FLAG"] = 0
        basic_df = basic_df.reset_index(drop=True)

        # セットになる行員向け入力シートと簡易診断入力シートを管理する辞書
        register_df_dic = {
            "basic_df": basic_df,
            "corporate_df": self.corporate_df,
            "building_df": self.building_df,
            "energy_df": self.energy_df,
        }

        return register_df_dic

    # @log_time
    def set_corporate_df(
        self,
        *,
        cur_sheet_df: pd.DataFrame,
        session: scoped_session,
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
        # Requestから同意書と会社名取得
        agreement_category = request_dict.get("agreement_category", None)
        company_name = request_dict.get("company_name", None)
        corporate_number = request_dict.get("corporate_number", None)

        # 1列2列を 項目：値の辞書にする
        info_dict = {}
        for key, value in zip(cur_sheet_df[1], cur_sheet_df[2]):
            if key == "基準年月":
                # 数値なら Excel シリアルとして変換
                if isinstance(value, (int, float)):
                    info_dict[key] = excel_serial_to_year_month(value)
                else:
                    info_dict[key] = value  # 既に文字列ならそのまま
            else:
                info_dict[key] = value

        # info_dict = dict(zip(cur_sheet_df[1], cur_sheet_df[2]))
        # 企業名
        # sheet_company_name = info_dict[vis_constants.SHEET_KEYWORDS.get(vis_constants.SheetName.INFO.value).company_name]

        # 基準年月
        base_year_month = convert_year_month(
            info_dict[
                vis_constants.SHEET_KEYWORDS.get(
                    vis_constants.SheetName.INFO.value
                ).base_year_month
            ]
        )
        # 出力年数（2年）
        output_year_num = info_dict[
            vis_constants.SHEET_KEYWORDS.get(
                vis_constants.SheetName.INFO.value
            ).output_year_num
        ]

        # 企業名から法人番号取得（拠点ID構築するため）
        company_repo = BaseRepository(session, model=MCorporateBasic)
        # company_filters = {"company_name": sheet_company_name}
        company_filters = {"corporate_number": corporate_number}
        company_row = company_repo.find_one_by(**(company_filters or {}))

        corporate_number = company_row.corporate_number
        company_address_prefecture = (
            company_row.company_address_prefecture if company_row else ""
        )
        company_address_city = company_row.company_address_city if company_row else ""

        # "2年"から2を取得する
        matchYearInt = re.search(r"\d+", output_year_num)
        if matchYearInt:
            year_number = matchYearInt.group()

        # 年月のリスト取得
        self.year_month_list = _generate_month_list(base_year_month, year_number)
        self.fiscal_years = get_fiscal_years(self.year_month_list)

        self.corporate_df.at[0, "COMPANY_NAME"] = company_row.company_name
        self.corporate_df.at[0, "CORPORATE_NUMBER"] = corporate_number
        self.corporate_df.at[0, "ADDRESS_PREFECTURE"] = company_address_prefecture
        self.corporate_df.at[0, "ADDRESS_CITY"] = company_address_city
        # レポート開始年月、レポート終了年月設定修正
        # self.corporate_df.at[0, 'REPORT_PERIOD_START_YEAR_MONTH'] = base_year_month
        # self.corporate_df.at[0, 'REPORT_PERIOD_END_YEAR_MONTH'] = max(self.year_month_list)

        # self.corporate_df.at[0, 'FISCAL_YEAR'] = base_year_month[:4] # TODO 基準年は一年以上の場合どうする？

        # 産業分類はヒアリングシートアップロード済みであれば、企業詳細情報マスタから取得
        # 企業名から法人番号取得（拠点ID構築するため）
        company_details_repo = BaseRepository(session, model=MCorporateDetailsInfo)

        company_details_filters = {
            "corporate_number": corporate_number,
            "agreement_category": agreement_category,
            # "org_id": org_id
        }
        company_details_row = company_details_repo.find_all_by(
            **(company_details_filters or {})
        )

        company_db_data = {
            "INDUSTRY_MAJOR_CATEGORY": safe(
                getattr(company_details_row, "industry_class_major_name", "")
            ),
            "INDUSTRY_MIDDLE_CATEGORY": safe(
                getattr(company_details_row, "industry_class_middle_name", "")
            ),
            "INDUSTRY_MINOR_CATEGORY": safe(
                getattr(company_details_row, "industry_class_minor_name", "")
            ),
            "INDUSTRY_DETAIL_CATEGORY": safe(
                getattr(company_details_row, "industry_class_detail_name", "")
            ),
            "INDUSTRY_MAJOR_CODE": safe(
                getattr(company_details_row, "industry_class_major_code", "")
            ),
            "INDUSTRY_MIDDLE_CODE": safe(
                getattr(company_details_row, "industry_class_middle_code", "")
            ),
            "INDUSTRY_MINOR_CODE": safe(
                getattr(company_details_row, "industry_class_minor_code", "")
            ),
            "INDUSTRY_DETAIL_CODE": safe(
                getattr(company_details_row, "industry_class_detail_code", "")
            ),
        }

        for col, val in company_db_data.items():
            self.corporate_df.at[0, col] = val

        # 可視化側設定項目 TODO 列名変更する必要ある？
        self.corporate_df.at[0, "COMPANY_ADDRESS_PREFECTURE"] = (
            company_address_prefecture
        )
        self.corporate_df.at[0, "COMPANY_ADDRESS_CITY"] = company_address_city

        # ヘッダを小文字にする
        self.corporate_df.columns = self.corporate_df.columns.str.lower()

        # GHG排出量算定システム会社名の取得
        userOrganizationInfo = (
            session.query(MUserOrganizationInfo.company_name)
            .outerjoin(
                MBuilding, MUserOrganizationInfo.org_id == MBuilding.agreement_org
            )
            .filter(
                MBuilding.corporate_number == corporate_number,
                MBuilding.agreement_category == agreement_category,
                # MBuilding.org_id == org_id
            )
            .first()
        )

        self.vis_company_name = (
            userOrganizationInfo.company_name if userOrganizationInfo else ""
        )

        return self.corporate_df

    def _set_competitor_industry_co2_avg(
        self,
        bmmst_sub: pd.DataFrame,
        tbuilding_entity: TBuildingInfo = None,
        cnapp_entity: TCnApplicationInfo = None,
    ):
        if not bmmst_sub.empty:
            if cnapp_entity:
                gross_floor_area = self.building_df["gross_floor_area"].sum()
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

    # def _get_yearly_mean_gross_dict(self, df: pd.DataFrame) -> dict[int, float]:
    #     """
    #     year_month が昇順に並んでいる前提で、
    #     12行ごとに年度平均を計算し {年度: 平均値} の辞書を返す
    #     """
    #     df = df.copy().reset_index(drop=True)
    #     n_groups = math.ceil(len(df) / 12)  # 年度の数
    #     result = {}

    #     self.fiscal_dict = {ym: str(int(ym) // 100) for ym in df["year_month"]}

    #     for g in range(n_groups):
    #         group_df = df.iloc[g*12:(g+1)*12]

    #         if group_df.empty:
    #             continue

    #         # 年度は最初の月の年を採用
    #         first_ym = int(group_df.iloc[0]["year_month"])
    #         fiscal_year = str(first_ym // 100)

    #         # 平均 (NaNは無視)
    #         mean_val = group_df["site_gross_floor_area"].mean(skipna=True)
    #         result[fiscal_year] = mean_val

    #     # self.fiscal_years = list(result.keys()) # 報告年度統一のため

    #     return result

    def _get_yearly_mean_gross_dict(self, df: pd.DataFrame) -> dict[int, float]:
        """
        year_month が昇順に並んでいる前提で、
        4月～翌年3月を1年度とみなし、{年度+1: 平均値} の辞書を返す
        例：
            202301~202303 → fiscal_year=2023
            202304~202403 → fiscal_year=2024
            202404~202412 → fiscal_year=2025
        """
        df = df.copy().reset_index(drop=True)
        result = {}

        # 年月列から年度（fiscal_year）を算出
        def calc_fiscal_year(ym: int) -> int:
            year = ym // 100
            month = ym % 100
            # 4月〜12月は「翌年度」
            if month >= 4:
                return str(year)
            # 1〜3月は「その年の年度」
            else:
                return str(year - 1)

        df["fiscal_year"] = df["year_month"].astype(int).apply(calc_fiscal_year)

        # 各年度ごとに平均を計算
        for fy, group_df in df.groupby("fiscal_year"):
            mean_val = group_df["site_gross_floor_area"].mean(skipna=True)
            result[fy] = mean_val

        # fiscal_dict も更新（各 year_month → fiscal_year）
        self.fiscal_dict = dict(zip(df["year_month"], df["fiscal_year"]))

        return result

    # @log_time
    def set_building_df(
        self,
        *,
        cur_sheet_df: pd.DataFrame,
        request_dict: dict,
        org_id: str,
        user_id: str,
    ) -> pd.DataFrame:

        # Requestから同意書と会社名取得
        agreement_category = request_dict.get("agreement_category", None)

        corporate_number: str = self.corporate_df.at[0, "corporate_number"]
        # fiscal_year: str = self.corporate_df.at[0, 'fiscal_year'][:4]

        # インデックスを揃える
        self.building_df = self.building_df.reindex(cur_sheet_df.index)

        for col in cur_sheet_df.columns:
            self.building_df[col] = cur_sheet_df[col]

        cur_sheet_df.reset_index(drop=True, inplace=True)
        self.building_df = self.building_df.reset_index(drop=True)
        self.building_df.loc[:, "registration_seq"] = 0

        cur_sheet_df.columns = cur_sheet_df.columns.str.lower()
        self.building_df.columns = self.building_df.columns.str.lower()

        # entityのカラムに合わせてリネームする
        self.building_df = self.building_df.rename(
            columns={
                "building_address_prefecture": "address_prefecture",
                "building_address_city": "address_city",
                "location_identifier_code": "building_id",
            }
        )
        self.building_df = self.building_df.loc[
            :, ~self.building_df.columns.duplicated()
        ]

        pref_mapping = dict(
            zip(self.ccimst["JP_CODE_NAME"].str.upper(), self.ccimst["CODE"])
        )

        for idx, building_sheet_row in enumerate(cur_sheet_df.itertuples()):
            target_location_gross_df = self.site_gross_floor_area_df[
                self.site_gross_floor_area_df["location_identifier_code"]
                == building_sheet_row.location_identifier_code
            ]
            gross_yearly_dict = self._get_yearly_mean_gross_dict(
                target_location_gross_df
            )
            building_id = corporate_number + getattr(
                building_sheet_row, "location_identifier_code"
            )

            pref_code = pref_mapping.get(building_sheet_row.address_prefecture)
            # 建物マスタ更新
            mbuilding_entity = (
                self.session.query(MBuilding)
                .filter_by(
                    corporate_number=corporate_number,
                    agreement_category=agreement_category,
                    # org_id=org_id,
                    building_id=building_id,
                )
                .first()
            )
            if not mbuilding_entity:
                mbuilding_entity = MBuilding(
                    corporate_number=corporate_number,
                    agreement_category=agreement_category,
                    org_id=org_id,
                    building_id=building_id,
                    created_by=user_id,
                )
                self.session.add(mbuilding_entity)
            else:
                mbuilding_entity.updated_by = user_id

            mbuilding_entity.building_address_prefecture = pref_code
            mbuilding_entity.location_identifier_name = (
                building_sheet_row.location_identifier_name
            )
            if building_sheet_row.building_name:
                mbuilding_entity.building_name = building_sheet_row.building_name
            mbuilding_entity.building_address_city = building_sheet_row.address_city
            latest_year = max(gross_yearly_dict.keys())
            mbuilding_entity.gross_floor_area = float(
                gross_yearly_dict.get(latest_year, 0)
            )

            # 建物情報更新
            for building_fiscal_year in self.fiscal_years:
                # 毎回上書きするので、登録回数を全行分0に固定する
                self.building_df.at[idx, "registration_seq"] = 0
                self.building_df.at[idx, "fiscal_year"] = building_fiscal_year
                self.building_df.at[idx, "zip_code"] = building_sheet_row.zip_code
                self.building_df.at[idx, "gross_floor_area"] = float(
                    gross_yearly_dict.get(building_fiscal_year, 0)
                )
                self.building_df.at[idx, "municipality_code"] = (
                    building_sheet_row.municipality_code
                )
                self.building_df.at[idx, "location_identifier_name"] = (
                    building_sheet_row.location_identifier_name
                )
                self.building_df.at[idx, "building_name"] = (
                    building_sheet_row.location_identifier_name
                )

                self.building_df.at[idx, "building_id"] = building_id
                self.building_df.at[idx, "corporate_number"] = corporate_number
                self.building_df.at[idx, "agreement_category"] = agreement_category
                self.building_df.at[idx, "org_id"] = org_id
                self.building_df.at[idx, "ep_customer_number"] = (
                    mbuilding_entity.ep_customer_number
                )
                self.building_df.at[idx, "ep_office_code"] = (
                    mbuilding_entity.ep_office_code
                )

                tbuilding_entity = (
                    self.session.query(TBuildingInfo)
                    .filter_by(
                        corporate_number=corporate_number,
                        agreement_category=agreement_category,
                        org_id=org_id,
                        building_id=building_id,
                        registration_seq=0,
                        fiscal_year=building_fiscal_year,
                    )
                    .first()
                )
                if not tbuilding_entity:
                    tbuilding_entity = TBuildingInfo(
                        corporate_number=corporate_number,
                        agreement_category=agreement_category,
                        org_id=org_id,
                        building_id=building_id,
                        registration_seq=0,
                        fiscal_year=building_fiscal_year,
                        created_by=user_id,
                    )
                    self.session.add(tbuilding_entity)
                else:
                    tbuilding_entity.updated_by = user_id

                    # 拠点ベンチマック業種がベンチマックマスタに存在
                    bmmst_sub = self.bmmst[
                        (
                            self.bmmst["industry_class_detail_code"]
                            == tbuilding_entity.industry_class_detail_code
                        )
                        & (
                            self.bmmst["pulldown_code"]
                            == tbuilding_entity.energy_benchmark_target_industry
                        )
                    ]
                    if not bmmst_sub.empty:
                        tbuilding_entity.gross_floor_area = self.building_df.at[
                            idx, "gross_floor_area"
                        ]
                        self._set_competitor_industry_co2_avg(
                            bmmst_sub=bmmst_sub, tbuilding_entity=tbuilding_entity
                        )

                tbuilding_entity.entry_draft_flag = "0"
                tbuilding_entity.location_identifier_name = (
                    building_sheet_row.location_identifier_name
                )
                tbuilding_entity.address_prefecture = pref_code
                tbuilding_entity.address_city = building_sheet_row.address_city
                tbuilding_entity.gross_floor_area = self.building_df.at[
                    idx, "gross_floor_area"
                ]
                tbuilding_entity.zip_code = building_sheet_row.zip_code
                tbuilding_entity.ep_office_code = mbuilding_entity.ep_office_code
                tbuilding_entity.ep_customer_number = (
                    mbuilding_entity.ep_customer_number
                )
                tbuilding_entity.supply_point_number = (
                    mbuilding_entity.supply_point_number
                    if mbuilding_entity.supply_point_number
                    else "dummy"
                )

                self.tbuilding_entity_list.append(tbuilding_entity)

                self.building_df.at[idx, "supply_point_number"] = safe(
                    getattr(tbuilding_entity, "supply_point_number", "dummy")
                )
                self.building_df.at[idx, "BUILDING_ADDRESS_PREFECTURE"] = safe(
                    getattr(tbuilding_entity, "address_prefecture", "")
                )
                self.building_df.at[idx, "BUILDING_ADDRESS_CITY"] = safe(
                    getattr(tbuilding_entity, "address_city", "")
                )

        # dropする列名リストを作成
        cols_to_drop = [
            col
            for col in self.building_df.columns
            if re.search(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]", col)
            or "tel" in col.lower()
        ]

        # 不要カラムdrop実行
        self.building_df.drop(columns=cols_to_drop, inplace=True)

        self.building_df.to_csv("b.csv", index=False)
        return self.building_df

    def insert_cn_appl(self, agreement_category: str, org_id: str, user_id: str):
        row = self.basic_df.iloc[0].to_dict()
        cleaned_row = {k: v for k, v in row.items() if v is not None and not pd.isna(v)}

        # CN対策実施情報登録
        cn_application_repo = BaseRepository(self.session, model=TCnApplicationInfo)
        # TCnApplicationInfo が定義しているカラム名一覧を取得
        cn_allowed_fields = {c.name for c in TCnApplicationInfo.__table__.columns}

        # エクセルにない情報を下記辞書に追記する
        cn_info = {
            "agreement_category": agreement_category,
            "org_id": org_id,
            "registration_seq": 0,
            "entry_draft_flag": 0,
            "business_office_count": len(self.basic_df),
            "created_by": user_id,
        }

        cn_merged_row = {**cn_info, **cleaned_row}

        # allowed_fields だけに絞る
        cn_filtered_row = {
            k: v for k, v in cn_merged_row.items() if k in cn_allowed_fields
        }
        cn_entity = TCnApplicationInfo(**cn_filtered_row)
        cn_application_repo.insert_entity(cn_entity)

        # レポート格納情報登録
        report_storage_repo = BaseRepository(self.session, model=TReportStorageInfo)
        # TReportStorageInfo が定義しているカラム名一覧を取得
        report_allowed_fields = {c.name for c in TReportStorageInfo.__table__.columns}

        # エクセルにない情報を下記辞書に追記する
        report_info = {
            "agreement_category": agreement_category,
            "org_id": org_id,
            "registration_seq": 0,
            "entry_draft_flag": 0,
            "report_classify": 0,
            "created_by": user_id,
        }

        report_merged_row = {
            **report_info,
            **cleaned_row,
        }  # building のカラムが優先される

        # allowed_fields だけに絞る
        report_filtered_row = {
            k: v for k, v in report_merged_row.items() if k in report_allowed_fields
        }
        report_entity = TReportStorageInfo(**report_filtered_row)
        report_storage_repo.insert_entity(report_entity)

    def insert_entity_with_info(
        self,
        session,
        model,
        cleaned_row: dict,
        pk_info: dict,
        extra_info: dict,
        user_id: str,
    ) -> None:
        repo = BaseRepository(session, model=model)

        # 既存検索して、存在したら、update実行 TODO
        target_entity_list = repo.find_all_by(pk_info)
        if target_entity_list is not None and len(target_entity_list) == 1:
            # 既にデータ登録されましたら、update実行
            target_entity = target_entity_list[0]
            repo.update(target_entity, extra_info)

        else:
            # 物理削除 TODO
            # repo.delete_by_conditions(**extra_info)

            # 定義されているカラムだけ許可
            allowed_fields = {c.name for c in model.__table__.columns}

            # 共通情報にユーザー、作成日時を追加
            merged_row = {**extra_info, **cleaned_row, "created_by": user_id}

            filtered_row = {k: v for k, v in merged_row.items() if k in allowed_fields}
            entity = model(**filtered_row)

        repo.insert_entity(entity)

    def insert_input_table_data(
        self, agreement_category: str, org_id: str, user_id: str
    ):
        row = self.basic_df.iloc[0].to_dict()
        cleaned_row = {k: v for k, v in row.items() if v is not None and not pd.isna(v)}

        # CN対策申込情報登録
        cn_info = {
            "agreement_category": agreement_category,
            "org_id": org_id,
            "registration_seq": 0,
            "entry_draft_flag": 0,
            "business_office_count": len(self.basic_df),
        }

        self.insert_entity_with_info(
            session=self.session,
            model=TCnApplicationInfo,
            cleaned_row=cleaned_row,
            extra_info=cn_info,
            user_id=user_id,
        )

        # レポート格納情報
        report_info = {
            "agreement_category": agreement_category,
            "org_id": org_id,
            "registration_seq": 0,
            "entry_draft_flag": 0,
            "report_classify": 0,
        }

        self.insert_entity_with_info(
            session=self.session,
            model=TReportStorageInfo,
            cleaned_row=cleaned_row,
            extra_info=report_info,
            user_id=user_id,
        )

        # レポート格納情報
        report_info = {
            "agreement_category": agreement_category,
            "org_id": org_id,
            "registration_seq": 0,
            "entry_draft_flag": 0,
            "report_classify": 0,
        }

        self.insert_entity_with_info(
            session=self.session,
            model=TReportStorageInfo,
            cleaned_row=cleaned_row,
            extra_info=report_info,
            user_id=user_id,
        )

    # @log_time
    def _get_energy_mapping_str(self) -> dict[str, MCorpCodeInfo]:
        # コードマスタからエネルギーカテゴリ取得
        code_repo = BaseRepository(self.session, model=MCorpCodeInfo)
        # filters = {"code_type": "energy_category"}
        # energy_category_rows = code_repo.find_all(**(filters or {}))

        # コードマスタからエネルギーコード取得 TODO コードマスタ構造変更 カテゴリとコード一行管理
        filters = {"code_type": "ENERGY"}
        energy_rows = code_repo.find_all(**(filters or {}))

        # エネルギー名: record 取得
        energy_dict: dict[str, MCorpCodeInfo] = {
            energy_row.jp_code_name: energy_row for energy_row in energy_rows
        }
        return energy_dict

    # @log_time
    def _get_code_mapping_str(self) -> dict[str, MCorpCodeInfo]:
        # コードマスタの全データ取得
        code_repo = BaseRepository(self.session, model=MCorpCodeInfo)
        all_code_rows = code_repo.find_all()

        # code_typeごとにグルーピング
        from collections import defaultdict

        code_type_map: dict[str, list[MCorpCodeInfo]] = defaultdict(list)
        for row in all_code_rows:
            code_type_map[row.code_type].append(row)

        return code_type_map

    def _get_city_gas_heating_value_mapping(self) -> list[MCityGasHeatingValue]:
        # 都市ガス発熱量マスタの全データ取得
        heating_value_repo = BaseRepository(self.session, model=MCityGasHeatingValue)
        all_heating_value_rows = heating_value_repo.find_all()

        return all_heating_value_rows

    # @log_time
    def makeup_df(self, cur_sheet_df: pd.DataFrame) -> pd.DataFrame:
        def convert_excel_serial_to_ym(val):
            """
            Excel日付シリアル値を 'YYYY年M月' に変換する。
            数値でない場合はそのまま返す。
            """
            try:
                # 数値に変換できる場合のみ
                num = float(val)
                date = pd.to_datetime(num, unit="d", origin="1899-12-30")
                return f"{date.year}年{date.month}月"
            except Exception:
                return str(val)

        # ======== ここで先に変換 =========
        cur_sheet_df.columns = [
            convert_excel_serial_to_ym(c) for c in cur_sheet_df.columns
        ]
        # 小文字に統一
        cur_sheet_df.columns = cur_sheet_df.columns.str.lower()
        cur_sheet_df = cur_sheet_df.applymap(normalize_blank)

        # for col in cur_sheet_df.columns:
        #     # 文字列項目のnanを空白に変換
        #     if pd.api.types.is_object_dtype(cur_sheet_df[col]) or pd.api.types.is_string_dtype(cur_sheet_df[col]):
        #         cur_sheet_df[col] = cur_sheet_df[col].fillna("")
        #     # 数字項目の桁数保持

        #     if pd.api.types.is_numeric_dtype(cur_sheet_df[col]):
        #         cur_sheet_df[col] = cur_sheet_df[col].fillna("")

        # ヘッダの改行を削除する 延床面積\r\n m2とか
        cur_sheet_df.columns = cur_sheet_df.columns.str.replace(
            r"[\r\n]+", "", regex=True
        ).str.strip()

        return cur_sheet_df

    # @log_time
    def transfer_energy_data(
        self, energy_df: pd.DataFrame, supplier_map, city_gas_supplier_map
    ):
        energy_df["input_supplier_name"] = energy_df["supplier_name"]
        energy_df["supply_menu_no"] = None
        energy_df["supply_menu"] = None
        energy_df["category"] = None

        lpgas_mask = energy_df["energy_name_jp"] == "LPガス"
        # energy_df["supplier_name"] = energy_df["supplier_name"].apply(
        #     lambda x: None if str(x).startswith("一般") else x
        # )
        energy_df.loc[lpgas_mask, "supplier_name"] = energy_df.loc[
            lpgas_mask, "supplier_name"
        ].apply(lambda x: None if str(x).startswith("一般") else x)
        # LPガスの場合の供給会社名処理
        energy_df.loc[lpgas_mask, "supply_conditions"] = energy_df.loc[
            lpgas_mask, "supplier_name"
        ].str.extract(r"（(.*?)）")[
            0
        ]  # 全角括弧内を抽出
        energy_df.loc[lpgas_mask, "category"] = None

        energy_df.loc[lpgas_mask, "supplier_name"] = energy_df.loc[
            lpgas_mask, "supplier_name"
        ].apply(
            lambda x: (
                None
                if (("(" in str(x) or "（" in str(x)) and str(x).startswith("一般"))
                else x
            )
        )
        water_mask = (
            energy_df["energy_name_jp"].isin(["冷温水蒸気", "冷水", "蒸気"])
        ) & (energy_df["supplier_name"].astype(str).str.startswith("DHC"))
        energy_df.loc[water_mask, "supplier_name"] = None

        city_gas_mask = energy_df["energy_name_jp"] == "都市ガス"
        energy_df.loc[city_gas_mask, "supply_conditions"] = energy_df.loc[
            city_gas_mask, "supplier_name"
        ].str.extract(r"（(.*?)）")[
            0
        ]  # 全角括弧内を抽出

        energy_df.loc[city_gas_mask, "supplier_name"] = (
            energy_df.loc[city_gas_mask, "input_supplier_name"]
            # .astype(str)
            # .str.split("（")  # 全角括弧で分割
            # .str[0]           # 括弧より前だけ取得
        )

        # electric_mask = energy_df["energy_name_jp"] == "電気"
        # def split_by_menu(text):
        #     match = re.search(r'メニュー', text)
        #     if match:
        #         idx = match.start()
        #         return text[:idx], text[idx:]
        #     else:
        #         return text, ""

        # split_res = energy_df.loc[electric_mask, "supply_menu_no"].astype(str).apply(split_by_menu)

        # energy_df.loc[electric_mask, "supply_menu"] = split_res.str[1]
        # energy_df.loc[electric_mask, "supply_menu_no"] = 1 # TODO

        # 条件: 電気 かつ energy_code が "03" で始まる
        energy_menu_mask = (
            (energy_df["energy_name_jp"] == "電気")
            | (energy_df["energy_code"].astype(str).str.startswith("03"))
            | (energy_df["energy_name_jp"] == "都市ガス")
            | (energy_df["input_supplier_name"].str.contains("メニュー", na=False))
        )

        # A〜Z の番号マッピング
        letter_to_num = {ch: i for i, ch in enumerate(string.ascii_uppercase, 1)}

        def extract_menu_info(text):
            """
            以下の形式に対応する：
            ① EEGS_供給事業者
            ② EEGS_供給事業者_メニューA
            ③ EEGS_供給事業者_特別メニューA
            ④ 東京電力メニューA
            ⑤ メニューA
            ⑥ メニューＡ（全角）
            # ⑦ 供給事業者　残差
            """

            # 文字列以外の場合は空で返却
            if not isinstance(text, str):
                return ("", None)

            menu = ""

            # ====================================
            # ① EEGS形式の解析を優先する
            # ====================================

            if text.startswith("EEGS_"):
                parts = text.split("_")
                # EEGS_供給事業者 の場合（メニュー指定なし）
                if len(parts) == 2:
                    menu = ""

                # EEGS_供給事業者_メニュー名 の場合
                # ※ メニュー名に "_" が含まれるケースを考慮
                elif len(parts) >= 3:
                    menu = "_".join(parts[2:])

            # ====================================
            # ② 「メニュー」文字列を含む一般形式の解析
            # ====================================
            else:
                match = re.search(r"メニュー", text)

                if match:
                    idx = match.start()
                    # 「メニュー」以降をメニュー名とする
                    menu = text[idx:]
                # else:
                #     match = re.search(r'残差', text)
                #     if match:
                #         menu = text[match.start():]

            # ====================================
            # ③ メニュー番号（A～Z）の取得処理
            # ====================================

            menu_no = None

            if menu:
                # 半角／全角A～Zを取得
                letter_match = re.search(r"([A-ZＡ-Ｚ])", menu)

                if letter_match:
                    # 全角→半角変換
                    letter = (
                        letter_match.group(1)
                        .upper()
                        .translate(
                            str.maketrans(
                                "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ",
                                "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                            )
                        )
                    )

                    # 対応する番号を取得
                    menu_no = letter_to_num.get(letter)

            return (menu, menu_no)

        split_res = energy_df.loc[energy_menu_mask, "input_supplier_name"].apply(
            extract_menu_info
        )

        # DataFrameとして分解して代入
        split_df = pd.DataFrame(
            split_res.tolist(),
            columns=["supply_menu", "supply_menu_no"],
            index=split_res.index,
        )
        energy_df.loc[energy_menu_mask, ["supply_menu", "supply_menu_no"]] = split_df

        # split_res = energy_df.loc[energy_menu_mask, "input_supplier_name"].astype(str).apply(extract_menu_info)
        # energy_df.loc[energy_menu_mask, ["supply_menu", "supply_menu_no"]] = pd.DataFrame(split_res.tolist(), index=split_res.index)

        # メニューなしは None 扱い
        energy_df["supply_menu_no"] = energy_df["supply_menu_no"].replace(
            {np.nan: None}
        )

        def process_supplier_name_eegs(name):
            """
            供給事業者名を抽出する処理

            以下の形式に対応する：
            ① EEGS_供給事業者
            → 供給事業者を返却
            ② その他
            → 変換なし

            戻り値：
                供給事業者名
            """

            # NaNの場合はそのまま返却
            if pd.isna(name):
                return name

            name = str(name)

            # ====================================
            # ① EEGS形式を優先処理
            # ====================================
            # EEGS_供給事業者

            if name.startswith("EEGS_"):
                parts = name.split("_")
                if len(parts) >= 2:
                    return parts[1]
                return name

            return name

        def process_supplier_name(name):
            """
            供給事業者名を抽出する処理

            以下の形式に対応する：
            ① 供給事業者_メニュー名
            → 供給事業者を返却
            ③ 供給事業者（〇〇プラン）
            → 括弧以降を削除
            ④ 供給事業者 メニューA
            → メニュー以降を削除
            ⑤ 供給事業者 残差
            → 残差以降を削除
            ⑤ その他
            → 変換なし

            戻り値：
                供給事業者名
            """

            # NaNの場合はそのまま返却
            if pd.isna(name):
                return name

            name = str(name)

            # ====================================
            # ③ 括弧ありの場合
            # ====================================
            # 例：東京電力（従量電灯B）

            if "（" in name:

                return name.split("（")[0]

            # ====================================
            # ※以降削除
            # ====================================
            if "※" in name:
                name = re.sub(r"※.*", "", name).strip()

            # ====================================
            # ④ 「メニュー」表記ありの場合
            # ====================================
            # 例：東京電力 メニューA

            if "メニュー" in name:
                name = re.sub(r"\s*メニュー.*", "", name)
                return name

            # ====================================
            # ⑤ 残差削除
            # ====================================

            if "残差" in name:
                return re.sub(r"\s*残差.*", "", name)

            # ====================================
            # ⑥ その他は変換なし
            # ====================================

            return name

        energy_df["supplier_name"] = energy_df["supplier_name"].apply(
            process_supplier_name_eegs
        )

        exclude_words = "上記以外の自己託送|自家発電|オフサイト|沖縄電力"

        electric_mask = (
            (
                (energy_df["energy_name_jp"] == "電気")
                & ~energy_df["input_supplier_name"].str.contains(
                    exclude_words, regex=True, na=False
                )
            )
            | (energy_df["energy_code"].astype(str).str.startswith("03"))
            # | (energy_df["energy_name_jp"] == "都市ガス")
        )
        energy_df.loc[electric_mask, "supplier_name"] = energy_df.loc[
            electric_mask, "supplier_name"
        ].apply(process_supplier_name)

        energy_df.loc[lpgas_mask, "supply_conditions"] = energy_df.loc[
            lpgas_mask, "supplier_name"
        ].str.extract(r"（(.*?)）")[
            0
        ]  # 全角括弧内を抽出

        # allowed_energies = [
        #     "LPガス",
        #     "液化石油ガス（ＬＰＧ）",
        #     "冷水",
        #     "蒸気",
        #     "冷温水蒸気",
        #     "電気",
        #     "都市ガス",
        #     "一次エネルギー",
        #     "温水"
        # ]
        # mask = ~energy_df["energy_name_jp"].isin(allowed_energies)
        # energy_df.loc[mask, "supplier_name"] = None

        # fill_mask = ~water_mask
        # # 空文字も NaN 扱いにして置換
        # energy_df.loc[fill_mask, "supplier_name"] = (
        #     energy_df.loc[fill_mask, "supplier_name"]
        #     .replace("", pd.NA)
        #     .fillna(energy_df.loc[fill_mask, "energy_name_jp"])
        # )

        nohenkan_mask = energy_df["energy_name_jp"].isin(
            ["一次エネルギー", "冷水", "温水", "蒸気", "冷温水蒸気"]
        )
        energy_df.loc[nohenkan_mask, "supplier_name"] = (
            energy_df.loc[nohenkan_mask, "supplier_name"]
            .replace("", pd.NA)
            .fillna(energy_df.loc[nohenkan_mask, "energy_name_jp"])
        )

        allowed_energies = [
            "LPガス",
            "一次エネルギー",
            "冷水",
            "温水",
            "蒸気",
            "冷温水蒸気",
            "電気",
            "都市ガス",
        ]
        noallowed_mask = ~energy_df["energy_name_jp"].isin(allowed_energies) | (
            (energy_df["input_supplier_name"].astype(str).str.contains("DHC"))
            & (energy_df["energy_name_jp"].isin(allowed_energies))
        )
        energy_df.loc[noallowed_mask, "supplier_name"] = None

        new_lpgas_mask = energy_df["input_supplier_name"].str.contains(
            "佐野ガス", na=False
        ) & ~energy_df["input_supplier_name"].str.contains(r"\(", na=False)

        energy_df.loc[new_lpgas_mask, "supplier_name"] = energy_df.loc[
            new_lpgas_mask, "input_supplier_name"
        ]

        # onsui_mask = energy_df["energy_name_jp"] == "温水"

        # energy_df.loc[onsui_mask, "supplier_name"] = energy_df.loc[onsui_mask, "input_supplier_name"]

        new_menu_mask = energy_df["supplier_name"].str.contains("メニュー", na=False)

        energy_df.loc[new_menu_mask, "supplier_name"] = energy_df.loc[
            new_menu_mask, "supplier_name"
        ].str.replace(r"\s*メニュー.*", "", regex=True)

        energy_df["supplier_reg_no"] = energy_df["supplier_name"].map(supplier_map)

        if energy_df["energy_name_jp"].eq("都市ガス").any():
            energy_df.loc[city_gas_mask, "supplier_reg_no"] = energy_df.loc[
                city_gas_mask, "supplier_name"
            ].map(city_gas_supplier_map)

        # 電気の行だけ fillna("REENE")
        mask = energy_df["energy_name_jp"] == "電気"

        # まずは通常の supplier_name ベースで登録番号を付与
        energy_df.loc[mask, "supplier_reg_no"] = energy_df.loc[
            mask, "supplier_name"
        ].map(supplier_map)
        mask_03 = energy_df["energy_code"].astype(str).str.startswith("03")
        energy_df.loc[
            mask_03 & energy_df["supplier_reg_no"].isna(), "supplier_reg_no"
        ] = "H0999"

        # input_supplier_name が electric_supplier_map のキーに含まれている場合は上書き
        mask_override = mask & energy_df["input_supplier_name"].isin(
            vis_constants.electric_supplier_map.keys()
        )

        energy_df.loc[mask_override, "supplier_reg_no"] = energy_df.loc[
            mask_override, "input_supplier_name"
        ].map(supplier_map)

        energy_df["supplier_reg_no"] = energy_df["supplier_reg_no"].apply(
            lambda x: str(x)[:5] if pd.notna(x) and str(x).strip() != "" else None
        )

        # energy_df["supplier_reg_no"] = energy_df["supplier_reg_no"].astype(str).str.slice(0, 5)

    # @log_time
    def set_energy_name(self, df: pd.DataFrame) -> pd.DataFrame:
        # df = df.copy()

        # デフォルト（自分自身を使う）
        df["energy_name_for_report"] = df["energy_name_jp"]
        df["energy_name_for_coefficient_matching"] = df["energy_name_jp"]

        # 電気以外の変換
        for jp_name, (report, coef) in vis_constants.energy_mapping.items():
            mask = df["energy_name_jp"] == jp_name
            df.loc[
                mask, ["energy_name_for_report", "energy_name_for_coefficient_matching"]
            ] = (report, coef)

        # 電気の変換
        electric_mask = df["energy_name_jp"] == "電気"

        if electric_mask.any():  # ← ここでチェック

            def map_electric(supplier):
                return vis_constants.electric_supplier_map.get(
                    supplier,
                    ("電気", "電気事業者からの買電（化石電気）"),  # 辞書にない場合
                )

            mapped = (
                df.loc[electric_mask, "supplier_name"]
                .map(map_electric)
                .apply(pd.Series)
            )
            mapped.columns = [
                "energy_name_for_report",
                "energy_name_for_coefficient_matching",
            ]

            df.loc[
                electric_mask,
                ["energy_name_for_report", "energy_name_for_coefficient_matching"],
            ] = mapped.values

        df["energy_name_jp"] = df["energy_name_jp"].replace(
            {"重油（B重油）": "Ｂ・Ｃ重油", "重油（C重油）": "Ｂ・Ｃ重油"}
        )

        new_mask = df["energy_name_jp"] == "コンデンセート（NGL）"

        # df.loc[new_mask, "energy_name_for_report"] = "コンデンセート（NGL）"
        # df.loc[new_mask, "energy_name_for_coefficient_matching"] = "コンデンセート"

        # newOil_mask = df["energy_name_jp"] == "石油コークス又はFCCコーク（流動接触分解で使⽤された触媒に析出する炭素）"
        # df.loc[newOil_mask, "energy_name_for_report"] = df["energy_name_jp"]

        self.energy_df = df

    # @log_time
    def _set_energy_df(
        self,
        cur_sheet_df: pd.DataFrame,
        sheet_cfg: dict,
        sheet_name: str,
        energy_dict: dict[str, MCorpCodeInfo],
    ) -> pd.DataFrame:
        # 小文字ヘッダ
        self.energy_df.columns = self.energy_df.columns.str.lower()
        # 設定する行属性名、単位列名、エネルギー値列名
        row_attr, unit_col, value_col = (
            sheet_cfg["row_attr"].lower(),
            sheet_cfg["unit_col"].lower(),
            sheet_cfg["value_col"].lower(),
        )

        # エネルギー行単位キー
        key_cols = [
            "location_identifier_code",
            "energy_name_jp",
            "supplier_name",
            # 'day_category',
        ]

        # ============================================
        # 昼夜補正の対象外列
        # ============================================
        exclude_cols = set(
            key_cols
            + [
                "day_category",
                "excel_row",
            ]
        )

        # ============================================
        # 補正対象列（数値列のみ）
        # ============================================
        value_cols = [
            col
            for col in cur_sheet_df.columns
            if col not in exclude_cols
            and pd.api.types.is_numeric_dtype(cur_sheet_df[col])
        ]

        def complement_day_to_night(group: pd.DataFrame) -> pd.DataFrame:
            """
            昼行は夜行補完用としてのみ使用する。
            夜行が NULL / 0 の場合のみ昼行の値で補完し、
            最終的に夜行のみを残す。
            """

            # 夜行が存在しない場合は何もしない
            if "夜" not in group["day_category"].values:
                return group

            # 夜行を取得
            night_idx = group[group["day_category"] == "夜"].index[0]

            # 昼行が無ければ夜行のみ返却
            if "昼" not in group["day_category"].values:
                return group.loc[[night_idx]]

            day_idx = group[group["day_category"] == "昼"].index[0]

            # 夜行を補完
            for col in value_cols:
                night_val = group.at[night_idx, col]
                day_val = group.at[day_idx, col]

                # 夜が NULL または 0 の場合のみ昼で補完
                if (pd.isna(night_val) or night_val == 0) and not pd.isna(day_val):
                    group.at[night_idx, col] = day_val

            # 昼行を削除し、夜行のみ返却
            return group.loc[[night_idx]]

        # ============================================
        # 昼夜補正処理を実行
        # ============================================
        cur_sheet_df = (
            cur_sheet_df.groupby(key_cols, group_keys=False)
            .apply(complement_day_to_night)
            .reset_index(drop=True)
        )

        # 同じ供給会社のエネルギーは最後の行だけを残す
        cur_sheet_df = cur_sheet_df[
            ~cur_sheet_df.duplicated(subset=key_cols, keep="last")
        ]

        # 年月形式の列名を抽出
        year_month_cols = [
            col
            for col in cur_sheet_df.columns
            if pd.Series(col)
            .dropna()
            .astype(str)
            .str.match(r"^\d{4}年\d{1,2}月$")
            .any()
        ]

        ym_col_map = {}
        for col in year_month_cols:
            m = re.match(r"(\d{4})年(\d{1,2})月", col)
            if m:
                year, month = m.groups()
                ym_col_map[col] = f"{year}{month.zfill(2)}"

        cur_sheet_df = cur_sheet_df.rename(columns=ym_col_map)
        year_month_cols = list(ym_col_map.values())

        unit_df = cur_sheet_df[key_cols + [row_attr]]

        # 横持の月分データを縦持ちのロング形式にする
        long_sheet_df = cur_sheet_df.melt(
            id_vars=key_cols + ["day_category", "excel_row"],
            value_vars=year_month_cols,
            var_name="year_month",
            value_name=value_col,
        )

        long_sheet_df = long_sheet_df.merge(unit_df, on=key_cols, how="left")
        long_sheet_df = long_sheet_df.rename(columns={row_attr: unit_col})

        # 年月列をyear/month列に分割
        long_sheet_df["year"] = long_sheet_df["year_month"].str[:4]
        long_sheet_df["month"] = long_sheet_df["year_month"].str[-2:]

        # long_sheet_df[unit_col] = np.repeat(cur_sheet_df[row_attr].values, len(year_month_cols))
        # long_sheet_df[unit_col] = cur_sheet_df[row_attr].repeat(len(year_month_dict)).reset_index(drop=True)

        # 基準年/energy_code/energy_name設定
        # long_sheet_df["fiscal_year"] = self.corporate_df.at[0, 'fiscal_year'][:4]
        long_sheet_df["fiscal_year"] = long_sheet_df["year_month"].map(
            lambda ym: self.fiscal_dict.get(ym)
        )
        # long_sheet_df["energy_name_jp"]=long_sheet_df["energy_name_jp"]+long_sheet_df["day_category"]

        def get_mst_energy(jp_name: str):
            # energy_mapping から coef を取得（ない場合は None）
            coef = vis_constants.energy_mapping.get(jp_name, (None, None))[1]

            if coef:  # mapping に存在 → coef から取得
                energy_obj = energy_dict.get(coef, None)
            else:  # mapping に存在しない → jp_name から直接取得
                energy_obj = energy_dict.get(jp_name, None)

            code = getattr(energy_obj, "code", "0000000000")
            en_name = getattr(energy_obj, "en_code_name", "DEFAULT_NAME")

            return (code, en_name)

        # map → DataFrame展開
        mapped_values = long_sheet_df["energy_name_jp"].map(get_mst_energy)
        long_sheet_df[["energy_code", "energy_name"]] = pd.DataFrame(
            mapped_values.tolist(), index=long_sheet_df.index
        )

        # long_sheet_df["energy_code"] = long_sheet_df["energy_name_jp"].map(
        #     lambda x: getattr(energy_dict.get(x, None), "code", "0000000000")
        # )
        # long_sheet_df["energy_name"] = long_sheet_df["energy_name_jp"].map(
        #     lambda x: getattr(energy_dict.get(x, None), "en_code_name", "DEFAULT_NAME")
        # )
        # 空文字を NaN に変換
        long_sheet_df.replace({"energy_name_jp": {"": pd.NA}}, inplace=True)

        # NaN の行を削除
        long_sheet_df = long_sheet_df.dropna(subset=["energy_name_jp"])
        long_sheet_df = long_sheet_df.replace({value_col: ""}, np.nan)
        long_sheet_df = long_sheet_df.dropna(subset=[value_col])
        long_sheet_df.to_csv(f"{sheet_name}.csv", index=False)
        # self.energy_df とマージ
        merge_keys = key_cols + ["year_month"]

        merged = pd.merge(
            self.energy_df,
            long_sheet_df,
            how="outer",
            on=merge_keys,
            suffixes=("", "_new"),
            indicator=True,
        )

        if "day_category_new" in merged.columns:
            merged["day_category"] = merged["day_category_new"].combine_first(
                merged["day_category"]
            )
            merged.drop(columns=["day_category_new"], inplace=True)

        if "excel_row_new" in merged.columns:
            merged["excel_row"] = merged["excel_row_new"].combine_first(
                merged["excel_row"]
            )
            merged.drop(columns=["excel_row_new"], inplace=True)
        # 新規・既存行をまとめて更新
        for col in [
            "fiscal_year",
            "energy_code",
            "energy_name",
            value_col,
            unit_col,
            "year",
            "month",
        ]:
            # merged[col] = merged[col + "_new"].combine_first(merged[col])
            # merged.drop(columns=[col + "_new"], inplace=True)

            # 空の要素を除去した状態で combine_first を使う例
            # NaNを埋めるならfillna(適当な値)に変更可能

            new_col = merged[col + "_new"].copy()
            old_col = merged[col].copy()

            # 例えば、両方とも NaN を False に変換（必要なら変更）
            # ここでは NaNをFalseに置換例：
            new_col = new_col.where(new_col.notna(), None)
            old_col = old_col.where(old_col.notna(), None)

            merged[col] = new_col.combine_first(old_col)
            merged = merged.drop(columns=[col + "_new"])

        # マージ結果を元に戻す
        self.energy_df = merged.drop(columns=["_merge"]).copy()
        self.energy_df["building_id"] = (
            self.corporate_df.at[0, "corporate_number"]
            + self.energy_df["location_identifier_code"]
        )

        building_dict = dict(
            zip(self.building_df["building_id"], self.building_df["building_name"])
        )
        self.energy_df["building_name"] = (
            self.energy_df["building_id"]
            .map(building_dict)
            .fillna(self.energy_df["building_id"])
        )

        # self.energy_df.to_csv("self.energy_df.csv", index=False)
        return self.energy_df

    # @log_time
    def get_df_from_sheet(
        self,
        *,
        input_file: FileStorage,
        sheet_name: str,
        request_dict: dict[str, any],
        energy_dict: dict[str, MCorpCodeInfo],
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

        # スキップ行数
        header_row_num, skip_row_num = (
            (None, 2) if sheet_name == vis_constants.SheetName.INFO.value else (4, 4)
        )

        # シート内容格納用DF
        cur_sheet_df = pd.DataFrame()
        if sheet_name == vis_constants.SheetName.INFO.value:
            # 情報シート読込
            get_row_num = 7
            cur_sheet_df = pd.read_excel(
                input_file,
                sheet_name=sheet_name,
                header=header_row_num,
                skiprows=skip_row_num,
                nrows=get_row_num,
                usecols=[1, 2],  # 項目：値
            )

            # 企業情報DataFrame設定
            self.corporate_df = self.set_corporate_df(
                cur_sheet_df=cur_sheet_df,
                session=self.session,
                request_dict=request_dict,
                org_id=org_id,
            )

        else:
            if (
                sheet_name == vis_constants.SheetName.BUILDING_INFO.value
                or sheet_name == vis_constants.SheetName.UNIT_INFO.value
            ):
                # 情報シート以外シート読込
                cur_sheet_df = pd.read_excel(
                    input_file,
                    sheet_name=sheet_name,
                    # header=header_row_num, # skiprowだけでいい、指定不要
                    skiprows=skip_row_num,
                    index_col=0,  # A列目は空のため、Unnamed: 0対応
                )
            else:
                cur_sheet_df = pd.read_excel(
                    input_file,
                    sheet_name=sheet_name,
                    skiprows=skip_row_num,
                    index_col=None,
                    header=None,  # 一旦ヘッダを無効にして
                    dtype=str,  # すべて文字列として読む
                )

                # 手動でヘッダ行を取り出して normalize
                header_row = (
                    pd.read_excel(
                        input_file,
                        sheet_name=sheet_name,
                        skiprows=skip_row_num,
                        index_col=None,
                        nrows=1,  # ヘッダ行だけ読む
                        header=None,
                    )
                    .iloc[0]
                    .tolist()
                )

                # N列目のインデックス（例: N=14 → 0始まりで13）
                start_col_idx = 12

                # 年月列だけ normalize
                for i, col_idx in enumerate(
                    range(start_col_idx, start_col_idx + len(self.year_month_list) - 1)
                ):
                    header_row[col_idx] = normalize_header(header_row[col_idx])

                # それ以外の列はそのまま
                new_columns = header_row

                # ヘッダを設定して実データを再ロード
                cur_sheet_df = pd.read_excel(
                    input_file,
                    sheet_name=sheet_name,
                    skiprows=skip_row_num,  # ヘッダ行は飛ばす
                    index_col=None,
                )

                # cur_sheet_df = cur_sheet_df.loc[:, ~cur_sheet_df.columns.astype(str).str.contains("^Unnamed")]
                cur_sheet_df.columns = new_columns

                cur_sheet_df["excel_row"] = range(1, len(cur_sheet_df) + 1)

            # 生df加工
            cur_sheet_df = self.makeup_df(cur_sheet_df)

            # 日本語名：英語名マッピング
            sheet_cfg = vis_constants.sheet_mapping[sheet_name]
            column_mapping = sheet_cfg["column_mapping"]

            # 必要な列だけ抽出して英語名にリネーム
            cur_sheet_df = cur_sheet_df.rename(columns=column_mapping)
            cur_sheet_df.columns = cur_sheet_df.columns.str.lower()
            # if sheet_name == vis_constants.SheetName.UNIT_INFO.value:
            #     cur_sheet_df = cur_sheet_df[cur_sheet_df["unit_deno_name"] == "延床面積"]
            #     # 月別集計値を取得する
            #     self.site_gross_floor_area_df = _get_year_month_val_dict(cur_sheet_df)

            if sheet_name == vis_constants.SheetName.BUILDING_INFO.value:
                # 物件情報シート
                # 建物用DF構築
                self.building_df = self.set_building_df(
                    cur_sheet_df=cur_sheet_df,
                    request_dict=request_dict,
                    org_id=org_id,
                    user_id=user_id,
                )
            else:
                if (
                    sheet_name in vis_constants.sheet_mapping
                    and sheet_name != vis_constants.SheetName.UNIT_INFO.value
                ):
                    # 集計対象シート
                    # エネルギー集計情報用DF構築
                    self.energy_df = self._set_energy_df(
                        cur_sheet_df, sheet_cfg, sheet_name, energy_dict
                    )


# @log_time
def _get_year_month_val_dict(cur_sheet_df: pd.DataFrame) -> pd.DataFrame:
    """年月ごとの値を取得する

    Args:
        cur_sheet_df (pd.DataFrame): _description_

    Returns:
        dict[str, FileStorage]: _description_
    """
    # 年月形式の列名を抽出
    year_month_cols = [
        col
        for col in cur_sheet_df.columns
        if pd.Series(col).str.match(r"\d{4}年\d{1,2}月").any()
    ]
    year_month_df = cur_sheet_df.melt(
        id_vars=["location_identifier_code"],  # 他の列は無視
        value_vars=year_month_cols,  # 年月の列だけ指定
        var_name="year_month",
        value_name="site_gross_floor_area",
    )
    year_month_df = year_month_df.dropna(subset=["site_gross_floor_area"])
    year_month_df = year_month_df[
        year_month_df["site_gross_floor_area"].notna()
        & (year_month_df["site_gross_floor_area"] != "")
    ]

    # DB登録値はyyyyMMのため、フォーマット変換する
    year_month_df["year_month"] = year_month_df["year_month"].apply(convert_year_month)

    year_month_df.to_csv("yeary.csv", index=False)

    # year_month_dict = dict(zip(year_month_df["年月"], year_month_df["value"]))

    return year_month_df


def _generate_month_list(start_str: str, year_str: str) -> list[str]:
    """年月リスト取得

    Args:
        start_str (str): 開始年月
        year_str (str): 計算年数

    Returns:
        list[str]: 年月取得
    """
    # "2年" → 2
    match = re.search(r"\d+", year_str)
    years = int(match.group()) if match else 0

    # 開始年月を datetime に変換
    start_date = datetime.strptime(start_str, "%Y%m")

    # 月数を計算（2年 = 24ヶ月）
    total_months = years * 12

    # 月ごとのリストを作成
    month_list = [
        (start_date + relativedelta(months=i)).strftime("%Y%m")
        for i in range(total_months)
    ]

    return month_list


def get_fiscal_years(month_list):
    """_summary_

    Args:
        month_list (_type_): _description_

    Returns:
        _type_: _description_
    """
    fiscal_years = set()
    for ym in month_list:
        # 年度ではなく、そのままの年を取得する
        # fiscal_years.add(ym[:4])

        dt = datetime.strptime(ym, "%Y%m")
        # 4月から翌年3月までが年度
        # 例えば 2025年4月〜2026年3月 は fiscal_year = 2025
        fiscal_year = dt.year if dt.month >= 4 else dt.year - 1
        fiscal_years.add(str(fiscal_year))
    return sorted(fiscal_years)


def format_date(date_str: str, from_format: str, to_format: str) -> Optional[str]:
    """
    日付文字列を指定された形式から別の形式に変換する。

    Args:
        date_str (str): 変換対象の日付文字列
        from_format (str): 元の日付フォーマット（例："%Y年%m月"）
        to_format (str): 変換後のフォーマット（例："%Y-%m"）

    Returns:
        str | None: 変換後の日付文字列（失敗したら None）
    """
    try:
        date_obj = datetime.strptime(date_str, from_format)
        return date_obj.strftime(to_format)
    except ValueError:
        return None


def excel_serial_to_year_month(serial):
    # Excel の基準日（1900-01-01 を 1 として扱う Excel 仕様 ※閏年バグ含む）
    base_date = datetime(1899, 12, 30)
    dt = base_date + timedelta(days=int(serial))
    return f"{dt.year}年{dt.month}月"


def normalize_header(value):
    """列名を 'YYYY年m月' に統一（Windows/Linux 両対応）"""
    try:
        if pd.api.types.is_number(value):
            # Excelシリアル日付 → datetime に変換
            date_value = datetime(1899, 12, 30) + timedelta(days=int(value))
        elif isinstance(value, pd.Timestamp):
            date_value = value
        elif isinstance(value, str):
            # 既に "YYYY年m月"
            if re.match(r"^\d{4}年\d{1,2}月$", value):
                return value
            # "YYYY/mm/dd" 形式など
            date_value = pd.to_datetime(value, errors="raise")
        else:
            return str(value)
        # Windows/Linux 両対応
        return f"{date_value.year}年{date_value.month}月"
    except Exception:
        # 変換失敗時は元値返す
        return str(value)
