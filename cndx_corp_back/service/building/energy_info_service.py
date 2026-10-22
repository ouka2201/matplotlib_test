import os

import pandas as pd
from flask import abort, current_app

from cndx_corp_back.common.database_manager import build_sql, get_db_engine
from cndx_corp_back.common.decorators import service
from cndx_corp_back.constant.constants import ENERGY_CODE_TO_ENG
from cndx_corp_back.dto.corp.branch_energy_info_dto import BranchEnergyInfoDTO
from cndx_corp_back.utils.dto_utils import include
from cndx_corp_back.utils.utils import get_message


class BuildingEnergyInfoService:

    allowed_key_get = {
        "bank_code",
        "branch_code",
        "corporate_number",
        "fiscal_year",
        "registration_seq",
    }

    @service
    def get_energy_info(self, request_dict: dict, logger=None):
        """
        エネルギー取得
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # 不要なパラメータを除外
        request_dict = include(request_dict, self.allowed_key_get)

        if request_dict.__len__() < 5:
            abort(400, get_message("INCORRECT", item_name="パラメータ"))

        branches_energy_info = self.get_branches_energy_info(request_dict)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return branches_energy_info

    def get_branches_energy_info(self, filters: dict) -> list:

        with get_db_engine().begin() as conn:
            # 支店情報を照会
            columns_br = [
                "area_information",
                "building_id",
                "building_name",
                "industry_category_small",
                "supply_point_number",
                "ep_store_number",
                "customer_number_ep",
                "address",
                "gross_floor_area",
                "electric_power_corporate_name",
                "contracted_power",
                "start_period",
            ]
            sql_branch = build_sql(
                "db_corp.t_cn_application_info", columns_br, filters, "building_id"
            )
            df_branch: pd.DataFrame = pd.read_sql(sql_branch, conn)

            # 建物ID list
            bld_id_list = df_branch["building_id"].tolist()

            # 期初を取得
            start_period = df_branch.at[0, "start_period"]
            start_year_str = start_period[:4]
            start_month_str = start_period[4:6]

            # エネルギー情報を照会
            filters.pop("branch_code")
            columns_en = [
                "building_id",
                "energy_code",
                "year",
                "month",
                "energy_consumption",
            ]
            sql_energy = build_sql(
                "db_corp.t_monthly_building_energy_aggregation",
                columns_en,
                filters,
                "building_id, year, month",
            )
            df_energy: pd.DataFrame = pd.read_sql(sql_energy, conn)

            # エネルギーコードを論理名にする
            df_energy["energy_code"] = df_energy["energy_code"].apply(
                lambda x: ENERGY_CODE_TO_ENG[x]
            )

            df_energy["year"] = df_energy["year"].astype(int)
            df_energy["month"] = df_energy["month"].astype(int)

            # 順番崩れないようにデータがない月分に対して0で補足
            year_int = int(start_year_str)
            month_int = int(start_month_str)
            for i in range(12):
                for bid in bld_id_list:
                    # 対象月のレコードが1つでもない場合
                    condition = (
                        (df_energy["building_id"] == bid)
                        & (df_energy["year"] == year_int)
                        & (df_energy["month"] == month_int)
                    )
                    if not condition.any():
                        new_row = pd.DataFrame(
                            [
                                {
                                    "building_id": bid,
                                    "energy_code": "electric_power",
                                    "year": year_int,
                                    "month": month_int,
                                    "energy_consumption": 0,
                                }
                            ]
                        )

                        df_energy = pd.concat([df_energy, new_row], ignore_index=True)

                month_int += 1
                if month_int > 12:
                    month_int = month_int % 12
                    year_int += 1

            df_pivot = df_energy.pivot(
                index=["building_id", "energy_code"],
                columns=["year", "month"],
                values="energy_consumption",
            )

            df_pivot = df_pivot.sort_index(axis=1, level=[0, 1])

            prev_bid = None
            branches_energy_info = []
            for (bid, energy_code), row in df_pivot.iterrows():

                if bid != prev_bid:
                    # 作業中の支店情報を切換
                    curr_branch_dict = {}
                    # 支店情報をの中身を作成
                    curr_branch_dict["energy_usage_info"] = {}
                    curr_branch_dict["basic_info"] = (
                        df_branch.loc[df_branch["building_id"] == bid].iloc[0].to_dict()
                    )
                    # 期初の年度と月別
                    curr_branch_dict["basic_info"].pop("start_period")
                    curr_branch_dict["basic_info"]["start_year"] = start_period[:4]
                    curr_branch_dict["basic_info"]["start_month"] = start_period[4:6]
                    curr_branch_dict["basic_info"].pop("building_id")

                    branches_energy_info.append(curr_branch_dict)
                    # 処理した件の id を覚えておく
                    prev_bid = bid

                curr_branch_dict["energy_usage_info"][energy_code] = row.to_list()
        return branches_energy_info
