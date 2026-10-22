import calendar
import io
import os
import statistics
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import fitz  # PyMuPDF
import numpy as np
import pandas as pd
import tableauserverclient as TSC
from flask import abort, current_app
from sqlalchemy import and_, func, select
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common import constants_values
from cndx_corp_back.common.constants_values import ReportStatus, ReportTypeValue
from cndx_corp_back.common.database_manager import get_db_engine, get_scoped_session
from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.dto.report.cn_karte_create_vis_in_dto import (
    CreateCnKarteVisInDto as VisInDto,
)
from cndx_corp_back.dto.report.create_cn_karte_in_dto import CreateCnKarteInDto as InDto
from cndx_corp_back.dto.report.electricity_vis_create_in_dto import (
    ElectricityVisCreateInDto as ElcInDto,
)
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_building_group_entity import MBuildingGroup
from cndx_corp_back.entity.m_prefecture_entity import PrefectureMst
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_cn_ranking_snapshot import TCnRankingSnapshot
from cndx_corp_back.entity.t_cn_report_snapshot_entity import TCnReportSnapshot
from cndx_corp_back.entity.t_electricity_vis_flg_snapshot_entity import (
    TElectricityVisFlgSnapshot,
)
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.entity.v_ep_30min_energy_long_entity import t_v_ep_30min_energy_long
from cndx_corp_back.m_building_group_entity import MBuidingGroup
from cndx_corp_back.query.query_mst import QueryMst
from cndx_corp_back.utils.utils import get_message, get_query


@dataclass
class CreationInfo:
    creation_id: str
    datasource_name: str
    dataframe: pd.DataFrame
    building_id: str
    hyper_path: str
    file: FileStorage
    pages: list[bytes]
    stream: io.BytesIO
    preview: FileStorage
    png_bytes: bytes


class ReportCreateComponent:
    """
    CNレポート作成コンポーネント

    機能切り替え:
    - use_postgres_storage: True = PostgreSQL保存, False = Hyper+Tableau（従来版）
    """

    site_name = ""

    def __init__(self, creation_id: str, use_postgres_storage=False, logger=None):
        """
        初期化
        Args:
            creation_id: 作成識別子
            logger: ログ出力インスタンス
            use_postgres_storage: True=PostgreSQL保存, False=Hyper+Tableau
        """
        if logger is None:
            logger = current_app.logger
        self.log = logger
        self.use_postgres_storage = use_postgres_storage

        # Tableau Server の認証情報
        self.server_url = current_app.config["TABLEAU_SERVER_URL"]
        self.username = current_app.config["TABLEAU_USERNAME"]
        self.password = current_app.config["TABLEAU_PASSWORD"]
        self.dashboard_name_list = None
        self.creation_id_seed = creation_id
        self.creation_infos: list[CreationInfo] = []

    @component
    @log_time
    def create_cn_karte(
        self, dto: InDto | VisInDto | ElcInDto, login_org_id, user_id, logger
    ) -> list[CreationInfo]:
        """
        CNカルテ作成
            :param dto: 型：地銀の場合は`InDto`、可視化の場合は`VisInDto`、見える化は`ElcInDto`
            :return files: 作成したレポートのリスト
        """

        self.log.info(f"{os.path.basename(__file__)}処理開始。")

        # ==== 1 抽出 ====

        filter_months = None

        with get_scoped_session() as session:

            # CNレポート
            if isinstance(dto, (InDto, VisInDto)):
                # 抽出条件
                main_filter, additional = self._get_filter_dict_cn(dto)

                # df 取得
                self._get_df_cn(dto, main_filter, additional, session)

                # log 用レポート名
                self.report_name = "cn_profile"

            # 電力見える化レポート
            elif isinstance(dto, ElcInDto):
                # 抽出条件
                main_filter = self._get_filter_dict_elc(dto)

                # df 取得
                self._get_df_elc(dto, main_filter)

                # log 用レポート名
                self.report_name = "elct_vis"
            else:
                pass

        # ==== 2 データ保存方法選択 ====
        self._save_to_postgres(dto, login_org_id, user_id, logger)

        return self.creation_infos

    # @log_time
    def _get_filter_dict_cn(self, dto: InDto | VisInDto):
        """
        フィルタを用意
            :param dto: 地銀の場合は `InDto`, 可視化側の場合は `VisInDto`
            :return filter_dict: 主要条件
            :return additional_list: 追加条件リスト
        """
        filter_dict = {}

        filter_dict["org_id"] = dto.org_id

        filter_dict["corporate_number"] = dto.corporate_number

        if isinstance(dto, InDto):

            filter_dict["registration_seq"] = dto.registration_seq

            common_part = f" AND agreement_category = '{dto.agreement_category}' "

            addtional_list = []
            addtional_list.append(
                f" AND fiscal_year = '{dto.fiscal_year}' {common_part}"
            )
            addtional_list.append(
                f" AND fiscal_year = '{int(dto.fiscal_year) -1}' {common_part}"
            )

            self.cn_month_seq_dict = _get_month_dict(4)
            """月の順序 for CNカルテ"""

        elif isinstance(dto, VisInDto):

            # 可視化の場合、固定値
            filter_dict["registration_seq"] = 0

            # 対象月を計算 （可視化側無条件）
            months = []
            months_previous = []  # 前年度

            year = int(dto.start_year)
            month = int(dto.start_month)

            self.cn_month_seq_dict = _get_month_dict(month)
            """月の順序 for CNカルテ"""

            for i in range(12):

                month_str = str(month).zfill(2)

                months.append(f"{year}{month_str}")
                months_previous.append(f"{year-1}{month_str}")

                month += 1

                if month > 12:
                    year += 1
                    month -= 12

            addtional_list = []
            addtional_list.append(
                f""" AND "target_year_month" IN ('{"', '".join(months)}') """
            )
            addtional_list.append(
                f""" AND "target_year_month" IN ('{"', '".join(months_previous)}') """
            )

            # グループ絞り条件
            if dto.group_for_multibuilding:
                for g in dto.group_for_multibuilding:
                    addtional_list[
                        0
                    ] += f""" AND "group{g.group_no}" = ('{g.option_no}') """
                    addtional_list[
                        1
                    ] += f""" AND "group{g.group_no}" = ('{g.option_no}') """

            # 単拠点の場合の id リスト
            if dto.building_ids_for_single:
                addtional_list[
                    0
                ] += f""" AND "building_id" IN ('{"', '".join(dto.building_ids_for_single)}') """
                addtional_list[
                    1
                ] += f""" AND "building_id" IN ('{"', '".join(dto.building_ids_for_single)}') """

            addtional_list[
                0
            ] += f""" AND "agreement_category" = '{dto.agreement_category}' """
            addtional_list[
                1
            ] += f""" AND "agreement_category" = '{dto.agreement_category}' """

        else:
            self.log.error("サポートしていない入力")
            abort(500)

        return filter_dict, addtional_list

    # @log_time
    def _get_df_cn(
        self,
        dto,
        view_filter_dict: dict,
        additional_list: list[str],
        session: scoped_session,
    ) -> list[CreationInfo]:
        """
        DF取得CNカルテ作成用
            :param dto: request DTO
            :return df: 作成用 Dataframe
        """

        # 当年度 ビュー DataFrame

        # 当年度 query
        query = get_query(
            QueryMst.CN_KARTE_VIEW,
            additional_condition=additional_list[0],
            **view_filter_dict,
        )

        # 前年度 query
        query_1 = get_query(
            QueryMst.CN_KARTE_VIEW,
            additional_condition=additional_list[1],
            **view_filter_dict,
        )

        with get_db_engine().connect() as conn:

            # 当年度の Dataframe
            df = pd.read_sql(query, conn)

            # DataFrame が空の場合はエラー
            if df is None or df.empty:
                abort(400, description=get_message("BUILDING_INFO_NOT_EXSIT"))

            if isinstance(dto, (InDto, VisInDto)):
                dto.agreement_category = df["agreement_category"][0]
            df = df.drop_duplicates(
                subset=[
                    "corporate_number",
                    "agreement_category",
                    "org_id",
                    "building_id",
                    "fiscal_year",
                    "registration_seq",
                    "energy_code",
                    "target_year_month",
                    "supplier_reg_no",
                ],
                keep="first",  # 最初を残す。last なら最後を残す
            )
            # ランキング計算
            new_df = pd.DataFrame()
            if isinstance(dto, VisInDto) and dto.building_ids_for_single:
                for bid in dto.building_ids_for_single:
                    filtered_df = df.loc[df["building_id"] == bid]
                    calc_df = _calc_ranking_cn(filtered_df)
                    new_df = pd.concat([new_df, calc_df], ignore_index=True)
            else:
                new_df = _calc_ranking_cn(df)
            df = new_df

            # フラグ付け
            df["year_flg"] = "1"
            df["month_flg"] = (
                df["target_year_month"].str[4:6].map(self.cn_month_seq_dict)
            )

            # 前年度の Dataframe
            df_past_year = pd.read_sql(query_1, conn)

            # DataFrame が空でない場合、df に追加
            if not df_past_year.empty:

                df_past_year = df_past_year.drop_duplicates(
                    subset=[
                        "corporate_number",
                        "agreement_category",
                        "org_id",
                        "building_id",
                        "fiscal_year",
                        "registration_seq",
                        "energy_code",
                        "target_year_month",
                        "supplier_reg_no",
                    ],
                    keep="first",  # 最初を残す。last なら最後を残す
                )
                unique_month_count = df_past_year["target_year_month"].nunique()
                if unique_month_count == 12:

                    # フラグ付け
                    df_past_year["year_flg"] = "2"
                    df_past_year["month_flg"] = (
                        df_past_year["target_year_month"]
                        .str[4:6]
                        .map(self.cn_month_seq_dict)
                    )

                    # ランキングを0に
                    df_past_year["energy_ranking"] = 0
                    df_past_year["energy_ranking_name"] = None

                    df = pd.concat([df, df_past_year], ignore_index=True)

        df["group_condition_1"] = None
        df["group_condition_2"] = None

        # TODO グループ名に
        if isinstance(dto, VisInDto) and dto.group_for_multibuilding:
            group_settings = None

            # グループの場合
            if len(dto.group_for_multibuilding) >= 1:
                creation_id = self.creation_id_seed + "_1"
                self.creation_infos.append(
                    CreationInfo(
                        creation_id=creation_id,
                        datasource_name=current_app.config["TABLEAU_DATASOURCE_NAME"],
                        dataframe=df,
                        building_id="1",
                        hyper_path=None,
                        file=None,
                        pages=None,
                        stream=None,
                        preview=None,
                        png_bytes=None,
                    )
                )
                g_no1 = dto.group_for_multibuilding[0].group_no
                o_no1 = dto.group_for_multibuilding[0].option_no
                group_settings = (
                    session.query(MBuidingGroup)
                    .filter(
                        MBuidingGroup.corporate_number == dto.corporate_number,
                        # MBuidingGroup.org_id == dto.org_id,
                        MBuidingGroup.agreement_category == dto.agreement_category,
                    )
                    .all()
                )
                for g in group_settings:
                    if g.group_id == g_no1:
                        df["group_condition_1"] = getattr(g, "select_item" + o_no1)
                        break
            if len(dto.group_for_multibuilding) >= 2:
                g_no2 = dto.group_for_multibuilding[1].group_no
                o_no2 = dto.group_for_multibuilding[1].option_no

                for g in group_settings:
                    if g.group_id == g_no2:
                        df["group_condition_2"] = getattr(g, "select_item" + o_no2)
                        break
        # 単拠点の場合
        elif isinstance(dto, VisInDto) and dto.building_ids_for_single:
            for bid in dto.building_ids_for_single:
                creation_id = f"{self.creation_id_seed}_{bid}"
                info = CreationInfo(
                    creation_id=creation_id,
                    datasource_name=current_app.config["TABLEAU_DATASOURCE_NAME"],
                    dataframe=df.loc[df["building_id"] == bid],
                    building_id=bid,
                    hyper_path=None,
                    file=None,
                    pages=None,
                    stream=None,
                    preview=None,
                    png_bytes=None,
                )
                self.creation_infos.append(info)
        # 企業全体の場合
        if not self.creation_infos:
            creation_id = self.creation_id_seed + "_0"
            self.creation_infos.append(
                CreationInfo(
                    creation_id=creation_id,
                    datasource_name=current_app.config["TABLEAU_DATASOURCE_NAME"],
                    dataframe=df,
                    building_id="0",
                    hyper_path=None,
                    file=None,
                    pages=None,
                    stream=None,
                    preview=None,
                    png_bytes=None,
                )
            )

        # 識別子
        df["creation_id"] = self.creation_id_seed

    # @log_time
    def _refresh_for_pg(self, server: TSC.Server, dto):

        # 全てのデータソースを取得
        all_datasources, pag = server.datasources.get()

        datasouce_name = None
        datasouce_name_electric_col = None
        datasouce_name_electric_row = None

        if isinstance(dto, (InDto, VisInDto)):
            # CNカルテデータソース抽出
            datasouce_name = os.getenv("CnProfileDataSourceName_value")
        elif isinstance(dto, ElcInDto):
            # 電力見えるかデータソース抽出
            datasouce_name_electric_row = os.getenv(
                "ElectricPowerDataSourceName_value_row"
            )
            datasouce_name_electric_col = os.getenv(
                "ElectricPowerDataSourceName_value_col"
            )

        for ds in all_datasources:

            if datasouce_name is not None and ds.name == datasouce_name:
                # 抽出
                before_ms = datetime.now()
                job = server.datasources.refresh(datasource_item=ds, incremental=True)
                server.jobs.wait_for_job(job.id, timeout=3600)
                after_ms = datetime.now()

                break

            if (
                datasouce_name_electric_col is not None
                and ds.name == datasouce_name_electric_col
            ):
                # 抽出
                before_ms = datetime.now()
                job = server.datasources.refresh(datasource_item=ds, incremental=True)
                server.jobs.wait_for_job(job.id, timeout=3600)
                after_ms = datetime.now()

            if (
                datasouce_name_electric_row is not None
                and ds.name == datasouce_name_electric_row
            ):
                # 抽出
                before_ms = datetime.now()
                job = server.datasources.refresh(datasource_item=ds, incremental=True)
                server.jobs.wait_for_job(job.id, timeout=3600)
                after_ms = datetime.now()

                self.log.info(
                    f"datasource refresh time consumption: {after_ms - before_ms}"
                )

        if not job:
            self.log.error("datasource not found")
            raise (500)

    # @log_time
    def _get_pages_list_postgres(
        self, dto: InDto | VisInDto | ElcInDto, server: TSC.Server
    ):

        # ビュー（ダッシュボード）の検索
        all_workbooks, _ = server.workbooks.get()

        self.log.info(f"self.workbook_name：★★{self.workbook_name}")
        target_workbook = next(
            wb for wb in all_workbooks if wb.name == self.workbook_name
        )

        server.workbooks.populate_views(target_workbook)

        # PDF印字オプション設定
        pdf_req_option = TSC.PDFRequestOptions()

        # ページタイプ
        pdf_req_option.page_type = TSC.PDFRequestOptions.PageType.A4

        pdf_req_option.parameter(name="locale", value="ja-jp")

        # 全ての対象ビューを取得 TODO 性能最適化
        target_views = {v_nm: None for v_nm in self.dashboard_name_list}
        for view_name in target_workbook.views:
            if view_name.name in target_views:
                target_views[view_name.name] = view_name

        for cinfo in self.creation_infos:

            if isinstance(dto, ElcInDto):
                # 横向き
                pdf_req_option.orientation = TSC.PDFRequestOptions.Orientation.Landscape

            option = deepcopy(pdf_req_option)
            option.vf("Creation_Id_K", cinfo.creation_id)
            option.vf("Creation_Id_R", cinfo.creation_id)

            if isinstance(dto, VisInDto) and dto.building_ids_for_single:
                option.vf("building_id", cinfo.building_id)
            if isinstance(dto, VisInDto) and dto.group_for_multibuilding:
                for g in dto.group_for_multibuilding:
                    option.vf("group" + g.group_no, g.option_no)

            cinfo.pages = self._get_pages(target_views, option, server)

    # @log_time
    def _get_pages(
        self,
        views: dict[str, TSC.ViewItem],
        pdf_option: TSC.PDFRequestOptions,
        server: TSC.Server,
    ) -> list[bytes]:
        """
        1つのレポートの pdf ページ・リストを返す
            :param views: ビュー リスト
            :param pdf_option: 作成用情報
            :param server: Tablue Server
        """

        pdf_pages = []

        for target_view in views.values():

            # レポートのデータを取得
            server.views.populate_pdf(target_view, pdf_option)

            # 結果の PDF をエクスポート
            pdf_bytes = target_view.pdf
            pdf_pages.append(pdf_bytes)

        return pdf_pages

    # @log_time
    def _get_creation_conf_cn(self, dto: InDto | VisInDto):

        self.dashboard_name_list = [
            "CNカルテ_P1",  # title
            "CNカルテ_P2",  # pie chart
            "CNカルテ_P5",  # ZEB raida
            "CNカルテ_P3",  # single table
            "CNカルテ_P4",  # multiple table
        ]

        # 拠点数判別
        # self.creation_infosから最初のDataFrameを取得
        if not self.creation_infos:
            self.log.error("creation_infosが空です")
            abort(500, "データが見つかりません")

        df: pd.DataFrame = self.creation_infos[0].dataframe

        office_count = df["building_id"].nunique()

        if office_count <= 0:
            self.log.error("事業所数が1以上である必要があります。")
            abort(500, "事業所数が1以上である必要があります。")

        # 拠点数区別
        if office_count <= 1 or (
            isinstance(dto, VisInDto) and dto.building_ids_for_single
        ):
            self.dashboard_name_list.pop(4)  # 単一拠点版はP4を除外
            if self.use_postgres_storage:
                self.workbook_name = os.getenv("CnProfileReportFormatName_value_single")
            else:
                self.workbook_name = (
                    constants_values.CnProfileReportFormatName.STAGING_SINGLE.value
                )

        else:
            self.dashboard_name_list.pop(3)  # 複数拠点版はP3を除外
            if self.use_postgres_storage:
                self.workbook_name = os.getenv(
                    "CnProfileReportFormatName_value_multiple"
                )
            else:
                self.workbook_name = (
                    constants_values.CnProfileReportFormatName.STAGING_MULTIPLE.value
                )

        # 可視化かつ標準版以外の場合、P5を除外
        if isinstance(dto, VisInDto):
            creation_format_raw = (getattr(dto, "creation_format", "") or "").strip()
            normalized_creation_format = creation_format_raw
            if creation_format_raw.isdigit():
                normalized_creation_format = creation_format_raw.lstrip("0") or "0"
            is_standard_format = (
                normalized_creation_format
                == constants_values.FormatTypeCode.STANTARD.value
                or getattr(dto, "format_type_code", None) in ("1", "01")
                or "標準" in creation_format_raw
            )
            if not is_standard_format and "CNカルテ_P5" in self.dashboard_name_list:
                self.dashboard_name_list.remove("CNカルテ_P5")
        else:
            self.dashboard_name_list.remove("CNカルテ_P5")

    # @log_time
    def _get_creation_conf_elct(self):

        self.dashboard_name_list = [
            "おもて",
            "うら",
        ]
        self.workbook_name = os.getenv("ElectricPowerReportFormatName_value")

    # @log_time
    def _to_pdf(self, pdf_pages: list[bytes]) -> io.BytesIO:

        pdf_stream = io.BytesIO()
        pdf_doc = fitz.open()  # 新しいPDFドキュメントを作成

        for page in pdf_pages:
            page_pdf = fitz.open("pdf", page)
            pdf_doc.insert_pdf(page_pdf)
            page_pdf.close()

        pdf_doc.save(
            pdf_stream,
            incremental=False,
            garbage=4,
            deflate=True,
            clean=True,
        )

        pdf_doc.close()
        pdf_stream.seek(0)

        return pdf_stream

    # @log_time
    def _get_filter_dict_elc(self, dto: ElcInDto):
        """
        フィルタを用意 for 電力見える化
            :param dto: ElectricityVisCreateInDto
            :return filter_dict: 主要条件
        """
        filter_dict = dto.model_dump()

        filter_dict.pop("contracted_power")
        month_from = filter_dict.pop("month_from")
        year_from = filter_dict.pop("fiscal_year")
        start_date = year_from + month_from
        d = date(int(year_from), int(month_from), 1)
        end_data = self.add_months(d, 12)
        filter_dict["date_from"] = start_date
        filter_dict["date_to"] = end_data.strftime("%Y%m")
        filter_dict["org_id"] = "TEP"

        return filter_dict

    def add_months(self, d, months):
        year = d.year + (d.month + months - 1) // 12
        month = (d.month + months - 1) % 12 + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    # @log_time
    def _get_df_elc(self, dto: ElcInDto, view_filter_dict):
        """
        DF取得 for 電力見える化
            :param dto: request DTO
            :return: None (データはself.creation_infosに保存)
        """

        # query
        query = get_query(QueryMst.ELEC_VIS, **view_filter_dict)

        with get_db_engine().connect() as conn:

            # Dataframe 取得
            raw_df = pd.read_sql(query, conn)

            # DataFrame が空の場合はエラー
            if raw_df is None or raw_df.empty:
                self.log.error("30分値データが見つかりませんでした。")
                abort(400, description=get_message("BUILDING_INFO_NOT_EXSIT"))

        raw_df: pd.DataFrame = self.create_flag_for_report(raw_df, dto)

        raw_df["contracted_power"] = dto.contracted_power

        time_dict = {
            f"v30min_used_energy_{str(i+1)}": f"{i//2}_{str(30*(i%2)).zfill(2)}"
            for i in range(48)
        }

        raw_df = raw_df.rename(columns=time_dict)

        # 作成用データ特定用情報
        raw_df["creation_id"] = self.creation_id_seed

        col_df = raw_df.melt(
            id_vars=[
                "acquisition_date",
                "agreement_category",
                "org_id",
                "building_id",
                "corp_number",
                "corp_name",
                "building_name",
                "supply_point_number",
                "ep_customer_number",
                "missing_time_range_count",
                "invalid_time_range_count",
                "company_id",
                "delete_flg",
                "created_by",
                "created_at",
                "building_address_prefecture",
                "building_address_city",
                "jp_code_name",
                "building_address",
                "contracted_power",
                "creation_id",
                "report_weeks",
                "report_max_day",
                "report_max_week",
                "report_max_frequency",
                "report_target_month",
            ],
            value_vars=time_dict.values(),
            var_name="time",
            value_name="value",
        )

        # CreationInfoリストに保存
        # 電力見える化では常に_0のcreation_idを使用
        creation_id = f"{self.creation_id_seed}_0"
        creation_info_dict = {
            "electric_power_datasource_step3_row": {"dataframe": raw_df},
            "electric_power_datasource_step3_col": {"dataframe": col_df},
        }
        # row形式とcol形式の両方のDataFrameを保存（col形式をメインとして使用）
        self.creation_infos.append(
            CreationInfo(
                creation_id=creation_id,
                datasource_name="electric_power_datasource_step3_row",
                dataframe=raw_df,
                building_id=dto.building_id,
                hyper_path="",
                file=None,
                pages=None,
                stream=None,
                preview=None,
                png_bytes=None,
            )
        )
        self.creation_infos.append(
            CreationInfo(
                creation_id=creation_id,
                datasource_name="electric_power_datasource_step3_col",
                dataframe=col_df,
                building_id=dto.building_id,
                hyper_path="",
                file=None,
                pages=None,
                stream=None,
                preview=None,
                png_bytes=None,
            )
        )

        # 必要に応じてrow形式も別途保存可能（現在は使用しない）
        # 今後row形式も必要な場合は別のCreationInfoとして追加

    # @log_time
    def create_flag_for_report(self, df: pd.DataFrame, dto: ElcInDto) -> pd.DataFrame:
        """レポート用の電力値フラグ追加"""
        # df = df.astype(str)

        # 電力値取得
        df_value = df.drop(
            columns=[
                "acquisition_date",
                "agreement_category",
                "org_id",
                "updated_by",
                "updated_at",
                "building_id",
                "corp_number",
                "corp_name",
                "building_name",
                "supply_point_number",
                "ep_customer_number",
                "missing_time_range_count",
                "invalid_time_range_count",
                "company_id",
                "delete_flg",
                "created_by",
                "created_at",
                "building_address_prefecture",
                "building_address_city",
                "jp_code_name",
                "building_address",
            ]
        )

        df_value_num = df_value.select_dtypes(include="number")
        # 最大値行取得
        row_max = df_value_num.max(axis=1)

        # # 全データ一行にする
        # values_flat = df_value.max(axis=1).values.flatten()

        # report_weeks：取得年月日のもと、日曜0、月曜1...土曜6のフラグ設定
        df["acquisition_date"] = pd.to_datetime(df["acquisition_date"], format="%Y%m%d")
        df["report_weeks"] = (df["acquisition_date"].dt.weekday + 1) % 7
        # =================================================================================
        # report_max_day：最大電力数值のレコードへフラグ設定（最小日のみ）

        global_max = row_max.max()
        max_rows = df[row_max == global_max]
        # 最小日付マーク
        target_index = max_rows["acquisition_date"].idxmin()
        # デフォールト値設置して、最大値フラグ1設定
        df["report_max_day"] = 0
        df.loc[target_index, "report_max_day"] = 1
        # =================================================================================
        # report_max_week：最大電力値のその周はフラグ1設定
        # 最小日絞り
        # 日付型変換（dfは acquisition_date が 'YYYYMMDD' 文字列想定）
        df["acquisition_date_dt"] = pd.to_datetime(
            df["acquisition_date"], format="%Y%m%d"
        )

        # 対象日（最大電力値の最小日など）
        target_date = pd.to_datetime(
            max_rows["acquisition_date"].min(), format="%Y%m%d"
        )

        # データ範囲
        data_min = df["acquisition_date_dt"].min()
        data_max = df["acquisition_date_dt"].max()

        # 1) まず日曜〜土曜の週を計算（必ず7日）
        # pandas weekday: Mon=0 ... Sun=6
        weekday_sun0 = (target_date.weekday() + 1) % 7  # Sun=0 ... Sat=6
        week_start = target_date - pd.Timedelta(days=weekday_sun0)  # Sunday
        week_end = week_start + pd.Timedelta(days=6)  # Saturday

        # 2) その週がデータ範囲からはみ出して「7日分そろわない」場合は補正
        #   - 週の開始がデータ最小日より前なら、開始をdata_minに寄せて7日
        #   - 週の終了がデータ最大日より後なら、終了をdata_maxに寄せて7日
        #   ※データが7日未満の場合は、可能な範囲だけ1にする
        span_days = (data_max - data_min).days + 1

        if span_days >= 7:
            if week_start < data_min:
                week_start = data_min.normalize()
                week_end = week_start + pd.Timedelta(days=6)
            if week_end > data_max:
                week_end = data_max.normalize()
                week_start = week_end - pd.Timedelta(days=6)
        else:
            # データ自体が7日未満なら、全期間を対象にする（7日を作れないため）
            week_start = data_min.normalize()
            week_end = data_max.normalize()

        # 3) フラグ付け（この範囲を1）
        df["report_max_week"] = (
            df["acquisition_date_dt"].between(week_start, week_end).astype(int)
        )

        # 補助列削除
        df = df.drop(columns=["acquisition_date_dt"])
        # =================================================================================
        # report_max_frequency：最大電力値のトップ50のうち、50番目の値を基準にして、各データがその値を超えていれば 1 を足す
        # 50個目の電力値取得
        # 1) DBから対象キーで絞り込みして取得
        with get_scoped_session() as session:
            stmt = select(
                t_v_ep_30min_energy_long.c.corp_number,
                t_v_ep_30min_energy_long.c.agreement_category,
                t_v_ep_30min_energy_long.c.org_id,
                t_v_ep_30min_energy_long.c.building_id,
                t_v_ep_30min_energy_long.c.corp_name,
                t_v_ep_30min_energy_long.c.building_name,
                t_v_ep_30min_energy_long.c.ep_customer_number,
                t_v_ep_30min_energy_long.c.supply_point_number,
                t_v_ep_30min_energy_long.c.acquisition_date,
                t_v_ep_30min_energy_long.c.time_slot,
                t_v_ep_30min_energy_long.c.time_label,
                t_v_ep_30min_energy_long.c.electric_power_value,
            ).where(
                and_(
                    t_v_ep_30min_energy_long.c.corp_number == dto.corporate_number,
                    t_v_ep_30min_energy_long.c.agreement_category
                    == dto.agreement_category,
                    # t_v_ep_30min_energy_long.c.org_id == dto.org_id,
                    t_v_ep_30min_energy_long.c.building_id == dto.building_id,
                )
            )

            rows = session.execute(stmt).mappings().all()
        df_max_frequency = pd.DataFrame(rows)
        if df_max_frequency.empty:
            df_max_frequency["report_max_frequency"] = []
            return df_max_frequency

        # 2) acquisition_date を文字列として扱う（YYYYMMDD前提）
        #    すでに int の場合でも比較は文字列の方が安全
        df_max_frequency["acquisition_date"] = df_max_frequency[
            "acquisition_date"
        ].astype(str)

        # 3) 数値化（念のため）
        df_max_frequency["electric_power_value"] = pd.to_numeric(
            df_max_frequency["electric_power_value"], errors="coerce"
        )

        # 4) ソート：electric_power_value 降順、acquisition_date 昇順
        df_sorted_max_frequency = df_max_frequency.sort_values(
            ["electric_power_value", "acquisition_date"],
            ascending=[False, True],
            kind="mergesort",
        )

        # 5) 先頭50件を抽出（上位50）
        top50 = df_sorted_max_frequency.head(50).copy()

        # 6) top50内で acquisition_date を集計（同じ日付は件数を数える）
        #    → 各行に「その日の件数」を持たせる
        freq_by_date = top50["acquisition_date"].value_counts()  # Series: date -> count
        top50["report_max_frequency"] = (
            top50["acquisition_date"].map(freq_by_date).astype(int)
        )

        # 7) 元dfに report_max_frequency を追加（top50に入った行だけ値を入れ、それ以外は0）
        df_max_frequency["report_max_frequency"] = 0

        # 行を特定するキー（同一buildingで time_slot がユニーク想定）
        # ※もしDB的にユニークキーがあるならそれを使うのがベスト
        key_cols = ["acquisition_date"]

        top50_key = top50[key_cols].copy()
        top50_key["report_max_frequency"] = top50["report_max_frequency"].values
        top50_key = top50_key.drop_duplicates(subset=["acquisition_date"], keep="first")

        # 年月日を文字列に
        df["acquisition_date"] = df["acquisition_date"].dt.strftime("%Y%m%d")
        df["report_target_month"] = (
            df["acquisition_date"].str.startswith(dto.target_month).astype(int)
        )
        df = df.merge(top50_key, on="acquisition_date", how="left")

        df["report_max_frequency"] = df["report_max_frequency"].fillna(0).astype(int)

        # =================================================================================

        # 1) report_max_target_month を初期化
        df_sorted = df.copy()
        df_sorted["report_max_target_month"] = 0

        # 2) 対象月（report_target_month==1）の行だけを対象とする
        mask_target = df_sorted["report_target_month"].eq(1)
        if mask_target.sum() == 0:
            return df_sorted

        # 3) acquisition_date を datetime にする（すでに datetime ならそのまま）
        if not pd.api.types.is_datetime64_any_dtype(df_sorted["acquisition_date"]):
            df_sorted["acquisition_date"] = pd.to_datetime(
                df_sorted["acquisition_date"].astype(str),
                format="%Y%m%d",
                errors="coerce",
            )

        # 4) electric_power_value が無い場合は作る（最大30分値）
        if "electric_power_value" not in df_sorted.columns:
            vcols = [f"v30min_used_energy_{i}" for i in range(1, 49)]
            df_sorted[vcols] = df_sorted[vcols].apply(pd.to_numeric, errors="coerce")
            df_sorted["electric_power_value"] = df_sorted[vcols].max(axis=1)

        # 5) 「どの単位で最大値・対象日を決めるか」(必要に応じて変更)
        group_cols = [
            "corp_number",
            "agreement_category",
            "org_id",
            "building_id",
            "ep_customer_number",
            "supply_point_number",
        ]

        # 6) 対象行だけ抜き出す（以降の処理はこの部分集合で完結させる）
        t = df_sorted.loc[
            mask_target, group_cols + ["acquisition_date", "electric_power_value"]
        ].copy()

        # 7) グループごとの最大 electric_power_value を各行に付与（Series -> 1次元になる）
        t["grp_max"] = t.groupby(group_cols, dropna=False)[
            "electric_power_value"
        ].transform("max")

        # 8) 「最大値の行」フラグ（これは 1次元の boolean Series）
        is_max_row = t["electric_power_value"].eq(t["grp_max"])

        # 9) 最大値が複数日あれば acquisition_date の最小日を対象日にする
        #    ※最大値の行だけに絞ってから groupby -> min
        obj_date = (
            t.loc[is_max_row]
            .groupby(group_cols, dropna=False)["acquisition_date"]
            .min()
            .rename("obj_date")
        )

        # 10) 各行に対象日を map で付与（1次元）
        #     group key を tuple 化して高速に紐付ける
        t["_key"] = list(map(tuple, t[group_cols].to_numpy()))
        obj_date_dict = obj_date.reset_index()
        obj_date_dict["_key"] = list(map(tuple, obj_date_dict[group_cols].to_numpy()))
        key_to_date = dict(zip(obj_date_dict["_key"], obj_date_dict["obj_date"]))
        t["obj_date"] = t["_key"].map(key_to_date)

        # 11) acquisition_date が obj_date と一致する行を 1 にする
        #     ※t の index は元 df の index と同じなのでそのまま戻せる
        idx_hit = t.index[t["acquisition_date"].eq(t["obj_date"])]
        df_sorted.loc[idx_hit, "report_max_target_month"] = 1

        df_sorted["acquisition_date"] = df_sorted["acquisition_date"].dt.strftime(
            "%Y%m%d"
        )

        return df_sorted

    @log_time
    def _save_to_postgres(self, dto, login_org_id, user_id, logger):
        """
        PostgreSQLに結果データを保存
        Args:
            dto: リクエストDTO
        """
        with get_scoped_session() as session:
            try:
                # CNカルテの場合
                if isinstance(dto, (InDto, VisInDto)):
                    if isinstance(dto, (VisInDto)):
                        # dto.fiscal_year = get_fiscal_year(dto.start_year + dto.start_month)
                        dto.fiscal_year = dto.start_year
                        tcnapp_org_id = dto.org_id
                        self._save_t_report_storage_info_to_postgres_vis(
                            session, dto, login_org_id, user_id
                        )
                    else:
                        self._save_t_report_storage_info_to_postgres_bnk(
                            session, dto, login_org_id, user_id
                        )
                        tcnapp_org_id = getTcnapp_org_id(session, dto)

                    self._save_cn_report_to_postgres(session, dto, tcnapp_org_id)
                    self._save_cn_ranking_to_postgres(session, dto, tcnapp_org_id)
                # 電力見える化の場合
                elif isinstance(dto, ElcInDto):
                    self._save_electricity_vis_to_postgres(
                        session, dto, login_org_id, logger
                    )

                self.log.info(
                    f"PostgreSQLにデータを保存しました: {self.creation_id_seed}"
                )

            except Exception as e:
                self.log.error(f"PostgreSQL保存でエラー: {e}")
                raise e

    @log_time
    def _save_t_report_storage_info_to_postgres_vis(
        self,
        session: scoped_session,
        dto: InDto | VisInDto,
        login_org_id: str,
        user_id: str,
    ):

        try:
            with get_scoped_session() as session:
                r_infos = []
                if hasattr(dto, "fiscal_year"):
                    fiscal_year = getattr(dto, "fiscal_year")
                elif hasattr(dto, "start_year"):
                    fiscal_year = getattr(dto, "start_year")
                elif hasattr(dto, "month_from"):
                    fiscal_year = getattr(dto, "month_from")[:4]
                else:
                    raise Exception(description="データ不備")

                # 建物基本情報取得
                building_stmt = select(MBuildingGroup).where(
                    MBuildingGroup.corporate_number
                    == getattr(dto, "corporate_number", None),
                    MBuildingGroup.agreement_category
                    == getattr(dto, "agreement_category", None),
                    # MBuildingGroup.org_id == getattr(dto, "org_id", None),
                    MBuildingGroup.delete_flg.is_not(True),
                )
                building_df = pd.read_sql(building_stmt, get_db_engine())

                if getattr(dto, "building_ids_for_single", None):
                    from dataclasses import dataclass

                    @dataclass
                    class GroupFilterDto:
                        group_no: str
                        option_no: str

                    m_building_stmt = session.query(
                        MBuilding.group1,
                        MBuilding.group2,
                        MBuilding.group3,
                        MBuilding.group4,
                        MBuilding.group5,
                    ).where(
                        MBuilding.corporate_number
                        == getattr(dto, "corporate_number", None),
                        MBuilding.agreement_category
                        == getattr(dto, "agreement_category", None),
                        # MBuilding.org_id == getattr(dto, "org_id", None),
                        MBuilding.building_id.in_(
                            getattr(dto, "building_ids_for_single", None)
                        ),
                        MBuilding.delete_flg.is_not(True),
                    )

                    row = m_building_stmt.first()

                    if row is None:
                        group_filters: list[GroupFilterDto] = []
                    else:
                        m = (
                            row._mapping
                            if hasattr(row, "_mapping")
                            else {
                                f"group{i}": getattr(row, f"group{i}", None)
                                for i in range(1, 6)
                            }
                        )

                        group_filters = [
                            GroupFilterDto(
                                group_no=str(i), option_no=str(m.get(f"group{i}"))
                            )
                            for i in range(1, 6)
                            if m.get(f"group{i}") not in (None, "")
                        ]

                    if not group_filters:
                        df_group_name = pd.DataFrame()
                    else:
                        df_group_name = self.pick_group_options(
                            building_df, group_filters
                        )
                else:
                    if (
                        getattr(dto, "group_for_multibuilding", None) is None
                        or getattr(dto, "group_for_multibuilding", None) == ""
                        or getattr(dto, "group_for_multibuilding", None) == []
                    ):
                        df_group_name = pd.DataFrame()
                    else:
                        df_group_name = self.pick_group_options(
                            building_df, getattr(dto, "group_for_multibuilding", None)
                        )

                gcols = self.extract_groups_from_df(df_group_name)

                group_values = (
                    (
                        gcols["group1"],
                        gcols["group2"],
                        gcols["group3"],
                        gcols["group4"],
                        gcols["group5"],
                    )
                    if getattr(dto, "site_selection_type_code", None) in ("02", "03")
                    else (None, None, None, None, None)
                )

                groups_cond = getattr(dto, "group_for_multibuilding", None) or []

                group1_id_val = option1_id_val = None
                group2_id_val = option2_id_val = None

                if len(groups_cond) > 0:
                    group1_id_val = pick(groups_cond[0], "group_no")
                    option1_id_val = pick(groups_cond[0], "option_no")

                if len(groups_cond) > 1:
                    group2_id_val = pick(groups_cond[1], "group_no")
                    option2_id_val = pick(groups_cond[1], "option_no")

                now = self.getLocalTime()

                for cinfo in self.creation_infos:
                    # print(f"★★commit直前----------------{len(cinfo.png_bytes)}")
                    r_info = TReportStorageInfo(
                        creation_id=cinfo.creation_id,
                        building_id=cinfo.building_id,
                        report_classify=ReportTypeValue.CN_REPORT_PDF.value,
                        corporate_number=dto.corporate_number,
                        agreement_category=dto.agreement_category,
                        org_id=login_org_id,
                        fiscal_year=fiscal_year if fiscal_year else "0000",
                        target_month=None,
                        registration_seq=getattr(dto, "registration_seq", 0),
                        group1=group_values[0],
                        group2=group_values[1],
                        group3=group_values[2],
                        group4=group_values[3],
                        group5=group_values[4],
                        group1_id=group1_id_val,
                        group2_id=group2_id_val,
                        option1_id=option1_id_val,
                        option2_id=option2_id_val,
                        report_status=ReportStatus.WORKING.value,
                        report_selection_period_from=(
                            dto.start_year + dto.start_month
                            if isinstance(dto, VisInDto)
                            else None
                        ),
                        format_type=getattr(dto, "creation_format", None),
                        site_selection_type=getattr(
                            dto, "site_selection_type_code", None
                        ),
                        report_created_at=now,
                        report_created_by=dto.user_email,
                        delete_flg=False,
                        created_by=user_id,
                        created_at=now,
                        updated_by=None,
                        updated_at=None,
                    )

                    r_infos.append(r_info)

                session.add_all(r_infos)

        except Exception as e:
            self.log.error(e)
            abort(500)

    @log_time
    def _save_t_report_storage_info_to_postgres_bnk(
        self,
        session: scoped_session,
        dto: InDto | VisInDto,
        login_org_id: str,
        user_id: str,
    ):

        try:
            with get_scoped_session() as session:
                r_infos = []
                now = self.getLocalTime()
                for cinfo in self.creation_infos:
                    r_info = TReportStorageInfo(
                        creation_id=cinfo.creation_id,
                        building_id=cinfo.building_id,
                        report_classify=ReportTypeValue.CN_REPORT_PDF.value,
                        corporate_number=dto.corporate_number,
                        agreement_category=dto.agreement_category,
                        org_id=login_org_id,
                        fiscal_year=dto.fiscal_year,
                        target_month=None,
                        registration_seq=dto.registration_seq,
                        report_status=ReportStatus.WORKING.value,
                        group1=None,
                        group2=None,
                        group3=None,
                        group4=None,
                        group5=None,
                        report_save_path=None,
                        report_selection_period_from=None,
                        format_type=None,
                        site_selection_type=getattr(
                            dto, "site_selection_type_code", None
                        ),
                        report_created_at=now,
                        report_created_by=user_id,
                        delete_flg=False,
                        created_by=user_id,
                        created_at=now,
                        updated_by=None,
                        updated_at=None,
                    )
                    r_infos.append(r_info)

                session.add_all(r_infos)

        except Exception as e:
            self.log.error(e)
            abort(500)

    @log_time
    def _save_cn_report_to_postgres(
        self, session: scoped_session, dto: InDto | VisInDto, tcnapp_org_id: str
    ):
        """CNレポートスナップショットをPostgreSQLに保存"""
        # 最初のCreationInfoからDataFrameを取得（全て同じデータを想定）
        if not self.creation_infos:
            self.log.warning("creation_infosが空です")
            return

        df: pd.DataFrame = self.creation_infos[0].dataframe

        # 年月範囲を決定
        if isinstance(dto, VisInDto):
            # 可視化側：start_year/month～end_year/monthの範囲
            start_year_month = f"{dto.start_year}{dto.start_month:0>2}"
            end_year_month = (
                f"{dto.end_year}{dto.end_month:0>2}"
                if dto.end_year and dto.end_month
                else start_year_month
            )
        else:
            # 地銀側：データから年月範囲を取得
            # available_months = sorted(df["target_year_month"].unique())
            available_months = sorted(df["target_year_month"].unique(), reverse=True)[
                :12
            ]
            start_year_month = available_months[-1]
            end_year_month = available_months[0]

        # 年月リストを生成
        year_months = self._generate_year_month_list(start_year_month, end_year_month)

        snapshots = []
        # KPI計算を事前に実行（全データを使用）
        try:
            # DataFrameの列名をcn_status_by_zeb関数が期待する形式に調整
            # kpi_df = df.copy()
            for creation_id in self.creation_infos:
                kpi_df = creation_id.dataframe.copy()

                kpi_df_last_year = kpi_df[kpi_df["year_flg"] == "2"]

                kpi_df = kpi_df[
                    (kpi_df["target_year_month"].astype(int) >= int(start_year_month))
                    & (kpi_df["target_year_month"].astype(int) <= int(end_year_month))
                ]
                # デバッグ情報：利用可能な列名を確認
                self.log.info(f"DataFrame列名: {list(kpi_df.columns)}")

                # CN関連の必要な列のデフォルト値設定
                # 重要：CO2_ADJUSTED_EMISSIONS_zebは実際のデータがある場合のみ設定し、ない場合は現在年データを使用
                required_columns = {}

                # 2013年基準データがない場合は、現在年データを代替として使用
                if "co2_adjusted_emissions_zeb" not in kpi_df.columns:
                    if "co2_adjusted_emissions" in kpi_df.columns:
                        # 実際のデータを基準値として使用（削減率計算のため、やや大きい値を想定）
                        kpi_df["co2_adjusted_emissions_zeb"] = (
                            kpi_df["CO2_ADJUSTED_EMISSIONS"] * 1.2
                        )  # 20%削減を想定
                        self.log.info(
                            "co2_adjusted_emissions_zeb: 現在年データの1.2倍を基準値として設定"
                        )
                    else:
                        required_columns["co2_adjusted_emissions_zeb"] = 0.0

                # その他の必要列のデフォルト値
                if "energy_quantity_for_law" not in kpi_df.columns:
                    required_columns["energy_quantity_"]
                if "heat_converted_energy_usage" not in kpi_df.columns:
                    required_columns["heat_converted_energy_usage"] = 0.0
                if "credit_certificate_purchase_tco2_amount" not in kpi_df.columns:
                    required_columns["credit_certificate_purchase_tco2_amount"] = 0.0
                if "co2_adjusted_emissions_avg" not in kpi_df.columns:
                    # 平均値がない場合は現在値を使用
                    if "co2_adjusted_emissions" in kpi_df.columns:
                        kpi_df["co2_adjusted_emissions_avg"] = kpi_df[
                            "co2_adjusted_emissions"
                        ]
                        self.log.info(
                            "co2_adjusted_emissions_avg: 現在年データを平均値として設定"
                        )
                    else:
                        required_columns["co2_adjusted_emissions_avg"] = 0.0

                for col, default_val in required_columns.items():
                    if col not in kpi_df.columns:
                        kpi_df[col] = default_val
                        self.log.info(f"デフォルト値設定: {col} = {default_val}")

                # データ存在チェック
                if kpi_df.empty or "co2_adjusted_emissions" not in kpi_df.columns:
                    self.log.warning("KPI計算に必要なデータが不足しています")
                    raise ValueError("KPI計算に必要なデータが不足")

                # データサマリーをログ出力
                self.log.info(f"KPI計算用データサマリー:")
                self.log.info(f"- レコード数: {len(kpi_df)}")
                if "co2_adjusted_emissions" in kpi_df.columns:
                    total_co2 = kpi_df["co2_adjusted_emissions"].sum()
                    self.log.info(f"- 総CO2排出量: {total_co2}")
                if "co2_adjusted_emissions_zeb" in kpi_df.columns:
                    total_co2_zeb = kpi_df["co2_adjusted_emissions_zeb"].sum()
                    self.log.info(f"- 基準年CO2排出量: {total_co2_zeb}")

                # KPI計算実行
                kpi_results = cn_status_by_zeb(kpi_df, kpi_df_last_year, self.log)
                self.log.info(f"cn_status_by_zeb計算結果: {kpi_results}")

                # 追加KPI計算（update_building_info_for_kpiロジックを基に計算）
                additional_kpi_results = self._calculate_additional_kpi_values(
                    session, kpi_df, dto
                )
                self.log.info(f"追加KPI計算結果: {additional_kpi_results}")

                # 各creation_idに対してレポートスナップショットを作成
                for i, year_month in enumerate(year_months):
                    # 該当年月のデータを取得
                    month_df = (
                        kpi_df[kpi_df["target_year_month"] == year_month]
                        if year_month in kpi_df["target_year_month"].values
                        else pd.DataFrame()
                    )

                    # # KPI計算（実装は後で詳細化）
                    # total_co2_this_year = float(month_df["co2_adjusted_emissions"].sum()) if len(month_df) > 0 else 0.0

                    # 月flgと年度flgを計算
                    month_flg = (i % 12) + 1  # 1-12のサイクル

                    year_flg = 1

                    # レポートスナップショット作成
                    report_snapshot = TCnReportSnapshot(
                        creation_id=creation_id.creation_id,
                        corporate_number=dto.corporate_number,
                        agreement_category=getattr(dto, "agreement_category", "01"),
                        org_id=tcnapp_org_id,
                        fiscal_year=year_month[:4],
                        registration_seq=getattr(dto, "registration_seq", 0),
                        year_month=year_month,
                        month_flg=month_flg,
                        year_flg=year_flg,
                        is_for_bnk=isinstance(dto, InDto),
                        need_data_insufficiency_list=(
                            dto.need_data_insufficiency_list
                            if isinstance(dto, VisInDto)
                            else False
                        ),
                        need_report_backdata=(
                            dto.need_report_backdata
                            if isinstance(dto, VisInDto)
                            else False
                        ),
                        need_kpi_list=(
                            dto.need_kpi_list if isinstance(dto, VisInDto) else False
                        ),
                        report_selection_period_from=f"{getattr(dto, 'start_year', year_month[:4])}{getattr(dto, 'start_month', '01'):0>2}",
                        report_selection_period_to=f"{getattr(dto, 'end_year', year_month[:4])}{getattr(dto, 'end_month', '12'):0>2}",
                        format_type=getattr(dto, "format_type_code", None),
                        group_condition_1=df["group_condition_1"][0],
                        group_condition_2=df["group_condition_2"][0],
                        # KPI計算結果の反映
                        # total_tco2_reduction_rate=float(kpi_results.get('total_tco2_reduction_rate') or 0),
                        # credit_certificate_coverage_rate=float(kpi_results.get('credit_certificate_coverage_rate') or 0),
                        # renewable_power_intro_rate=float(kpi_results.get('renewable_power_intro_rate') or 0),
                        renewable_energy_procurement_current=safe_round(
                            kpi_results.get("renewable_energy_procurement_current")
                            or 0,
                            5,
                        ),
                        total_energy_use_current=safe_round(
                            kpi_results.get("total_energy_use_current") or 0, 5
                        ),
                        renewable_energy_procurement_last=safe_round(
                            kpi_results.get("renewable_energy_procurement_last") or 0, 5
                        ),
                        total_energy_use_last=safe_round(
                            kpi_results.get("total_energy_use_last") or 0, 5
                        ),
                        cn_zeb_total_tco2_result=safe_round(
                            kpi_results.get("cn_zeb_total_tco2_result") or 0, 5
                        ),
                        cn_zeb_credit_certificate=safe_round(
                            kpi_results.get("cn_zeb_credit_certificate") or 0, 5
                        ),
                        cn_zeb_renewable_electric_power=safe_round(
                            kpi_results.get("cn_zeb_renewable_electric_power") or 0, 5
                        ),
                        cn_zeb_emission_factor_improvement=safe_round(
                            kpi_results.get("cn_zeb_emission_factor_improvement") or 0,
                            5,
                        ),
                        # その他KPI項目の計算結果
                        kpi_energy_saving_rate=safe_round(
                            additional_kpi_results.get("kpi_energy_saving_rate"), 5
                        ),
                        kpi_electrification_rate=safe_round(
                            additional_kpi_results.get("kpi_electrification_rate"), 5
                        ),
                        kpi_energy_creation_rate=safe_round(
                            additional_kpi_results.get("kpi_energy_creation_rate"), 5
                        ),
                        kpi_renewable_network_rate=safe_round(
                            additional_kpi_results.get("kpi_renewable_network_rate"), 5
                        ),
                        delete_flg=False,
                        created_by=creation_id.creation_id.rsplit("_", 2)[0],
                    )
                    snapshots.append(report_snapshot)

                    # 前年度分
                    year_month_prev = f"{int(year_month[:4])-1}{year_month[-2:]}"
                    # if self.use_postgres_storage:
                    #     month_list_prev = creation_info.dataframe["target_year_month"]
                    # else:
                    month_list_prev = creation_id.dataframe[
                        "target_year_month"
                    ].tolist()

                    if year_month_prev in month_list_prev:
                        year_flg = 2
                        year_month_final = year_month_prev
                    else:
                        year_flg = 0
                        year_month_final = year_month

                    # レポートスナップショット作成
                    report_snapshot = TCnReportSnapshot(
                        creation_id=creation_id.creation_id,
                        corporate_number=dto.corporate_number,
                        agreement_category=getattr(dto, "agreement_category", "01"),
                        org_id=tcnapp_org_id,
                        fiscal_year=year_month[:4],
                        registration_seq=getattr(dto, "registration_seq", 0),
                        year_month=year_month_final,
                        month_flg=month_flg,
                        year_flg=year_flg,
                        is_for_bnk=isinstance(dto, InDto),
                        need_data_insufficiency_list=(
                            dto.need_data_insufficiency_list
                            if isinstance(dto, VisInDto)
                            else False
                        ),
                        need_report_backdata=(
                            dto.need_report_backdata
                            if isinstance(dto, VisInDto)
                            else False
                        ),
                        need_kpi_list=(
                            dto.need_kpi_list if isinstance(dto, VisInDto) else False
                        ),
                        report_selection_period_from=f"{getattr(dto, 'start_year', year_month[:4])}{getattr(dto, 'start_month', '01'):0>2}",
                        report_selection_period_to=f"{getattr(dto, 'end_year', year_month[:4])}{getattr(dto, 'end_month', '12'):0>2}",
                        format_type=getattr(dto, "format_type_code", None),
                        group_condition_1=df["group_condition_1"][0],
                        group_condition_2=df["group_condition_2"][0],
                        delete_flg=False,
                        created_by=creation_id.creation_id.rsplit("_", 2)[0],
                    )
                    snapshots.append(report_snapshot)

            session.add_all(snapshots)

        except Exception as e:
            self.log.warning(f"KPI計算でエラーが発生しました: {e}")
            raise e

    # @log_time
    def _save_cn_ranking_to_postgres(
        self, session: scoped_session, dto: InDto | VisInDto, tcnapp_org_id
    ):
        """CNランキングスナップショットをPostgreSQLに保存"""
        # 最初のCreationInfoからDataFrameを取得
        if not self.creation_infos:
            self.log.warning("creation_infosが空です")
            return

        # df:pd.DataFrame = self.creation_infos.dataframe.copy()

        # df_with_ranking = df.copy()

        # creation_idのリストを生成（CreationInfoから）
        creation_ids = [info.creation_id for info in self.creation_infos]

        snapshots = []
        # 各creation_idに対してランキングスナップショットを作成
        for creation_id in self.creation_infos:

            df_with_ranking: pd.DataFrame = creation_id.dataframe.copy()

            df_with_ranking = df_with_ranking[df_with_ranking["energy_ranking"] != 0]

            # _calc_ranking_cn関数を使用してランキングを計算
            self.log.info("CNランキング計算を開始します")

            # 必要な列の存在確認
            required_columns = ["energy_code", "co2_adjusted_emissions", "energy_name"]
            missing_columns = [
                col for col in required_columns if col not in df_with_ranking.columns
            ]

            if missing_columns:
                self.log.error(
                    f"ランキング計算に必要な列が不足しています: {missing_columns}"
                )
                self.log.info(f"利用可能な列: {list(df_with_ranking.columns)}")
                # 不足している列があっても処理を続行（デフォルト値で補完）
                for col in missing_columns:
                    if col == "energy_name":
                        df_with_ranking[col] = df_with_ranking.get(
                            "energy_code", "Unknown"
                        )  # エネルギーコードで代替
                    else:
                        df_with_ranking[col] = 0  # 数値列はデフォルト0

            # エネルギーコード毎にランキング情報を保存
            for energy_code in df_with_ranking["energy_code"].unique():
                energy_df = df_with_ranking[
                    df_with_ranking["energy_code"] == energy_code
                ]

                if len(energy_df) > 0:
                    # _calc_ranking_cn関数で計算された値を使用
                    energy_ranking = int(energy_df["energy_ranking"].iloc[0])
                    energy_ranking_name = energy_df["energy_ranking_name"].iloc[0]

                    ranking_snapshot = TCnRankingSnapshot(
                        creation_id=creation_id.creation_id,
                        corporate_number=dto.corporate_number,
                        agreement_category=getattr(dto, "agreement_category", "01"),
                        org_id=tcnapp_org_id,
                        fiscal_year=getattr(
                            dto, "fiscal_year", getattr(dto, "start_year", 2024)
                        ),
                        registration_seq=getattr(dto, "registration_seq", 0),
                        energy_code=energy_code,
                        energy_ranking_name=energy_ranking_name,
                        energy_ranking=energy_ranking,
                        delete_flg=False,
                        created_by=creation_id.creation_id.rsplit("_", 2)[0],
                    )
                    snapshots.append(ranking_snapshot)

        session.add_all(snapshots)

    @log_time
    def _save_electricity_vis_to_postgres(
        self, session: scoped_session, dto: ElcInDto, login_org_id, logger
    ):
        """電力見える化レポートフラグ付けスナップショットをPostgreSQLに保存"""
        # ElcInDtoの場合、creation_infosの構造が異なる可能性があるため対応
        # col形式のDataFrame（melt済み）を使用
        col_df: pd.DataFrame = None

        report_created_at = func.now()

        for creation_info in self.creation_infos:
            # 電力見える化用のDataFrameを検索
            if creation_info.creation_id.endswith("_0"):  # 電力見える化は常に_0
                col_df = creation_info.dataframe
                break

        if col_df is None:
            self.log.error("電力見える化用DataFrameが見つかりません")
            return

        # creation_idの生成
        creation_id = f"{self.creation_id_seed}_0"  # 電力見える化は常に_0

        # 拠点住所取得
        row = (
            session.query(
                func.concat(
                    PrefectureMst.pref_nm, MBuilding.building_address_city
                ).label("building_address"),
            )
            .select_from(MBuilding)
            .outerjoin(
                PrefectureMst,
                PrefectureMst.pref_cd == MBuilding.building_address_prefecture,
            )
            .where(
                MBuilding.corporate_number == dto.corporate_number,
                MBuilding.agreement_category == dto.agreement_category,
                # MBuilding.org_id == dto.org_id,
                MBuilding.building_id == dto.building_id,
                MBuilding.delete_flg.is_not(True),
                PrefectureMst.delete_flag == 0,
            )
            # .order_by(TBuildingInfo.registration_seq.desc(),
            #         TBuildingInfo.fiscal_year.desc())
            .first()
        )

        building_address_data = "" if row is None else (row.building_address or "")

        r_infos = []
        r_info = TReportStorageInfo(
            creation_id=creation_id,
            building_id=dto.building_id,
            report_classify=ReportTypeValue.POWER_VISUAL_PDF.value,
            corporate_number=dto.corporate_number,
            agreement_category=dto.agreement_category,
            org_id=login_org_id,
            fiscal_year=dto.fiscal_year,
            target_month=dto.target_month,
            registration_seq="0",
            report_status=ReportStatus.WORKING.value,
            report_selection_period_from=dto.fiscal_year + dto.month_from,
            site_selection_type=getattr(dto, "site_selection_type_code", None),
            report_created_at=report_created_at,
            report_created_by=dto.user_id,
            delete_flg=False,
            created_by=dto.user_id,
        )
        r_infos.append(r_info)

        session.add_all(r_infos)
        # session.commit()

        # フラグが1のレコードのみをフィルタリング
        # まずフラグ列の存在確認とデフォルト値設定
        for flag_col in [
            "report_max_day",
            "report_max_week",
            "report_max_frequency",
            "report_target_month",
        ]:
            if flag_col not in col_df.columns:
                col_df[flag_col] = 0

        # スナップショットの作成
        snapshots = []
        for _, row in col_df.iterrows():
            # acquisition_dateの処理
            acquisition_date = row.get("acquisition_date", "")
            if hasattr(acquisition_date, "strftime"):  # datetimeオブジェクトの場合
                acquisition_date = acquisition_date.strftime("%Y%m%d")
            else:
                acquisition_date = str(acquisition_date)

            row = row.copy()

            row["time"] = str(row.get("time", ""))[:5]
            snapshot = TElectricityVisFlgSnapshot(
                creation_id=creation_id,
                corp_number=dto.corporate_number,
                agreement_category=dto.agreement_category,
                org_id="TEP",
                contracted_power=dto.contracted_power,
                building_address=building_address_data,
                building_id=dto.building_id,
                supply_point_number=str(row.get("supply_point_number", ""))[
                    :27
                ],  # 長さ制限
                acquisition_date=acquisition_date,
                acquisition_time=str(row.get("time", ""))[:5],  # 長さ制限
                corp_name=str(row.get("corp_name", ""))[:100],  # 長さ制限
                building_name=str(row.get("building_name", ""))[:100],  # 長さ制限
                ep_customer_number=str(row.get("ep_customer_number", ""))[
                    :16
                ],  # 長さ制限
                # company_id=str(row.get("company_id", ""))[:14],  # 長さ制限
                report_max_day=row.get("report_max_day", "0"),
                report_max_week=row.get("report_max_week", "0"),
                report_max_frequency=row.get("report_max_frequency", "0"),
                report_target_month=row.get("report_target_month", "0"),
                report_max_target_month=row.get("report_max_target_month", "0"),
                delete_flg=False,
                created_by=dto.user_id,
                created_at=report_created_at,
            )
            snapshots.append(snapshot)

            # 建物マスタの契約電力更新
        mBuilding_UP_for_contracted_power = (
            session.query(MBuilding)
            .filter_by(
                corporate_number=dto.corporate_number,
                agreement_category=dto.agreement_category,
                # agreement_org=dto.org_id,
                building_id=dto.building_id,
            )
            .one_or_none()
        )

        if mBuilding_UP_for_contracted_power is None:
            abort(400, description=get_message("BUILDING_INFO_NOT_EXSIT"))

        new_power = Decimal(dto.contracted_power) if dto.contracted_power else None

        if mBuilding_UP_for_contracted_power.contracted_power != new_power:
            mBuilding_UP_for_contracted_power.contracted_power = new_power
            mBuilding_UP_for_contracted_power.updated_by = dto.user_id
            mBuilding_UP_for_contracted_power.updated_at = report_created_at

        session.add_all(snapshots)
        session.add(mBuilding_UP_for_contracted_power)

    # @log_time
    def _generate_year_month_list(
        self, start_year_month: str, end_year_month: str
    ) -> list[str]:
        """
        開始年月から終了年月までの年月リストを生成
        Args:
            start_year_month: 開始年月 (YYYYMM形式)
            end_year_month: 終了年月 (YYYYMM形式)
        Returns:
            list[str]: 年月リスト (YYYYMM形式)
        """
        year_months = []

        start_year = int(start_year_month[:4])
        start_month = int(start_year_month[4:6])
        end_year = int(end_year_month[:4])
        end_month = int(end_year_month[4:6])

        current_year = start_year
        current_month = start_month

        while (current_year < end_year) or (
            current_year == end_year and current_month <= end_month
        ):
            year_months.append(f"{current_year}{current_month:02d}")

            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return year_months

    # @log_time
    def _calculate_additional_kpi_values(self, session, df: pd.DataFrame, dto) -> dict:
        """
        update_building_info_for_kpi関数の計算ロジックを基にした追加KPI値の計算
        """
        try:
            from cndx_corp_back.common import constants_values
            from cndx_corp_back.entity.t_cn_application_info_entity import (
                TCnApplicationInfo,
            )

            energy_saving_denominator = 0
            energy_benchmark_indicator_avg = 0
            print_mode = 0  # デフォルト企業全体(地銀も)
            fiscal_years = df["fiscal_year"].dropna().unique().tolist()

            if isinstance(dto, VisInDto):
                # 可視化側：条件によって分岐
                # 単拠点の場合
                if (
                    hasattr(dto, "building_ids_for_single")
                    and dto.building_ids_for_single
                ):
                    print_mode = 2
                elif hasattr(dto, "is_for_multibuilding") and dto.is_for_multibuilding:
                    if (
                        hasattr(dto, "group_for_multibuilding")
                        and dto.group_for_multibuilding
                    ):
                        # グループの場合
                        print_mode = 1

            # 企業全体の場合
            if print_mode == 0:
                # CN申請情報取得
                cnapp_info_list = (
                    session.query(TCnApplicationInfo)
                    .filter(
                        TCnApplicationInfo.corporate_number == dto.corporate_number,
                        TCnApplicationInfo.agreement_category
                        == getattr(dto, "agreement_category", "01"),
                        TCnApplicationInfo.org_id == dto.org_id,
                        TCnApplicationInfo.registration_seq
                        == int(df["registration_seq"].iloc[0]),
                        # TCnApplicationInfo.fiscal_year==getattr(dto, 'fiscal_year', getattr(dto, 'start_year', 2024))
                        TCnApplicationInfo.fiscal_year.in_(fiscal_years),
                    )
                    .all()
                )

                if not cnapp_info_list:
                    return {
                        "kpi_energy_saving_rate": None,
                        "kpi_electrification_rate": None,
                        "kpi_energy_creation_rate": None,
                        "kpi_renewable_network_rate": None,
                    }
                # energy_saving_denominator = getattr(cnapp_info_list[0], 'energy_saving_denominator', 0)
                # competitor_industry_co2_avg = getattr(cnapp_info_list[0], 'competitor_industry_co2_avg', 0)
                # 平均値取得
                energy_saving_denominator = (
                    statistics.mean(
                        [
                            item.energy_saving_denominator
                            for item in cnapp_info_list
                            if item.energy_saving_denominator is not None
                        ]
                    )
                    if any(
                        item.energy_saving_denominator is not None
                        for item in cnapp_info_list
                    )
                    else None
                )

                energy_benchmark_indicator_avg = (
                    statistics.mean(
                        [
                            float(item.energy_benchmark_indicator)
                            for item in cnapp_info_list
                            if item.energy_benchmark_indicator is not None
                        ]
                    )
                    if any(
                        item.energy_benchmark_indicator is not None
                        for item in cnapp_info_list
                    )
                    else None
                )

            # グループ、単拠点の場合
            else:
                # 対象拠点id取得
                building_ids = df["building_id"].dropna().unique().tolist()
                # 建物情報取得
                t_building_info_list = (
                    session.query(TBuildingInfo)
                    .filter(
                        TBuildingInfo.corporate_number == dto.corporate_number,
                        TBuildingInfo.agreement_category
                        == getattr(dto, "agreement_category", "01"),
                        TBuildingInfo.org_id == dto.org_id,
                        TBuildingInfo.registration_seq
                        == int(df["registration_seq"].iloc[0]),
                        # TBuildingInfo.fiscal_year==getattr(dto, 'fiscal_year', getattr(dto, 'start_year', 2024)),
                        TBuildingInfo.fiscal_year.in_(fiscal_years),
                        TBuildingInfo.building_id.in_(building_ids),
                    )
                    .all()
                )

                if not t_building_info_list:
                    return {
                        "kpi_energy_saving_rate": None,
                        "kpi_electrification_rate": None,
                        "kpi_energy_creation_rate": None,
                        "kpi_renewable_network_rate": None,
                    }
                # 平均値取得
                energy_saving_denominator = (
                    statistics.mean(
                        [
                            item.energy_saving_denominator
                            for item in t_building_info_list
                            if item.energy_saving_denominator is not None
                        ]
                    )
                    if any(
                        item.energy_saving_denominator is not None
                        for item in t_building_info_list
                    )
                    else None
                )

                energy_benchmark_indicator_avg = (
                    statistics.mean(
                        [
                            float(item.energy_benchmark_indicator)
                            for item in t_building_info_list
                            if item.energy_benchmark_indicator is not None
                        ]
                    )
                    if any(
                        item.energy_benchmark_indicator is not None
                        for item in t_building_info_list
                    )
                    else None
                )

            # 各種エネルギー使用量計算
            # 電力コード定数の取得
            try:
                electric_power_code = constants_values.ENERGY_CODE_ELECTRIC_POWER_2023
            except AttributeError:
                # デフォルトの電力エネルギーコード
                electric_power_code = "0200010001"  # 一般的な電力コード

            # 電力熱量換算値
            heat_consumption_total_electric_power = (
                float(
                    df[df["energy_code"] == electric_power_code][
                        "heat_converted_energy_usage"
                    ].sum()
                )
                if "heat_converted_energy_usage" in df.columns
                else 0.0
            )

            # 全エネルギー熱量換算値
            heat_consumption_total = (
                float(df["heat_converted_energy_usage"].sum())
                if "heat_converted_energy_usage" in df.columns
                else 0.0
            )

            # 創エネエネルギー消費量
            energy_consumption_self_electric_power = (
                float(
                    df[df["supplier_reg_no"] == "REENE"][
                        "energy_quantity_for_law"
                    ].sum()
                )
                if "energy_quantity_for_law" in df.columns
                else 0.0
            )

            # 全電力エネルギー消費量
            energy_consumption_total_electric_power = (
                float(
                    df[df["energy_code"].str.startswith("02")][
                        "energy_quantity_for_law"
                    ].sum()
                )
                if "energy_quantity_for_law" in df.columns
                else 0.0
            )

            codes = [
                "9900010002",
                "9900010003",
                "9900010004",
                "9900010001",
                "9900010006",
                "9900010013",
                "9900011013",
                "9900011002",
                "9900011003",
                "9900011004",
                "9900011007",
                "9900011005",
                "9900011001",
            ]

            # 証書・クレジット購入量
            if "credit_certificate_purchase_tco2_amount" in df.columns:
                credit_certificate_purchase_tco2_total = float(
                    df.loc[
                        df["energy_code"].isin(codes),
                        "credit_certificate_purchase_tco2_amount",
                    ].sum()
                )
            else:
                credit_certificate_purchase_tco2_total = 0.0

            # 電力CO2換算値
            co2_total_electric_power = (
                float(
                    df[df["energy_code"] == electric_power_code][
                        "co2_adjusted_emissions"
                    ].sum()
                )
                if "co2_adjusted_emissions" in df.columns
                else 0.0
            )

            # 電力平均CO2換算値
            co2_total_electric_power_avg = (
                float(
                    df[(df["energy_code"] == electric_power_code)][
                        "co2_adjusted_emissions_avg"
                    ].sum()
                )
                if "co2_adjusted_emissions_avg" in df.columns
                else 0.0
            )

            # KPI計算
            # 省エネ率実績割合
            kpi_energy_saving_rate = 0
            # val = getattr(cnapp_info_list[0], 'energy_saving_denominator', None)
            if (
                energy_saving_denominator is not None
                and energy_benchmark_indicator_avg is not None
                and energy_saving_denominator > 0
            ):
                kpi_energy_saving_rate = float(
                    (float(energy_saving_denominator) - energy_benchmark_indicator_avg)
                    / float(energy_saving_denominator)
                )
            else:
                kpi_energy_saving_rate = 0

            # 電化率実績割合
            kpi_electrification_rate = 0
            if heat_consumption_total > 0:
                kpi_electrification_rate = float(
                    heat_consumption_total_electric_power / heat_consumption_total
                )

            # 創エネ率実績割合
            kpi_energy_creation_rate = 0
            if energy_consumption_total_electric_power > 0:
                kpi_energy_creation_rate = float(
                    energy_consumption_self_electric_power
                    / energy_consumption_total_electric_power
                )
            else:
                kpi_energy_creation_rate = 0

            # CN外部調達
            kpi_renewable_network_rate = 0
            renewable_rate = co2_total_electric_power_avg - co2_total_electric_power
            if renewable_rate < 0:
                renewable_rate = 0.0
            if co2_total_electric_power_avg > 0:
                kpi_renewable_network_rate = float(
                    (renewable_rate + credit_certificate_purchase_tco2_total)
                    / co2_total_electric_power_avg
                )

            # レーダー図不具合対応のため処理
            values = [
                kpi_energy_saving_rate,
                kpi_electrification_rate,
                kpi_energy_creation_rate,
                kpi_renewable_network_rate,
            ]

            # 0（0.0含み）の位置確定
            zero_indices = [i for i, v in enumerate(values) if v == 0]

            # 唯一1の場合のみNoneにする
            if len(zero_indices) == 1:
                values[zero_indices[0]] = None

            (
                kpi_energy_saving_rate,
                kpi_electrification_rate,
                kpi_energy_creation_rate,
                kpi_renewable_network_rate,
            ) = values

            return {
                "kpi_energy_saving_rate": kpi_energy_saving_rate,
                "kpi_electrification_rate": kpi_electrification_rate,
                "kpi_energy_creation_rate": kpi_energy_creation_rate,
                "kpi_renewable_network_rate": kpi_renewable_network_rate,
            }

        except Exception as e:
            self.log.warning(f"追加KPI計算でエラーが発生しました: {e}")
            raise e

    @log_time
    def pick_group_options(self, df, filters):
        item_cols = [f"select_item{i}" for i in range(1, 8)]
        long_df = df.melt(
            id_vars=[
                "corporate_number",
                "agreement_category",
                "org_id",
                "group_id",
                "group_name",
            ],
            value_vars=item_cols,
            var_name="option_col",
            value_name="value",
        )
        long_df["option_no"] = long_df["option_col"].str.extract(r"(\d+)").astype(int)
        long_df["group_id"] = pd.to_numeric(
            long_df["group_id"], errors="coerce"
        ).astype("Int64")

        if filters:  # ここで判定
            filters_df = to_filters_df(filters)
            out = (
                long_df.merge(filters_df, on=["group_id", "option_no"], how="inner")
                .drop(columns=["option_col"])
                .dropna(subset=["value"])
            )
        else:
            out = long_df.drop(columns=["option_col"]).dropna(subset=["value"])

        # 見やすい列順に整理
        out = out[
            [
                "corporate_number",
                "agreement_category",
                "org_id",
                "group_id",
                "group_name",
                "option_no",
                "value",
            ]
        ].sort_values(["group_id", "option_no"])

        return out

    @log_time
    def extract_groups_from_df(
        self, df: pd.DataFrame, max_groups: int = 5
    ) -> Dict[str, Optional[str]]:
        """
        df から group1～group5 を作る。
        - group_id が 1..5 の行だけ対象
        - value が NaN/空ならスキップ
        - 同じ group_id が複数行ある場合は先に出たものを採用
        """
        result: Dict[str, Optional[str]] = {
            f"group{i}": None for i in range(1, max_groups + 1)
        }
        if df is None or df.empty:
            return result

        # 型をそろえる
        work = df.copy()
        work["group_id"] = pd.to_numeric(work["group_id"], errors="coerce").astype(
            "Int64"
        )
        work["value"] = work["value"].astype(str).str.strip()

        # ノイズ除去
        work = work.dropna(subset=["group_id"])
        work = work[work["value"].ne("")]

        # group_id 1..max_groups のみ
        work = work[(work["group_id"] >= 1) & (work["group_id"] <= max_groups)]

        # option_no があればソートして優先順を制御（小さい option_no を優先したい場合）
        if "option_no" in work.columns:
            work["option_no"] = pd.to_numeric(work["option_no"], errors="coerce")
            work = work.sort_values(["group_id", "option_no"], na_position="last")
        else:
            work = work.sort_values(["group_id"])

        # 各 group_id の最初の value を採用
        seen = set()
        for _, row in work.iterrows():
            gid = int(row["group_id"])
            if gid not in seen:
                result[f"group{gid}"] = row["value"]
                seen.add(gid)
                if len(seen) == max_groups:
                    break

        return result

    def getLocalTime(self):
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        timestamp = (
            now_local.strftime("%Y/%m/%d %H:%M:%S")
            + f".{int(now_local.microsecond / 1000):03d}"
        )
        return timestamp


def adjust_margin(binary_pdf):
    """PDF余白調整"""

    pdf_stream = io.BytesIO(binary_pdf)

    doc = fitz.open("pdf", pdf_stream)

    for page in doc:
        rect = page.cropbox  # 現在のページのトリミング領域

        # 左：右へ10 下：上へ20 右：右へ-50 上：上へ-20
        new_rect = fitz.Rect(rect.x0 + 10, rect.y0 + 20, rect.x1 - 45, rect.y1 - 20)

        page.set_cropbox(new_rect)

    # バイナリデータとして保存
    output_stream = io.BytesIO()
    doc.save(output_stream)
    doc.close()

    # return output_stream
    return output_stream.getvalue()


# @log_time
def pdf_to_img(pdf_stream, filename):
    """プレビュー画像を生成"""
    # try:
    #     pdf_doc = fitz.open("pdf", pdf_stream)

    #     page:fitz.Page = pdf_doc.load_page(0)

    #     # 画像レンダリング
    #     pix:fitz.Pixmap = page.get_pixmap()
    #     # pix.save("page1.png")

    #     png_bytes = pix.tobytes("png")
    #     png_stream = io.BytesIO(png_bytes)
    #     png_stream.seek(0)  # 重置指针位置

    #     # FileStorage を組立
    #     file_storage = FileStorage(
    #         stream=png_stream,
    #         filename=f"{filename}.png",
    #         content_type="image/png"
    #     )

    #     # thumbnail_base64 = base64.b64encode(png_bytes).decode("utf-8")
    #     # logger.debug(f"{len(png_bytes)}:★★★★★★★★★★★★★★★")
    #     return file_storage, png_bytes
    pdf_doc = fitz.open("pdf", pdf_stream)

    # try:
    # 1ページ目を取得
    page: fitz.Page = pdf_doc.load_page(0)

    # 元ページのサイズを取得
    page_rect = page.rect

    # プレビュー用の最大横幅（縮略図サイズ）
    max_width = 300

    # 横幅を基準に等比率でスケーリング
    scale = max_width / page_rect.width
    matrix = fitz.Matrix(scale, scale)

    # ページを画像としてレンダリング
    # ・alpha=False：透過情報を除外し、メモリ使用量を削減
    pix: fitz.Pixmap = page.get_pixmap(matrix=matrix, alpha=False)

    # JPEG形式のバイト列を生成（DB保存・高速処理向け）
    img_bytes = pix.tobytes("jpeg", jpg_quality=80)

    # BytesIO に変換（アップロード用）
    img_stream = io.BytesIO(img_bytes)

    # FileStorage を生成
    file_storage = FileStorage(
        stream=img_stream, filename=f"{filename}.jpg", content_type="image/jpeg"
    )

    return file_storage, img_bytes

    # finally:
    #     # PDFリソースを解放
    #     pdf_doc.close()


def to_fullwidth_digit(halfwidth_digit):
    """
    半角数字 (0-9) を全角数字にする。
        :param halfwidth_digit: str 形式の半角数字，例えば '5'
        :return: 該当する全角数字，例えば '５'
    """
    if halfwidth_digit in "0123456789":
        return chr(ord(halfwidth_digit) + 0xFEE0)
    else:
        raise ValueError("半角数字の入力ではない")


def _calc_ranking_cn(df: pd.DataFrame):

    df["energy_category_name"] = df["energy_category_name"].str.strip()

    df_new = df.copy()

    # 除外対象のエネルギーコード
    exclude_codes = [
        "9900010002",
        "9900010003",
        "9900010004",
        "9900011002",
        "9900011003",
        "9900011004",
        "9900011005",
        "9900011007",
        "9900010006",
        "9900010013",
        "9900011013",
        "9900011001",
    ]

    all_exclude_codes = [
        "9900010002",
        "9900010003",
        "9900010004",
        "9900011002",
        "9900011003",
        "9900011004",
        "9900011005",
        "9900011007",
        "9900011006",
        "9900011008",
        "9900011009",
        "9900011010",
        "9900011011",
        "9900011012",
        "9900011013",
        "9900011014",
        "9900010006",
        "9900010013",
        "9900011013",
        "9900011001",
    ]

    # energy_code が 0200010011 の行
    mask_target = df_new["energy_code"] == "0200010011"

    # 除外対象の行（energy_code は問わない）
    mask_exclude = df_new["energy_code"].isin(exclude_codes)

    all_mask_exclude = df_new["energy_code"].isin(all_exclude_codes)

    # 除外対象の co2_adjusted_emissions 合計
    subtract_value = df_new.loc[mask_exclude, "co2_adjusted_emissions"].sum()

    # 0200010011 の行から除外対象の合計値を減算
    ele_energy_code_sum = (
        df_new.loc[mask_target, "co2_adjusted_emissions"].sum() - subtract_value
    )

    energy_code_sum = (
        df[
            (df["energy_code"] != "0200010011")
            & (~df["energy_code"].isin(all_exclude_codes))
        ]
        .groupby("energy_code")["co2_adjusted_emissions"]
        .sum()
    )

    energy_code_sum = pd.concat(
        [energy_code_sum, pd.Series({"0200010011": ele_energy_code_sum})]
    )

    energy_code_ranking = energy_code_sum.rank(method="dense", ascending=False).astype(
        int
    )
    df["energy_ranking"] = (
        df["energy_code"].map(energy_code_ranking).apply(lambda x: min(x, 5))
    )

    # ランキングの最大値を取得
    max_rank = energy_code_ranking.max()
    # 条件に基づいて energy_category_name を更新
    df["energy_ranking_name"] = np.where(
        (df["energy_ranking"] > 5)
        | (
            (df["energy_ranking"] == 5)
            & ((max_rank > 5) | len(df["energy_code"].unique()) > 5)
        ),
        "その他",
        df["energy_category_name"],
    )

    df.loc[all_mask_exclude, "energy_ranking"] = 6

    return df


def _get_month_dict(start_month: str):
    """月順序を表すdict"""
    return {str((start_month + i - 1) % 12 + 1).zfill(2): i for i in range(12)}


# 8つの追加項目 計算処理
@log_time
def cn_status_by_zeb(mb_df, mb_df_last_year, logger):

    # 重複レコード削除

    # 電気証書対象のenergy_codeリスト
    deduction_codes_eletric = [
        "9900010002",
        "9900010003",
        "9900010004",
        "9900011002",
        "9900011003",
        "9900011004",
        "9900011005",
        "9900011007",
        "9900010006",
        "9900010013",
        "9900011013",
        "9900011001",
    ]
    # 熱証書とその他対象のenergy_codeリスト
    deduction_codes_heat_other = [
        "9900011006",
        "9900011008",
        "9900011009",
        "9900011010",
        "9900011011",
        "9900011012",
        "9900011014",
    ]
    # その他対象のenergy_codeリスト
    deduction_codes_heat = ["9900011006", "9900011008"]
    # 熱証書対象のenergy_codeリスト
    deduction_codes_other = [
        "9900011009",
        "9900011010",
        "9900011011",
        "9900011012",
        "9900011014",
    ]

    # CO2排出係数の取得
    co2_coefficient_eletric_2013 = constants_values.CO2_EMISSION_ELECRIC_COEFFICIENT
    co2_coefficient_industrial_2013 = (
        constants_values.CO2_EMISSION_INDUSTRIAL_COEFFICIENT_2013
    )

    # デバッグ情報
    logger.debug(f"cn_status_by_zeb入力データ形状: {mb_df.shape}")
    logger.debug(f"利用可能な列: {list(mb_df.columns)}")

    # 全CO2排出値
    all_tco2_this_year = (mb_df["co2_adjusted_emissions"].sum()) or 0
    # all_tco2_last_year = (mb_df["last_year_co2_adjusted_emissions"].sum()) or 0
    if mb_df_last_year.empty:
        all_tco2_last_year = 0
    else:
        all_tco2_last_year = (mb_df_last_year["co2_adjusted_emissions"].sum()) or 0
    logger.debug(f"全CO2排出値（当年）: {all_tco2_this_year}")

    # 電気証書使用量
    credit_certificate_elecric_co2zeb_this_year = (
        mb_df[mb_df["energy_code"].isin(deduction_codes_eletric)][
            "co2_adjusted_emissions_zeb"
        ].sum()
    ) or 0
    # 熱証書使用量
    credit_certificate_heat_co2zeb_this_year = (
        mb_df[mb_df["energy_code"].isin(deduction_codes_heat)][
            "co2_adjusted_emissions_zeb"
        ].sum()
    ) or 0
    # その他のCO2排出量
    credit_certificate_other_amount_this_year = (
        mb_df[mb_df["energy_code"].isin(deduction_codes_other)][
            "credit_certificate_purchase_tco2_amount"
        ].sum()
    ) or 0

    # 今年度全証書CO2排出量
    credit_certificate_tco2_this_year = (
        mb_df["credit_certificate_purchase_tco2_amount"].sum()
    ) or 0
    logger.debug(f"証書CO2排出値（当年）: {credit_certificate_tco2_this_year}")

    # 前年度全証書CO2排出量
    # credit_certificate_tco2_last_year = (mb_df["last_year_credit_certificate_purchase_tco2_amount"].sum()) or 0
    if mb_df_last_year.empty:
        credit_certificate_tco2_last_year = 0
    else:
        credit_certificate_tco2_last_year = (
            mb_df_last_year["credit_certificate_purchase_tco2_amount"].sum()
        ) or 0
    logger.debug(f"証書CO2排出値（前年）: {credit_certificate_tco2_last_year}")

    # 今年度合計値から証書控除
    all_tco2_this_year = max(all_tco2_this_year - credit_certificate_tco2_this_year, 0)
    # 前年度合計値から証書控除
    all_tco2_last_year = max(all_tco2_last_year - credit_certificate_tco2_last_year, 0)

    # energy_code 0200010011の特別処理
    energy_code_0200010011_emissions = mb_df[mb_df["energy_code"] == "0200010011"][
        "co2_adjusted_emissions"
    ].sum()

    # last_year_energy_code_0200010011_emissions = mb_df[mb_df["energy_code"] == "0200010011"]["last_year_co2_adjusted_emissions"].sum()
    if mb_df_last_year.empty:
        last_year_energy_code_0200010011_emissions = 0
    else:
        last_year_energy_code_0200010011_emissions = mb_df_last_year[
            mb_df_last_year["energy_code"] == "0200010011"
        ]["co2_adjusted_emissions"].sum()

    deduction_emissions = mb_df[mb_df["energy_code"].isin(deduction_codes_eletric)][
        "co2_adjusted_emissions"
    ].sum()

    # last_year_deduction_emissions = mb_df[mb_df["energy_code"].isin(deduction_codes_eletric)]["last_year_co2_adjusted_emissions"].sum()
    if mb_df_last_year.empty:
        last_year_deduction_emissions = 0
    else:
        last_year_deduction_emissions = mb_df_last_year[
            mb_df_last_year["energy_code"].isin(deduction_codes_eletric)
        ]["co2_adjusted_emissions"].sum()

    # 0200010011の排出量から控除対象を引く
    adjusted_0200010011_emissions = max(
        energy_code_0200010011_emissions - deduction_emissions, 0
    )

    last_year_adjusted_0200010011_emissions = max(
        last_year_energy_code_0200010011_emissions - last_year_deduction_emissions, 0
    )

    # 全体の排出量を再計算（0200010011と控除対象を除外し、調整後の0200010011を追加）
    exclude_codes = (
        ["0200010011"] + deduction_codes_eletric + deduction_codes_heat_other
    )
    all_tco2_this_year = mb_df[~mb_df["energy_code"].isin(exclude_codes)][
        "co2_adjusted_emissions"
    ].sum()
    all_tco2_this_year += adjusted_0200010011_emissions

    # all_tco2_last_year = mb_df[~mb_df["energy_code"].isin(exclude_codes)]["last_year_co2_adjusted_emissions"].sum()
    if mb_df_last_year.empty:
        all_tco2_last_year = 0
    else:
        all_tco2_last_year = mb_df_last_year[
            ~mb_df_last_year["energy_code"].isin(exclude_codes)
        ]["co2_adjusted_emissions"].sum()
    all_tco2_last_year += last_year_adjusted_0200010011_emissions

    # 熱関連の控除対象コードの排出量を引く
    deduction_heat_emissions = mb_df[
        mb_df["energy_code"].isin(deduction_codes_heat_other)
    ]["co2_adjusted_emissions"].sum()
    all_tco2_this_year = max(all_tco2_this_year - deduction_heat_emissions, 0)

    # last_year_deduction_heat_emissions = mb_df[mb_df["energy_code"].isin(deduction_codes_heat_other)]["last_year_co2_adjusted_emissions"].sum()
    if mb_df_last_year.empty:
        last_year_deduction_heat_emissions = 0
    else:
        last_year_deduction_heat_emissions = mb_df_last_year[
            mb_df_last_year["energy_code"].isin(deduction_codes_heat_other)
        ]["co2_adjusted_emissions"].sum()
    all_tco2_last_year = max(all_tco2_last_year - last_year_deduction_heat_emissions, 0)

    # 全CO2排出値2013
    all_tco2_2013 = (mb_df["co2_adjusted_emissions_zeb"].sum()) or 0
    logger.debug(f"全CO2排出値（基準年）: {all_tco2_2013}")

    # 全証書CO2排出値2013
    # credit_certificate_tco2_2013 = (mb_df[mb_df["energy_code"] == "9900"]["co2_adjusted_emissions_zeb"].sum()) or 0
    val = mb_df[mb_df["energy_code"].astype(str).str.startswith("9900")][
        "co2_adjusted_emissions_zeb"
    ].sum()
    credit_certificate_tco2_2013 = val if val else 0
    logger.debug(f"証書CO2排出値（基準年）: {credit_certificate_tco2_2013}")

    all_tco2_2013 = max(all_tco2_2013 - credit_certificate_tco2_2013, 0)

    # 合計
    total_TCO2_result = (
        0
        if all_tco2_2013 == 0
        else max(0, (all_tco2_2013 - all_tco2_this_year) / all_tco2_2013)
    )
    logger.debug(f"合計TCO2削減率: {total_TCO2_result}")

    total_TCO2_last_result = (
        0
        if all_tco2_2013 == 0
        else max(0, (all_tco2_2013 - all_tco2_last_year) / all_tco2_2013)
    )

    # 証書・クレジット
    credit_certificate_result = (
        0
        if all_tco2_2013 == 0
        else (
            credit_certificate_elecric_co2zeb_this_year
            + credit_certificate_heat_co2zeb_this_year
            + credit_certificate_other_amount_this_year
        )
        / all_tco2_2013
    )

    logger.debug(f"証書・クレジット比率: {credit_certificate_result}")

    mb_df_sub = mb_df[mb_df["supplier_reg_no"] == "REENE"]

    renewable_electric_power_2013 = (
        (mb_df_sub["energy_quantity_for_law"].sum()) or 0
    ) * 1000

    renewable_electric_power_TCO2_2013 = (
        renewable_electric_power_2013 * co2_coefficient_eletric_2013
    )

    # 再エネ発電導入
    renewable_electric_power = (
        0 if all_tco2_2013 == 0 else renewable_electric_power_TCO2_2013 / all_tco2_2013
    )

    logger.debug(f"再エネ発電導入比率: {renewable_electric_power}")

    total_energy_use_current = (mb_df["heat_converted_energy_usage"].sum()) or 0

    total_energy_use_last = (mb_df["last_year_heat_converted_energy_usage"].sum()) or 0

    total_energy_use_2023 = (mb_df["heat_converted_energy_usage_zeb"].sum()) or 0

    # 計算結果を返す
    return {
        "cn_zeb_total_tco2_result": total_TCO2_result,
        "cn_zeb_credit_certificate": credit_certificate_result,
        "cn_zeb_renewable_electric_power": renewable_electric_power,
        "cn_zeb_emission_factor_improvement": max(
            total_TCO2_result - credit_certificate_result - renewable_electric_power, 0
        ),
        "renewable_energy_procurement_current": float(total_energy_use_2023)
        * float(total_TCO2_result),
        "total_energy_use_current": total_energy_use_current,
        "renewable_energy_procurement_last": float(total_energy_use_2023)
        * float(total_TCO2_last_result),
        "total_energy_use_last": total_energy_use_last,
    }


def safe_round(value, ndigits=5):
    if value is None or value == "" or str(value).lower() == "none":
        return value
    try:
        return round(float(value), ndigits)
    except (ValueError, TypeError):
        return value


def to_filters_df(filters):
    return pd.DataFrame(
        [{"group_id": int(f.group_no), "option_no": int(f.option_no)} for f in filters]
    )


def pick(o, key, default=None):
    if o is None:
        return default
    if isinstance(o, dict):
        return o.get(key, default)
    return getattr(o, key, default)


def getTcnapp_org_id_bk(session, dto):
    """TCnApplicationInfoのorg_idを取得"""
    org_id = (
        session.query(TCnApplicationInfo.org_id)
        .filter(
            TCnApplicationInfo.corporate_number == dto.corporate_number,
            TCnApplicationInfo.agreement_category == dto.agreement_category,
            TCnApplicationInfo.fiscal_year == dto.fiscal_year,
            TCnApplicationInfo.registration_seq == getattr(dto, "registration_seq", 0),
            TCnApplicationInfo.delete_flg.is_(False),
        )
        .scalar_one_or_none()
    )

    if org_id is None:
        return None

    return org_id


def getTcnapp_org_id(session, dto):
    org_id = (
        session.query(TCnApplicationInfo.org_id)
        .filter(
            TCnApplicationInfo.corporate_number == dto.corporate_number,
            TCnApplicationInfo.agreement_category == dto.agreement_category,
            TCnApplicationInfo.fiscal_year == str(dto.fiscal_year),
            TCnApplicationInfo.registration_seq == getattr(dto, "registration_seq", 0),
            TCnApplicationInfo.delete_flg.is_(False),
        )
        .one_or_none()
    )

    return org_id[0] if org_id else None


def get_fiscal_year(year_month: str) -> int:
    year = int(year_month[:4])
    month = int(year_month[4:6])

    if month >= 4:
        return year
    else:
        return year - 1
