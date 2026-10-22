import io
import os
from base64 import b64encode

from flask import abort, current_app

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import service
from cndx_corp_back.common.hadoop_manager import get_from_hdfs
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.utils.utils import get_message


class CnKarteDownloadService:
    """
    レポートステータス管理サービス
    """

    parameters = {"corporate_number", "fiscal_year"}

    @service
    def execute(self, request_dict: dict, download_all: bool = False, logger=None):
        """レポート取得"""

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")

        if download_all:
            self.parameters.pop("fiscal_year")

        with get_scoped_session() as session:
            rp_infos = session.query(TReportStorageInfo).filter_by(
                **request_dict, report_classify="1"
            )
            rp_info = rp_infos.first()

        if rp_info is None:
            if logger:
                logger.info("該当レコードなし、ダウンロード失敗。")
            abort(404, description=get_message("NOT_FOUND", item_name="該当レコード"))

        file_name = os.path.basename(rp_info.report_save_path)

        with open(rp_info.report_save_path, "rb") as f:
            pdf_bytes = f.read()  # ファイルの内容を読み込む

        pdf_stream = io.BytesIO(pdf_bytes)

        # TODO 正式
        # pdf_stream=get_from_hdfs("dtap://TenantStorage/corp/report_pdf_files/入力シート０２銀行/入力シートアップロード画面０２株式会社/2024/企業カルテ_入力シート０２銀行_入力シートアップロード画面０２株式会社_2024_3.pdf")

        pdf_stream.seek(0)

        # BytesIO から base64 に
        base64_encoded = b64encode(pdf_stream.read())

        # 文字列に変換
        base64_str = base64_encoded.decode("utf-8")

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return base64_str, file_name
