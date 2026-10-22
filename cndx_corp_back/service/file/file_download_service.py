import os
from dataclasses import dataclass, field
from io import BytesIO
from typing import List

from flask import Response, abort, current_app
from flask_jwt_extended import get_jwt_identity
from pandas import DataFrame, ExcelFile
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common.dag.call_dag import call_register_dag
from cndx_corp_back.common.decorators import service
from cndx_corp_back.common.load_master import mst_data
from cndx_corp_back.logic.building_vis.file_validator import FileValidation
from cndx_corp_back.logic.file.energy_input_check_component import (
    EnergyInputCheckComponent,
)
from cndx_corp_back.logic.file.file_download_component import FileDownloadComponent
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


class FileDownloadService:

    @service
    def execute(self, file_path: str, logger=None) -> Response:
        """
        入力シートファイル検証し転送する
        """
        if logger is None:
            logger = current_app.logger
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        logger.info(f"処理対象ファイル名：{file_path}")

        # ファイル転送 comp を呼出
        file_response: Response = FileDownloadComponent().execute(file_path=file_path)

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return file_response
