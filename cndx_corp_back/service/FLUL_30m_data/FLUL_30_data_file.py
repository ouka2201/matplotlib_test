import os

from flask import current_app
from werkzeug.datastructures import FileStorage

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.file.data_extract_component import (
    FileDataExtractComponent,
)
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent
from cndx_corp_back.utils.dto_utils import include


class Per30mDataFileService:

    @service
    def upload_30m_data_file(
        self, file: FileStorage, encoding, dto, userid, logger=None
    ) -> None | list:
        """
        30分値データをアップロード

        チェックエラーがある場合はメッセージリストを返却
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        # 解析登録 comp を呼出
        message_list = FileDataExtractComponent().get_data_from_30m_data(
            file, encoding, dto, userid
        )

        if message_list:
            return message_list

        # csv ファイルをアップロード
        # dir_data = include(dto.dump(), {"corp_number", "building_id"})
        # put_dir_path = "corp/per_30m_data"
        # アップロード comp を呼出
        # FileTransferComponent().excute(
        #     file=file, dir_data=dir_data, put_dir_path=put_dir_path
        # )

        return []
