import os
import traceback

from flask import current_app

from cndx_corp_back.common.decorators import component


class FsMountFileCheckComponent:

    @component
    def execute(self, file_path: str, logger=None) -> bool:
        """
        FsMount上にファイルが存在するかをチェックする
        osライブラリを使用してファイルサーバのパスを参照
        """
        if logger is None:
            logger = current_app.logger

        logger.info(
            f"[DEBUG] FsMountFileCheckComponent.execute開始: file_path={file_path}"
        )
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        logger.info(f"チェック対象ファイルパス：{file_path}")

        try:
            # osライブラリを使用してファイルの存在とアクセス権限をチェック
            logger.info(f"[DEBUG] ファイル存在チェック実行: file_path={file_path}")
            exists = os.path.isfile(file_path) and os.access(file_path, os.R_OK)

            if not exists:
                logger.warning(
                    f"FsMountファイルが存在しないかアクセスできません: {file_path}"
                )
            else:
                logger.info(f"FsMountファイルが存在します: {file_path}")

            logger.info(f"{os.path.basename(__file__)}処理終了。")
            logger.info(
                f"[DEBUG] FsMountFileCheckComponent.execute終了: exists={exists}"
            )
            return exists
        except Exception as e:
            logger.error(f"FsMountファイル存在チェックでエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            return False
