import os

from flask import current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.file.fsMount_file_check_component import (
    FsMountFileCheckComponent,
)


class FsMountFileCheckService:

    @service
    def execute(self, file_path: str, logger=None) -> bool:
        """
        FsMount上にファイルが存在するかをチェックする
        """
        if logger is None:
            logger = current_app.logger

        logger.info(
            f"[DEBUG] FsMountFileCheckService.execute開始: file_path={file_path}"
        )
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        logger.info(f"処理対象ファイル名：{file_path}")

        # FsMountファイル存在チェック comp を呼出
        logger.info("[DEBUG] FsMountFileCheckComponentを呼び出し")
        exists: bool = FsMountFileCheckComponent().execute(
            file_path=file_path, logger=logger
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        logger.info(f"[DEBUG] FsMountFileCheckService.execute終了: exists={exists}")
        return exists
