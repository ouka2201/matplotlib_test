import os
import re
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from flask import abort, current_app
from pydantic import ValidationError
from sqlalchemy import and_, case, func, insert, literal, select
from sqlalchemy.orm import aliased, scoped_session
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common.constants_values import ReportTypeValue
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import log_time, service
from cndx_corp_back.dto.report.cn_karte_create_vis_extended_dto import (
    CreateCnKarteVisExtendedDto,
)
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
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.ext import db
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent

# ※ 「CNカルテ（PDF）本体の作成」を再有効化する場合のみ import してください
from cndx_corp_back.logic.report.report_create_component import (
    CreationInfo,
    ReportCreateComponent,
)
from cndx_corp_back.service.backdata_report_create_service import (
    BackdataReportCreateComponent,
)
from cndx_corp_back.service.kesson_report_create_service import (
    KessonReportCreateComponent,
)
from cndx_corp_back.service.kpi_report_create_service import KpiReportCreateComponent
from cndx_corp_back.utils.utils import get_message


class ReportPdfCreateService:

    # ----------------------------------------------------------------------
    # メイン処理
    # ----------------------------------------------------------------------
    @service
    # @log_time
    def execute(
        self,
        dto,
        raw_request: Dict[str, Any] | None = None,
        user_id: str = "system",
        login_org_id: str = "system",
        logger=None,
    ):
        """
        画面からのDTO + 生リクエストを受け取り、拡張DTOを構築して帳票生成を実行する。

        引数:
          - dto: 画面DTO（CreateCnKarteVisInDto or ElectricityVisCreateInDto想定）
          - raw_request: リクエストJSON（任意、足りないキーを補完する目的）
        戻り値:
          - dict: レスポンス用の簡易情報（creation_id 等）
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 処理開始。")

        # ログインユーザーの組織IDで設定
        # dto.org_id = login_org_id

        # DTOの種類によって処理を分岐
        if isinstance(dto, ElcInDto):
            return self._execute_electricity_vis_report(
                dto, raw_request, login_org_id, user_id, logger
            )
        else:
            return self._execute_cn_karte_report(
                dto, raw_request, login_org_id, user_id, logger
            )

    @log_time
    def _execute_cn_karte_report(self, dto, raw_request, login_org_id, user_id, logger):
        """CNカルテレポート処理"""
        # 1) 画面DTO（by_alias=False）とリクエストJSONをマージ
        merged_payload: Dict[str, Any] = {
            **(
                dto.model_dump(by_alias=False, exclude_none=True)
                if hasattr(dto, "model_dump")
                else dict(dto)
            ),
            **(raw_request or {}),
        }
        logger.debug(f"統合ペイロード: {merged_payload}")

        # 2) 拡張DTOの生成
        try:
            extended_dto = CreateCnKarteVisExtendedDto(**merged_payload)
        except ValidationError as e:
            logger.error(f"拡張DTOの構築に失敗: {e}")
            raise

        building_id_filter = None  # "ALL" / 仮想ID / 実ID / "GROUP"
        result_dict = None

        if "building_ids_for_single" in raw_request and (
            raw_request["building_ids_for_single"] != []
        ):
            building_id_filter = raw_request.get("building_ids_for_single", None)

        if building_id_filter is None:
            self.report_print_proccess(
                extended_dto, login_org_id, user_id, raw_request, logger
            )
        else:
            # 複数単拠点の場合、拠点ごと一個ずつ作成
            # for building_ids_for_single in building_id_filter:
            #     raw_request["building_ids_for_single"] = [building_ids_for_single]
            self.report_print_proccess(
                extended_dto, login_org_id, user_id, raw_request, logger
            )

        logger.info(f"{os.path.basename(__file__)} 処理終了。")

        return result_dict

    def report_print_proccess(self, dto, login_org_id, user_id, raw_request, logger):
        # creation_id発行
        epoch_sec = int(datetime.now(ZoneInfo("Asia/Tokyo")).timestamp())
        base_creation_id = f"{user_id}_{epoch_sec}"

        # レポート生成 comp を呼出
        ReportCreateComponent(base_creation_id, True).create_cn_karte(
            dto, login_org_id, user_id
        )

        # --- レスポンス用辞書 ---
        result_dict = {
            "creation_id": base_creation_id,
            "target_type": dto.target_type,
            "report_type": dto.report_type,
        }
        # csvファイル出力
        result_dict = self._execute_cn_vis_csv_report(
            dto,
            raw_request,
            base_creation_id,
            result_dict,
            user_id,
            login_org_id,
            logger,
        )

    @log_time
    def _execute_cn_vis_csv_report(
        self,
        extended_dto,
        raw_request,
        base_creation_id,
        result_dict,
        user_id,
        login_org_id,
        logger,
    ):
        # 検索条件対象建物情報取得
        if (
            extended_dto.need_data_insufficiency_list
            or extended_dto.need_report_backdata
            or extended_dto.need_kpi_list
        ):

            where_base = []
            building_id_filter = None  # "ALL" / 仮想ID / 実ID / "GROUP"
            if "building_ids_for_single" in raw_request:
                building_id_filter = raw_request.get("building_ids_for_single", None)

            group_items = (
                raw_request.get("group_for_multibuilding") or []
            )  # ★ 追加：グループ条件
            # === フィルタ判定 ===
            # グループ指定：group_items があれば優先（building_id の文字は無視）
            # グループ検索条件
            if len(group_items) > 0:
                # ★ group_items -> group1..5 の AND 条件へ展開
                for gi in group_items:
                    gid = int(gi.get("group_no"))
                    ono = str(gi.get("option_no"))
                    col = getattr(MBuilding, f"group{gid}", None)
                    if col is not None and ono not in (None, ""):
                        where_base.append(col == ono)
            else:
                # 単拠点（または旧"GROUP"だが条件なし）→ building_id で絞る
                if building_id_filter:
                    where_base.append(MBuilding.building_id.in_(building_id_filter))
                # "ALL" の場合はそのまま（全拠点）

            where_base.append(
                MBuilding.corporate_number == raw_request.get("corporate_number")
            )
            where_base.append(
                MBuilding.agreement_category == raw_request.get("agreement_category")
            )
            where_base.append(MBuilding.delete_flg.is_not(True))

            # --- 建物マスタ情報取得SQL ---
            with get_scoped_session() as session:
                # 同じテーブルの重複参照を避けるためにエイリアスを使用
                TBI = aliased(TBuildingInfo)
                # 以降の TBuildingInfo 参照はエイリアスに紐付け、重複した FROM を回避
                # 注意: TBuildingInfo を再代入しない。Python にローカル変数と見なされるのを避ける
                building_stmt = (
                    session.query(
                        MBuilding.building_id,
                        MBuilding.corporate_number.label("法人番号"),
                        MBuilding.agreement_category.label("同意書取得区分"),
                        MBuilding.org_id.label("組織ID"),
                        MBuilding.group1.label("グループ1"),
                        MBuilding.group2.label("グループ2"),
                        MBuilding.group3.label("グループ3"),
                        MBuilding.group4.label("グループ4"),
                        MBuilding.group5.label("グループ5"),
                        MBuilding.location_identifier_code.label("拠点識別番号"),
                        MBuilding.location_identifier_name.label("拠点識別名"),
                        MBuilding.gross_floor_area.label("延床面積"),
                        literal("").label("KPI省エネ率"),
                        literal("").label("KPI電化率"),
                        literal("").label("KPI創エネ"),
                        literal("").label("KPICN率"),
                        PrefectureMst.pref_nm.label("住所都道府県"),
                        TBI.address_city.label("住所"),
                        func.coalesce(
                            TBI.ep_customer_number, MBuilding.ep_customer_number
                        ).label("お客さま番号"),
                        TBI.supply_point_number.label("供給地点特定番号"),
                        TBI.industry_class_detail_name.label("業種"),
                        TBI.industry_class_detail_code.label("業種コード"),
                        TBI.ep_office_code.label("事業所コード"),
                        TBI.location_identifier_name.label("拠点名"),
                        TBI.gross_floor_area.label("延床（㎡）"),
                        TBI.energy_benchmark_target_industry.label(
                            "省エネ法ベンチマーク業種"
                        ),
                        TBI.energy_benchmark_indicator.label(
                            "省エネ法ベンチマーク指標"
                        ),
                        TBI.energy_saving_denominator.label("省エネ率分母"),
                        # MBuilding.energy_benchmark_index_denominator.label("省エネ法ベンチマーク指標分母"),
                        TBI.competitor_industry_co2_avg.label("他社比較業種"),
                        case(
                            (
                                (len(group_items) > 0) | (len(building_id_filter) > 0),
                                literal(1),
                            ),
                            else_=literal(0),
                        ).label("判定フラグ"),
                    )
                    .select_from(MBuilding)
                    .outerjoin(
                        TBI,
                        and_(
                            TBI.corporate_number == MBuilding.corporate_number,
                            TBI.agreement_category == MBuilding.agreement_category,
                            TBI.building_id == MBuilding.building_id,
                            TBI.registration_seq == 0,
                            TBI.delete_flg.is_not(True),
                            TBI.fiscal_year == raw_request["start_year"],
                        ),
                    )
                    .outerjoin(
                        PrefectureMst, PrefectureMst.pref_cd == TBI.address_prefecture
                    )
                    .where(and_(*where_base))
                    .all()
                )

                # グループ名取得
                group_stmt = (
                    session.query(
                        MBuildingGroup.corporate_number.label("法人番号"),
                        MBuildingGroup.agreement_category.label("同意書取得区分"),
                        MBuildingGroup.org_id.label("組織ID"),
                        MBuildingGroup.group_id.label("グループID"),
                        MBuildingGroup.select_item1.label("選択肢１"),
                        MBuildingGroup.select_item2.label("選択肢２"),
                        MBuildingGroup.select_item3.label("選択肢３"),
                        MBuildingGroup.select_item4.label("選択肢４"),
                        MBuildingGroup.select_item5.label("選択肢５"),
                        MBuildingGroup.select_item6.label("選択肢６"),
                        MBuildingGroup.select_item7.label("選択肢７"),
                    )
                    .where(
                        MBuildingGroup.corporate_number
                        == raw_request.get("corporate_number"),
                        MBuildingGroup.agreement_category
                        == raw_request.get("agreement_category"),
                        # MBuildingGroup.org_id == raw_request.get("org_id"),
                        MBuildingGroup.delete_flg.is_not(True),
                    )
                    .all()
                )

            # 絞り対象建物情報取得
            df_building = pd.DataFrame(
                [
                    {field: getattr(row, field) for field in row._fields}
                    for row in building_stmt
                ],
                dtype=str,
            )
            df_building_group = pd.DataFrame(
                [
                    {field: getattr(row, field) for field in row._fields}
                    for row in group_stmt
                ],
                dtype=str,
            )

            if df_building.empty:
                abort(400, description=get_message("BUILDING_INFO_NOT_EXSIT"))
            if df_building_group.empty:

                columns = [
                    "法人番号",
                    "同意書取得区分",
                    "組織ID",
                    "グループID",
                    "選択肢１",
                    "選択肢２",
                    "選択肢３",
                    "選択肢４",
                    "選択肢５",
                    "選択肢６",
                    "選択肢７",
                ]
                df_building_group = pd.DataFrame(columns=columns)

            df_building = set_group_info(df_building, df_building_group)

        # ===================== 1. 欠損一覧（PDF or ZIP） =====================
        if extended_dto.need_data_insufficiency_list:
            kesson_files = KessonReportCreateComponent(base_creation_id).create_files(
                df_building,
                dto=extended_dto,
                logger=logger,
                return_type="fileobj",  # fileobj と filename が返る
            )

            kesson_path_dict = {
                "put_sub_path": "/".join(
                    [
                        "cn_profile",
                        extended_dto.org_id,
                        extended_dto.agreement_category,
                        extended_dto.corporate_number,
                        extended_dto.start_year,
                    ]
                )
            }
            file_upload = FileTransferComponent()

            kesson_saved_paths = []
            if not kesson_files:
                logger.warning(
                    "Kesson: create_files() からファイルが返りませんでした。"
                )

            for item in kesson_files:
                b_id = item["building_id"]  # 実ID / GROUP / ALL
                fileobj = item["fileobj"]  # BytesIO
                filename = item["filename"]  # 例: kesson_bundle_....zip
                mimetype = item.get("mimetype", "application/zip")

                fs = FileStorage(
                    stream=fileobj, filename=filename, content_type=mimetype
                )

                saved_path_str = None
                try:
                    upload_target_path = file_upload.get_upload_path(
                        target_path_dict=kesson_path_dict
                    )  # Path
                    upload_dir_str = str(upload_target_path)
                    saved_path_str = os.path.join(upload_dir_str, filename)

                    # 転送実行（component 内で filename を使って保存される）
                    file_upload.excute(
                        input_file=fs, upload_target_path=upload_target_path
                    )
                except Exception as e:
                    logger.error(e)
                    abort(500)
                finally:
                    try:
                        if fs.stream and hasattr(fs.stream, "close"):
                            fs.stream.close()
                        # noqa: B901
                    except Exception:
                        pass

                if saved_path_str:
                    per_creation_id = f"{base_creation_id}_{b_id}"
                    # report_classify: "3" = 欠損一覧
                    self.insert_report_record(
                        extended_dto,
                        b_id,
                        ReportTypeValue.MISSING_DATA_PDF.value,
                        saved_path_str,
                        logger,
                        user_id,
                        creation_id=per_creation_id,
                        login_org_id=login_org_id,
                    )
                    kesson_saved_paths.append(saved_path_str)
                else:
                    logger.error(
                        "Kesson: saved_path_str が未設定のため、DB 登録をスキップしました。"
                    )

            result_dict["kesson_report_paths"] = kesson_saved_paths

        # ===================== 2. レポートバックデータ（CSV / ZIP） =====================
        if extended_dto.need_report_backdata:
            backdata_files = BackdataReportCreateComponent(
                base_creation_id
            ).create_files(
                df_building, dto=extended_dto, logger=logger, return_type="fileobj"
            )

            backdata_path_dict = {
                "put_sub_path": "/".join(
                    [
                        "cn_profile",
                        extended_dto.org_id,
                        extended_dto.agreement_category,
                        extended_dto.corporate_number,
                        extended_dto.start_year,
                    ]
                )
            }
            file_upload = FileTransferComponent()

            backdata_saved_paths = []
            if not backdata_files:
                logger.warning(
                    "Backdata: create_files() からファイルが返りませんでした。"
                )

            for item in backdata_files:
                b_id = item["building_id"]  # 実ID / GROUP / ALL
                fileobj = item["fileobj"]
                filename = item["filename"]  # 例: cn_backdata_....csv / .zip
                mimetype = item.get("mimetype", "application/octet-stream")

                fs = FileStorage(
                    stream=fileobj, filename=filename, content_type=mimetype
                )

                saved_path_str = None
                try:
                    upload_target_path = file_upload.get_upload_path(
                        target_path_dict=backdata_path_dict
                    )
                    upload_dir_str = str(upload_target_path)
                    saved_path_str = os.path.join(upload_dir_str, filename)

                    file_upload.excute(
                        input_file=fs, upload_target_path=upload_target_path
                    )
                except Exception as e:
                    logger.error(e)
                    abort(500)
                finally:
                    try:
                        if fs.stream and hasattr(fs.stream, "close"):
                            fs.stream.close()
                    except Exception:
                        pass

                if saved_path_str:
                    per_creation_id = f"{base_creation_id}_{b_id}"
                    # report_classify: "2" = バックデータ
                    self.insert_report_record(
                        extended_dto,
                        b_id,
                        ReportTypeValue.CN_REPORT_CSV.value,
                        saved_path_str,
                        logger,
                        user_id,
                        creation_id=per_creation_id,
                        login_org_id=login_org_id,
                    )
                    backdata_saved_paths.append(saved_path_str)
                else:
                    logger.error(
                        "Backdata: saved_path_str が未設定のため、DB 登録をスキップしました。"
                    )

            result_dict["report_backdata_paths"] = backdata_saved_paths

        # ===================== 3. KPI一覧（CSV） =====================
        if extended_dto.need_kpi_list:
            kpi_files = KpiReportCreateComponent(base_creation_id).create_files(
                df_building, dto=extended_dto, logger=logger, return_type="fileobj"
            )

            kpi_path_dict = {
                "put_sub_path": "/".join(
                    [
                        "cn_profile",
                        extended_dto.org_id,
                        extended_dto.agreement_category,
                        extended_dto.corporate_number,
                        extended_dto.start_year,
                    ]
                )
            }
            file_upload = FileTransferComponent()

            kpi_report_paths = []
            if not kpi_files:
                logger.warning("KPI: create_files() からファイルが返りませんでした。")

            for item in kpi_files:
                b_id = item["building_id"]  # 実ID / GROUP / ALL
                fileobj = item["fileobj"]
                filename = item["filename"]
                mimetype = item.get("mimetype", "text/csv")

                fs = FileStorage(
                    stream=fileobj, filename=filename, content_type=mimetype
                )

                saved_path_str = None
                try:
                    upload_target_path = file_upload.get_upload_path(
                        target_path_dict=kpi_path_dict
                    )
                    upload_target_dir_str = str(upload_target_path)
                    saved_path_str = os.path.join(upload_target_dir_str, filename)

                    file_upload.excute(
                        input_file=fs, upload_target_path=upload_target_path
                    )
                except Exception as e:
                    logger.error(e)
                    abort(500)
                finally:
                    try:
                        if fs.stream and hasattr(fs.stream, "close"):
                            fs.stream.close()
                    except Exception:
                        pass

                if saved_path_str:
                    per_creation_id = f"{base_creation_id}_{b_id}"
                    # report_classify: "4" = KPI CSV
                    self.insert_report_record(
                        extended_dto,
                        b_id,
                        ReportTypeValue.KPI_CSV.value,
                        saved_path_str,
                        logger,
                        user_id,
                        creation_id=per_creation_id,
                        login_org_id=login_org_id,
                    )
                    kpi_report_paths.append(saved_path_str)
                else:
                    logger.error(
                        "KPI: saved_path_str が未設定のため、DB 登録をスキップしました。"
                    )

            result_dict["kpi_report_paths"] = kpi_report_paths

        return result_dict

    @log_time
    def _execute_electricity_vis_report(
        self, dto: ElcInDto, raw_request, login_org_id, user_id, logger
    ):
        """電力見える化レポート処理"""
        logger.info("電力見える化レポート処理開始")

        # creation_id / 作成者を補正
        dto.user_id = user_id
        epoch_sec = int(datetime.now(ZoneInfo("Asia/Tokyo")).timestamp())
        base_creation_id = f"{user_id}_{epoch_sec}"

        # レポート生成 comp を呼出（PostgreSQL保存モード）
        ReportCreateComponent(base_creation_id, True).create_cn_karte(
            dto, login_org_id, user_id
        )

        return []

    def create_cn_report_bnk(self, dto: InDto, user_id, login_org_id, logger):
        """CNカルテレポート処理"""

        report_created_by = user_id

        epoch_sec = int(datetime.now(ZoneInfo("Asia/Tokyo")).timestamp())
        base_creation_id = f"{report_created_by}_{epoch_sec}"

        # dto.org_id = login_org_id

        # レポート生成 comp を呼出
        ReportCreateComponent(base_creation_id, True).create_cn_karte(
            dto, login_org_id, user_id
        )

    # ----------------------------------------------------------------------
    # t_report_storage_info への登録共通処理
    #   ※ site_selection_type / format_type は“コード”で保存する（01/02/03）
    #   ※ グループ作成時のみ group1～group5 を保存（番号）。個別・企業全体は NULL。
    # ----------------------------------------------------------------------
    @log_time
    def insert_report_record(
        self,
        dto: CreateCnKarteVisExtendedDto,
        building_id: str,
        report_classify: int,
        path: str,
        logger,
        report_created_by: str,
        creation_id: str,
        login_org_id: str,
    ):

        # グループ判定（02=グループ）
        is_group = getattr(dto, "site_selection_type_code", None) == "02"

        # グループの選択番号を抽出（グループ以外は None のまま）
        gcols = {f"group{i}": None for i in range(1, 6)}
        if (is_group and getattr(dto, "group_for_multibuilding", None)) or getattr(
            dto, "building_ids_for_single", None
        ):

            session: scoped_session = db.session
            engine = session.get_bind()

            # 建物基本情報取得
            building_stmt = select(MBuildingGroup).where(
                MBuildingGroup.corporate_number
                == getattr(dto, "corporate_number", None),
                MBuildingGroup.agreement_category
                == getattr(dto, "agreement_category", None),
                MBuildingGroup.org_id == getattr(dto, "org_id", None),
            )
            building_df = pd.read_sql(building_stmt, engine)

            gcols = {}
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
                    MBuilding.org_id == getattr(dto, "org_id", None),
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
                    df_group_name = ReportCreateComponent.pick_group_options(
                        building_df, group_filters
                    )
            else:
                if (
                    getattr(dto, "group_for_multibuilding", None) is None
                    or getattr(dto, "group_for_multibuilding", None) == ""
                ):
                    df_group_name = pd.DataFrame()
                else:
                    df_group_name = ReportCreateComponent.pick_group_options(
                        building_df, getattr(dto, "group_for_multibuilding", None)
                    )
            gcols = ReportCreateComponent.extract_groups_from_df(self, df_group_name)

            # 単拠点配列が指定され、かつグループ指定がない場合は、
            # MBuilding の group1..group5 数値を基に MBuildingGroup の選択肢ラベルへ置き換える
            if (
                not (is_group and getattr(dto, "group_for_multibuilding", None))
            ) and getattr(dto, "building_ids_for_single", None):
                try:
                    mb_row = (
                        session.query(MBuilding)
                        .filter(
                            MBuilding.corporate_number
                            == getattr(dto, "corporate_number", None),
                            MBuilding.agreement_category
                            == getattr(dto, "agreement_category", None),
                            MBuilding.org_id == getattr(dto, "org_id", None),
                            MBuilding.building_id == building_id,
                        )
                        .first()
                    )
                except Exception:
                    mb_row = None

                if mb_row is not None and not building_df.empty:
                    new_gcols = {f"group{i}": None for i in range(1, 6)}
                    for i in range(1, 6):
                        label_value = None
                        raw_val = getattr(mb_row, f"group{i}", None)
                        if raw_val is not None and str(raw_val).strip() != "":
                            try:
                                sel_idx = int(str(raw_val).strip())
                            except ValueError:
                                sel_idx = None

                            if sel_idx is not None and 1 <= sel_idx <= 7:
                                try:
                                    grp_rows = building_df[
                                        building_df["group_id"].astype(str) == str(i)
                                    ]
                                    if not grp_rows.empty:
                                        col_name = f"select_item{sel_idx}"
                                        if col_name in grp_rows.columns:
                                            val = grp_rows.iloc[0][col_name]
                                            label_value = None if pd.isna(val) else val
                                except Exception:
                                    label_value = None
                        new_gcols[f"group{i}"] = label_value
                    gcols = new_gcols

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

        # t_report_storage_info へ登録（group1～group5 を含む）
        timestamp = self.getLocalTime()
        stmt = insert(TReportStorageInfo).values(
            # creation_id=dto.creation_id,
            creation_id=creation_id,
            building_id=building_id,  # "ALL" / "GROUP" / 実ID
            report_classify=report_classify,
            corporate_number=dto.corporate_number,
            agreement_category=dto.agreement_category,
            org_id=login_org_id,
            fiscal_year=dto.start_year,
            registration_seq=0,
            report_save_path=path,
            report_status=None,  # 生成直後は未ダウンロード等
            report_selection_period_from=f"{dto.start_year}{dto.start_month}",
            # コード保存（00=簡易, 01=標準）
            format_type=getattr(dto, "format_type_code", None),
            # コード保存（01=企業全体, 02=グループ, 03=個別）
            site_selection_type=getattr(dto, "site_selection_type_code", None),
            # ここが今回の追加ポイント
            group1=group_values[0],
            group2=group_values[1],
            group3=group_values[2],
            group4=group_values[3],
            group5=group_values[4],
            report_created_at=timestamp,
            report_created_by=dto.user_email,
            created_by=report_created_by,
            # created_at=timestamp,
        )

        db.session.execute(stmt)
        db.session.commit()
        db.session.close()

        logger.info(
            "t_report_storage_info 登録完了: "
            f"classify={report_classify}, building_id={building_id}, path={path}, "
            f"format_type={dto.format_type_code}, site_selection_type={dto.site_selection_type_code}, "
            f"group=({gcols['group1']},{gcols['group2']},{gcols['group3']},{gcols['group4']},{gcols['group5']})"
        )

    def getLocalTime(self):
        utc_time = datetime.now(timezone.utc)
        now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
        timestamp = (
            now_local.strftime("%Y/%m/%d %H:%M:%S")
            + f".{int(now_local.microsecond / 1000):03d}"
        )
        return timestamp

    # ----------------------------------------------------------------------
    # 内部ユーティリティ
    # ----------------------------------------------------------------------
    def _get_user_id(self, logger) -> str:
        """
        ユーザーIDを取得するヘルパー関数
        - JWT が取得できない場合は "system" を返す
        """
        try:
            from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
        except Exception as e:
            logger.error(f"JWTからユーザーIDの取得に失敗: {str(e)}")
            user_id = None
        return user_id or "system"


@log_time
def set_group_info(df1, df2):
    KEYS = ["法人番号", "同意書取得区分", "組織ID"]

    for k in KEYS:
        df1[k] = df1[k].astype(str)
        df2[k] = df2[k].astype(str)

    fw2hw = str.maketrans("０１２３４５６７８９", "0123456789")

    def num_from_name(s):
        m = re.search(r"[0-9０-９]+", str(s))
        return int(m.group(0).translate(fw2hw)) if m else None

    group_cols = [
        c for c in df1.columns if re.fullmatch(r"グループ[0-9０-９]+", str(c))
    ]
    group_cols = [c for c in group_cols if 1 <= num_from_name(c) <= 5]

    opt_cols = [c for c in df2.columns if c.startswith("選択肢")]
    df2_long = df2.melt(
        id_vars=KEYS + ["グループID"],
        value_vars=opt_cols,
        var_name="選択肢列",
        value_name="選択肢値",
    )
    df2_long["選択肢番号"] = (
        df2_long["選択肢列"]
        .str.extract(r"([0-9０-９]+)")[0]
        .str.translate(fw2hw)
        .astype("Int64")
    )

    df2_key = df2_long[KEYS + ["グループID", "選択肢番号", "選択肢値"]].copy()

    df2_key["グループID"] = pd.to_numeric(
        df2_key["グループID"], errors="coerce"
    ).astype("Int64")

    for gcol in group_cols:
        gid = num_from_name(gcol)

        tmp = df1[KEYS + [gcol]].copy()
        tmp["_i"] = np.arange(len(tmp))
        tmp["グループID"] = gid
        tmp["選択肢番号"] = pd.to_numeric(tmp[gcol], errors="coerce").astype("Int64")

        merged = tmp.merge(
            df2_key,
            on=KEYS + ["グループID", "選択肢番号"],
            how="left",
        ).sort_values("_i")

        df1.loc[:, gcol] = merged["選択肢値"].values

    return df1.astype("object").where(pd.notna(df1), None)


def extract_num(s: str) -> int:
    """列名や文字列から数字を抽出する（全角／半角に対応）"""
    m = re.search(r"[0-9０-９]+", str(s))
    return int(m.group(0)) if m else None


def _get_gross_area(recs: list[TBuildingInfo], start_month):
    weight_1 = (4 - start_month) % 12

    return recs[0].gross_floor_area * weight_1 + recs[1].gross_floor_area * (
        12 - weight_1
    )
