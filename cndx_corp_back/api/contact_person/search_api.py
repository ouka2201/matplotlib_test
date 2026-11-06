"""LMMGMG-API-04 営業担当者検索。"""

import traceback

from flask import Response, current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.contact_person import contact_person_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.constant.handover_constants import HANDOVER_SYSTEM_ERROR
from cndx_corp_back.service.contact_person.search_service import search_managers


class ContactPersonSearchApi(MethodView):
    """引継元・引継先の候補となる営業担当者を検索するAPI。"""

    @jwt_user_context_db(refresh=False)
    @controller
    def get(
        self,
        dict_request_data: dict,
        user_context: dict | None = None,
        logger: CorpLogger | None = None,
    ) -> tuple[Response, int]:
        """検索条件に合う営業担当者と処理結果を返す。

        Args:
            dict_request_data: リクエストから取得した検索条件と検索者情報。
            user_context: 認証処理で取得したユーザー情報。
            logger: リクエスト用のロガー。省略時はアプリのロガーを使用する。

        Returns:
            JSONレスポンスとHTTPステータスの組。成功時は担当者一覧と200を
            返す。入力エラーは400、権限エラーは403、想定外のエラーは500。
        """
        logger = logger if logger is not None else current_app.logger
        try:
            managers = search_managers(dict_request_data, user_context or {})
        except PermissionError as error:
            logger.warning("営業担当者検索：権限チェックエラー。")
            return jsonify({"message": str(error)}), 403
        except ValueError as error:
            logger.warning("営業担当者検索：入力チェックエラー。")
            return jsonify({"message": str(error)}), 400
        except Exception as error:
            # API境界で例外を統一し、検索語・SQLパラメータをログへ出さない。
            stack = "".join(traceback.format_tb(error.__traceback__))
            logger.error(f"営業担当者検索失敗：{type(error).__name__}\n{stack}")
            return jsonify({"message": HANDOVER_SYSTEM_ERROR}), 500
        return jsonify({"manager_list": managers}), 200


contact_person_bp.add_url_rule(
    "/search",
    view_func=ContactPersonSearchApi.as_view("search_api"),
    methods=["GET"],
)
