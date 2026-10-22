import os

from flask import Response, current_app

from cndx_corp_back.common.decorators import service
from cndx_corp_back.logic.file.fsMount_file_download_component import (
    FsMountFileDownloadComponent,
)


class FsMountFileDownloadService:

    @service
    def execute(self, file_path: str, logger=None) -> Response:
        """
        FsMountからファイルをダウンロードする
        """
        if logger is None:
            logger = current_app.logger

        logger.info(
            f"[DEBUG] FsMountFileDownloadService.execute開始: file_path={file_path}"
        )
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        logger.info(f"処理対象ファイル名：{file_path}")

        # FsMountファイルダウンロード comp を呼出
        logger.info("[DEBUG] FsMountFileDownloadComponentを呼び出し")
        file_response: Response = FsMountFileDownloadComponent().execute(
            file_path=file_path, logger=logger
        )

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        logger.info("[DEBUG] FsMountFileDownloadService.execute終了")

        return file_response
