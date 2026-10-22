import os

from flask import abort, current_app, send_file
from flask.views import MethodView

from cndx_corp_back.api.report import report_bp
from cndx_corp_back.common.decorators import controller
from cndx_corp_back.service.report.cn_karte_visual_download_service import (
    CnKarteVisualDownloadService,
)


class CnKarteVisualDownloadApi(MethodView):
    @controller
    def get(self, dict_request_data, logger=None):
        if logger is None:
            logger = current_app.logger

        logger.info(
            f"{os.path.basename(__file__)} – CNカルテ(可視化)ファイルダウンロード処理開始"
        )

        # サービス呼び出し（ファイルパスを取得）
        file_path = CnKarteVisualDownloadService().execute(
            request_dict=dict_request_data, logger=logger
        )

        if not os.path.isfile(file_path):
            logger.error(f"ファイルが見つかりません: {file_path}")
            abort(404, description="ファイルが存在しません")

        logger.info(f"{os.path.basename(__file__)} – ダウンロード処理正常終了")

        # send_fileで直接ダウンロードさせる
        return send_file(file_path, as_attachment=True)


# ルーティング登録
cn_karte_visual_download_view = CnKarteVisualDownloadApi.as_view(
    "cn_karte_visual_download_api"
)
report_bp.add_url_rule(
    "/cn-karte/visual/download",
    view_func=cn_karte_visual_download_view,
    methods=["GET"],
)
