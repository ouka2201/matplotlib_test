import os
from re import match

import pandas as pd
from flask import current_app

import cndx_corp_back.logic.EBMG_BaseEnergy.auto_entry_logic as AutoEntryLogic
from cndx_corp_back.common.decorators import service
from cndx_corp_back.dto.EBMG.energy_auto_entry_in_dto import (
    EnergyAutoEntryIn,
)
from cndx_corp_back.logic.EBMG_BaseEnergy.Inquiry_logic import BaseEnergyInquiryLogic
from cndx_corp_back.logic.EBMG_BaseEnergy.search_electric_logic import (
    BaseEnergyElectricLogic,
)


class BaseEnergyInquiryService:

    @service
    def get_base_energy_info(self, request_dict: dict, user_context, logger=None):
        """
        エネルギーデータ登録編集画面初期表示処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        logic = BaseEnergyInquiryLogic()
        # 産業分類マスタ
        minor, detail = logic.get_industry_classification_mst()
        # 都市ガスマスタ
        city_gas = logic.get_city_gas_heating_value_mst()
        # 熱マスタ
        heat = logic.get_heat_supplier_menu_mst()

        # 既に登録されたデータがある場合
        if request_dict.get("entry_draft_flag"):
            # 建物情報から取得
            results: list[dict] = logic.inquiry_building_info_map(
                user_context, request_dict=request_dict
            )
        elif (
            request_dict.get("entry_draft_flag") == ""
            or request_dict.get("entry_draft_flag") is None
        ):
            # 建物マスタから取得
            results: list[dict] = logic.inquiry_building_mast_map(
                user_context, request_dict=request_dict
            )

        result = {
            "industry_class_minor": minor,
            "industry_class_detail": detail,
            "city_gas": city_gas,
            "heat_supplier": heat,
            "buildings": results,
        }
        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result

    @service
    def search_electric_co(self, request_dict: dict, logger=None):
        """
        電気事業者検索サービス
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 電気事業者検索
        results = BaseEnergyElectricLogic.get_electric_co(self, request_dict)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return results

    @service
    def search_heat_supplier(self, request_dict: dict, logger=None):
        """
        熱供給事業者検索サービス
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 熱供給事業者検索
        results = BaseEnergyElectricLogic.get_heat_supplier(self, request_dict)

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return results

    @service
    def get_city_gas_list(self, logger=None):
        """City gas supplier master list."""
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} get_city_gas_list start")

        logic = BaseEnergyInquiryLogic()
        results = logic.get_city_gas_heating_value_mst()

        logger.info(f"{os.path.basename(__file__)} get_city_gas_list end")
        return results

    @service
    def get_heat_supplier_list(self, logger=None):
        """Heat supplier master list."""
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} get_heat_supplier_list start")

        logic = BaseEnergyInquiryLogic()
        results = logic.get_heat_supplier_menu_mst()

        logger.info(f"{os.path.basename(__file__)} get_heat_supplier_list end")
        return results

    @service
    def get_base_energy_auto30(self, indto: EnergyAutoEntryIn, logger=None):
        """
        電力30分値エネルギーデータ月別取得処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 12ヶ月分繰り返しで取得した30分値データ
        results = []
        results, flag = AutoEntryLogic.monthly_sums(indto, 12)

        if flag is True:
            result = {
                "unit": "千kWh",
                "electricity_data": results,
            }
        else:
            result = {
                "unit": "kWh",
                "electricity_data": results,
            }

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return result
