import os
import traceback
from dataclasses import dataclass, field
from io import BytesIO
from typing import List

import logic.building_vis.register_vis_aggregation_Info_component as rai
from flask import current_app
from flask_jwt_extended import get_jwt_identity
from pandas import DataFrame, ExcelFile
from sqlalchemy.orm import scoped_session
from werkzeug.datastructures import FileStorage

import cndx_corp_back.logic.building.register_inputdata_info_component as rii
from cndx_corp_back.common.dag.call_dag import call_register_dag
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.common.load_master import mst_data
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.logic.building_vis.insert_vis_inputdata import (
    insert_input_table_data,
)
from cndx_corp_back.logic.building_vis.vis_building_data_check import (
    VisBuilidingDataCheck,
)
from cndx_corp_back.logic.building_vis.vis_energy_data_check import VisEnergyDataCheck
from cndx_corp_back.logic.building_vis.vis_hearing_data_check import VisHearingDataCheck
from cndx_corp_back.logic.building_vis.visualization_building_files_etl import (
    BuildingInputFileParser,
)
from cndx_corp_back.logic.building_vis.visualization_files_etl import InputFileParser
from cndx_corp_back.logic.building_vis.visualization_hearing_files_etl import (
    HearingInputFileParser,
)
from cndx_corp_back.logic.file.energy_input_check_component import (
    EnergyInputCheckComponent,
)
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent
from cndx_corp_back.utils.excel_utils import (
    base64_to_excel,
    exists_sheet_like,
    get_data_frame,
)


@dataclass
class Result:
    path: str
    file_name: str
    error_message_list: List[str] = field(default_factory=list)


class VisFileCheckService:

    def __init__(
        self,
        *,
        input_file: FileStorage,
        org_id: str,
        user_id: str,
        request_dict: dict[str, any],
        file_type: str,
        logger: CorpLogger = None,
    ) -> None:

        self.input_file: FileStorage = input_file
        self.org_id = org_id
        self.user_id = user_id
        self.request_dict = request_dict
        self.file_type = file_type
        self.logger = logger

    @service
    def execute(self, logger=None) -> list[str]:
        # 処理ファイル種別
        file_type = self.file_type

        with get_scoped_session() as session:
            if file_type == "energy":
                # エネルギーデータ
                file_check = VisEnergyDataCheck(
                    input_file=self.input_file,
                    logger=logger,
                    session=session,
                    org_id=self.org_id,
                    user_id=self.user_id,
                    request_dict=self.request_dict,
                )
            if file_type == "hearing":
                # ヒアリングデータ
                file_check = VisHearingDataCheck(
                    input_file=self.input_file,
                    logger=logger,
                    session=session,
                    org_id=self.org_id,
                    user_id=self.user_id,
                    request_dict=self.request_dict,
                )
            if file_type == "buildingMaster":
                # 建物データ
                file_check = VisBuilidingDataCheck(
                    input_file=self.input_file,
                    logger=logger,
                    session=session,
                    org_id=self.org_id,
                    user_id=self.user_id,
                    request_dict=self.request_dict,
                )

            try:
                check_ret = file_check.execute()
                if len(file_check.format_errors) > 1:
                    return file_check.format_errors
                elif len(file_check.data_errors) > 1:
                    return file_check.data_errors
                elif len(file_check.building_error_list) > 1:
                    return file_check.building_error_list
                elif len(file_check.check_file_company_name) > 1:
                    return file_check.check_file_company_name
                else:
                    return check_ret

            except Exception:
                self.logger.error("ファイルチェック処理失敗しました。")
                raise
