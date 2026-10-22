import os
from dataclasses import dataclass, field
from io import BytesIO
from typing import List

from flask import current_app
from flask_jwt_extended import get_jwt_identity
from pandas import DataFrame, ExcelFile
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common.dag.call_dag import call_register_dag
from cndx_corp_back.common.decorators import service
from cndx_corp_back.common.load_master import mst_data
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


class FileCheckTransferService:

    @service
    def execute(
        self, file: FileStorage, dict_request_data: dict, logger=None
    ) -> list[str]:
        """
        入力シートファイル検証し転送する
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        logger.info(f"処理対象ファイル名：{file.filename}")
        if file is not None:
            # ファイルの中身を取得
            input = file.read()
            excel_file = ExcelFile(BytesIO(input))
        else:
            input = dict_request_data["file_base64"]
            excel_file = base64_to_excel(input)

        message_list = list()

        # エネルギー入力チェック comp を呼出
        EnergyInputCheckComponent().excute(input=excel_file, message_list=message_list)

        if message_list:
            return message_list

        sheet_nm = exists_sheet_like(excel_file, "記入シート")
        df: DataFrame = get_data_frame(excel_file, sheet_nm)
        df.fillna("", inplace=True)

        bank_name = df.iat[4, 10]
        company_name = df.iat[13, 10]
        reporting_year = df.iat[19, 10]
        user_id = get_jwt_identity()

        # フォルダ構成名取得
        dir_data = {
            "bank_name": bank_name,
            "company_name": company_name,
            "reporting_year": reporting_year,
        }

        # 新しいファイル名
        new_filename = (
            f"行員向け入力シート_{bank_name}_{company_name}_{reporting_year}.xlsx"
        )

        # FileStorage を新しいファイル名で再作成
        new_file = FileStorage(
            stream=file.stream, filename=new_filename, content_type=file.content_type
        )

        # ファイル転送 comp を呼出
        FileTransferComponent().excute(
            file=new_file, dir_data=dir_data, put_dir_path="/corp/input_sheet_files"
        )

        # データ登録dag実行
        call_register_dag(file, mst_data, user_id, logger)

        logger.info(f"{os.path.basename(__file__)}処理終了。")

        return message_list
