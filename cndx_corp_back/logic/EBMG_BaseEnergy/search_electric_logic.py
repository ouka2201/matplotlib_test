import os
import traceback
from datetime import datetime

import pandas as pd
from flask import current_app
from sqlalchemy import case, func, literal, select
from sqlalchemy.sql import over

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_electricity_conversion_entity import MElectricityConversion
from cndx_corp_back.entity.m_heat_supplier_menu_entity import MHeatSupplierMenu


class BaseEnergyElectricLogic:

    @component
    def get_electric_co(self, dict_request_data, logger=None):
        """
        電気事業者_検索
        """
        if logger is None:
            logger = current_app.logger

        # エネルギーの作成年月の終わりの年の翌年のメニューを適応
        target_year = int(dict_request_data["target_year"][0:4]) + 1

        # 電気事業者プルダウン用検索処理
        with get_scoped_session() as session:
            df = top_menus(
                session, dict_request_data["company_name"], target_year, logger
            )

        # 結果格納用List
        electricCoList = df.to_dict(orient="records")
        results: list[dict] = []
        for electricCo in electricCoList:
            if (
                len(results) != 0
                and electricCo["electric_company_reg_no"]
                == results[-1]["electric_company_reg_no"]
            ):
                results[-1]["select_menu"].append(
                    {
                        "menu_no": electricCo["menu_no"],
                        "menu_nm": electricCo["menu_nm"],
                    }
                )
            else:
                results.append(
                    {
                        "electric_co_name": electricCo["electric_supplier_nm"],
                        "electric_company_reg_no": electricCo[
                            "electric_company_reg_no"
                        ],
                        "select_menu": [
                            {
                                "menu_no": electricCo["menu_no"],
                                "menu_nm": electricCo["menu_nm"],
                            }
                        ],
                    }
                )

        return results

    @component
    def get_heat_supplier(self, dict_request_data, logger=None):
        """
        熱供給事業者_検索
        """
        if logger is None:
            logger = current_app.logger

        # エネルギーの作成年月の終わりの年の翌年のメニューを適応
        target_year = int(dict_request_data["target_year"][0:4]) + 1

        # 熱供給事業者プルダウン用検索処理
        with get_scoped_session() as session:
            df = top_menus_heat(
                session, dict_request_data["company_name"], target_year, logger
            )

        # 結果格納用List
        heatList = df.to_dict(orient="records")
        results: list[dict] = []
        for heat in heatList:
            if (
                len(results) != 0
                and heat["heat_supplier_cd"] == results[-1]["heat_supplier_cd"]
            ):
                results[-1]["select_menu"].append(
                    {
                        "menu_no": heat["menu_no"],
                        "menu_name": heat["menu_name"],
                    }
                )
            else:
                results.append(
                    {
                        "heat_supplier_name": heat["heat_supplier_name"],
                        "heat_supplier_cd": heat["heat_supplier_cd"],
                        "select_menu": [
                            {
                                "menu_no": heat["menu_no"],
                                "menu_name": heat["menu_name"],
                            }
                        ],
                    }
                )

        return results


def top_menus(session, company_name, target_year, logger=None) -> pd.DataFrame:
    """
    電力会社・同一メニューごとに 公表回数 が最大の
    レコードだけを取り出す。対象年にヒットしなければ前年で再検索。
    """
    year_int = int(target_year)

    def make_subquery(year):
        # PKごとにpublication_countの降順でcountを付与
        return (
            select(
                MElectricityConversion.electric_company_reg_no,
                MElectricityConversion.electric_supplier_nm,
                MElectricityConversion.menu_no,
                MElectricityConversion.menu_nm,
                MElectricityConversion.residual_flg,
                func.row_number()
                .over(
                    partition_by=[
                        MElectricityConversion.electric_company_reg_no,
                        MElectricityConversion.report_target_year,
                        MElectricityConversion.menu_no,
                    ],
                    order_by=MElectricityConversion.publication_count.desc(),
                )
                .label("no"),
            )
            .where(
                MElectricityConversion.electric_supplier_nm.like(f"%{company_name}%"),
                MElectricityConversion.report_target_year == str(year),
                MElectricityConversion.delete_flg.is_(False),
            )
            .order_by(
                MElectricityConversion.electric_company_reg_no,
                MElectricityConversion.menu_no,
            )
            .subquery()
        )

    def make_stmt(subq):
        # メニュー未設定 → 「標準メニュー」
        # 残差フラグ True → menu_nm + 「（標準メニュー）」
        # それ以外 → 元の menu_nm
        menu_nm_case = case(
            (subq.c.menu_nm == "メニュー未設定", literal("標準メニュー")),
            (
                subq.c.residual_flg.is_(True),
                func.concat(subq.c.menu_nm, "（標準メニュー）"),
            ),
            else_=subq.c.menu_nm,
        ).label("menu_nm")

        return (
            select(
                subq.c.electric_company_reg_no,
                subq.c.electric_supplier_nm,
                subq.c.menu_no,
                menu_nm_case,
            )
            .select_from(subq)
            .where(
                subq.c.no == 1,
                # 「代替値」のメニューは除外
                subq.c.menu_nm != "代替値",
            )
        )

    # target_yearで検索
    subq = make_subquery(year_int)
    stmt = make_stmt(subq)
    logger.info(stmt)
    results = pd.read_sql(stmt, session.connection())

    # ヒットがなければ前年を試す
    if results.empty:
        prev = year_int - 1
        subq = make_subquery(prev)
        stmt = make_stmt(subq)
        logger.info(stmt)
        results = pd.read_sql(stmt, session.connection())

    return results


def top_menus_heat(session, company_name, target_year, logger=None) -> pd.DataFrame:
    """
    熱供給事業者・同一メニューごとに 公表回数 が最大の
    レコードだけを取り出す。対象年にヒットしなければ前年で再検索。
    """
    year_int = int(target_year)

    def make_subquery(year):
        # PKごとにpublication_countの降順でcountを付与
        return (
            select(
                MHeatSupplierMenu.heat_supplier_cd,
                MHeatSupplierMenu.heat_supplier_name,
                MHeatSupplierMenu.menu_no,
                MHeatSupplierMenu.menu_name,
                MHeatSupplierMenu.residual_flg,
                func.row_number()
                .over(
                    partition_by=[
                        MHeatSupplierMenu.heat_supplier_cd,
                        MHeatSupplierMenu.report_year,
                        MHeatSupplierMenu.menu_no,
                    ],
                    order_by=MHeatSupplierMenu.publication_count.desc(),
                )
                .label("no"),
            )
            .where(
                MHeatSupplierMenu.heat_supplier_name.like(f"%{company_name}%"),
                MHeatSupplierMenu.report_year == str(year),
                MHeatSupplierMenu.delete_flg.is_(False),
            )
            .order_by(MHeatSupplierMenu.heat_supplier_cd, MHeatSupplierMenu.menu_no)
            .subquery()
        )

    def make_stmt(subq):
        # メニュー未設定 → 「標準メニュー」
        # 残差フラグ True → menu_name + 「（標準メニュー）」
        # それ以外 → 元の menu_name
        menu_name_case = case(
            (subq.c.menu_name == "メニュー未設定", literal("標準メニュー")),
            (
                subq.c.residual_flg.is_(True),
                func.concat(subq.c.menu_name, "（標準メニュー）"),
            ),
            else_=subq.c.menu_name,
        ).label("menu_name")

        return (
            select(
                subq.c.heat_supplier_cd,
                subq.c.heat_supplier_name,
                subq.c.menu_no,
                menu_name_case,
            )
            .select_from(subq)
            .where(
                subq.c.no == 1,
                # 「代替値」のメニューは除外
                subq.c.menu_name != "代替値",
            )
        )

    # target_yearで検索
    subq = make_subquery(year_int)
    stmt = make_stmt(subq)
    logger.info(stmt)
    results = pd.read_sql(stmt, session.connection())

    # ヒットがなければ前年を試す
    if results.empty:
        prev = year_int - 1
        subq = make_subquery(prev)
        stmt = make_stmt(subq)
        logger.info(stmt)
        results = pd.read_sql(stmt, session.connection())

    return results
