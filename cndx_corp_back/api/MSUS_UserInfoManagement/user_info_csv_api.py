import os
from datetime import datetime

from flask import Response, abort, current_app, jsonify, request
from flask.views import MethodView
from pydantic import ValidationError

from cndx_corp_back.api.MSUS_UserInfoManagement import mst_user_info_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.MSUS_UserInfoManagement.user_info_csv_service import (
    UserInfoCsvService,
)
from cndx_corp_back.utils.utils import get_message


class UserInfoCsvApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):
        """
        POST: ユーザー一覧CSVダウンロード処理
        """

        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)}処理開始。")
        try:
            # サービスを呼び出す
            if isinstance(user_context, dict):
                user_id = user_context.get("user_id") or None
                role_id = user_context.get("role") or None
                org_id = user_context.get("org_id") or None
            else:
                user_id = None
                role_id = None
                org_id = None
            csv_generator = UserInfoCsvService().get_user_info_csv(
                dict_request_data, user_id, role_id, org_id
            )

            current_time = datetime.now()
            # YYYYMMDDhhmmss 形式
            timestamp_str = current_time.strftime("%Y%m%d%H%M%S")

            # ファイル名を m_user_現在日付.csv の形式で作成
            filename = f"m_user_{timestamp_str}.csv"
            # FlaskのResponseにジェネレータを渡し、ストリーミング応答を作成
            response = Response(csv_generator, mimetype="text/csv")
            # ファイル名とSJISエンコーディングを設定
            response.headers["Content-Disposition"] = (
                f'attachment; filename="{filename}"'
            )
            response.headers["Content-Type"] = "text/csv; charset=Shift_JIS"

            logger.info(f"{os.path.basename(__file__)}処理終了。")

            return response

        except Exception as e:
            logger.error(f"データ取得エラー: {str(e)}")
            return (
                jsonify(
                    {
                        "error": get_message(
                            "FAILURE", field="ユーザー一覧CSVダウンロード"
                        )
                    }
                ),
                500,
            )


# ルート登録
mst_user_info_csv_view = UserInfoCsvApi.as_view("user_info_csv_api")
mst_user_info_bp.add_url_rule(
    "/csv/download", view_func=mst_user_info_csv_view, methods=["POST"]
)
