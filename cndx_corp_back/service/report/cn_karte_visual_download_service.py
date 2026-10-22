import os

from flask import abort, current_app

from cndx_corp_back.common.decorators import service


class CnKarteVisualDownloadService:
    """
    CNカルテ(可視化) ファイルダウンロードサービス
    """

    @service
    def execute(self, request_dict: dict, logger=None) -> str:
        """レポートのファイルパスを返す（DBを使わずに直接）"""

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} 処理開始")

        # --- file_name パラメータ必須 ---
        file_name = request_dict.get("file_name", "").strip()
        if not file_name:
            logger.error("file_name パラメータが不足しています")
            abort(400, description="file_name パラメータが不足しています")

        # --- 拡張子でディレクトリ分岐 ---
        if file_name.lower().endswith(".csv"):
            dir_path = "C:/HZY/FILE DOWNLOAD/CSV"
        else:
            dir_path = "C:/HZY/FILE DOWNLOAD/PDF"

        # --- パス組み立て ---
        full_path = os.path.join(dir_path, file_name)

        if not os.path.isfile(full_path):
            logger.error(f"ファイルが存在しません: {full_path}")
            abort(404, description="ファイルが見つかりません")

        logger.info(f"{os.path.basename(__file__)} 処理終了: {full_path}")
        return full_path
