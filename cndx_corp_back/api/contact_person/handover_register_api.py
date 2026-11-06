import traceback

from flask import Response, current_app, jsonify
from flask.views import MethodView

from cndx_corp_back.api.contact_person import contact_person_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.common.log import CorpLogger
from cndx_corp_back.constant.handover_constants import (
    HANDOVER_SYSTEM_ERROR,
    HANDOVER_TYPE_BULK,
    HANDOVER_TYPE_INDIVIDUAL,
)
from cndx_corp_back.service.contact_person.handover_register_service import (
    register_handover,
)


def _masked_source_key(data: dict) -> str:
    """ログに出力する引継元の識別情報をマスクする。

    Args:
        data: 引継元の組織IDとユーザーIDを含む入力情報。

    Returns:
        各IDの末尾4文字だけを残した文字列。4文字以下のIDは全体を隠す。
        文字列でない値や英数字以外を含む値は出力しない。
    """
    return ", ".join(
        f"{key}=***{value[-4:] if len(value) > 4 else ''}"
        for key in ("handover_from_org_id", "handover_from_user_id")
        if isinstance(value := data.get(key), str) and value.isalnum()
    )


class HandoverApi(MethodView):
    """営業担当の個別引継登録を受け付けるAPI。"""

    handover_type = HANDOVER_TYPE_INDIVIDUAL

    @jwt_user_context_db(refresh=False)
    @controller
    def post(
        self,
        dict_request_data: dict,
        user_context: dict | None = None,
        logger: CorpLogger | None = None,
    ) -> tuple[Response, int]:
        """引継予定を登録し、処理結果を返す。

        Args:
            dict_request_data: リクエストから取得した引継の登録内容。
            user_context: 認証処理で取得したユーザー情報。
            logger: リクエスト用のロガー。省略時はアプリのロガーを使用する。

        Returns:
            JSONレスポンスとHTTPステータスの組。成功は200、入力・登録状態の
            エラーは400、権限エラーは403、想定外のエラーは500を返す。
        """
        logger = logger if logger is not None else current_app.logger
        try:
            register_handover(dict_request_data, user_context or {}, self.handover_type)
        except PermissionError as error:
            logger.warning("営業担当引継登録：権限チェックエラー。")
            return jsonify({"message": str(error)}), 403
        except ValueError as error:
            logger.warning("営業担当引継登録：入力・登録状態チェックエラー。")
            return jsonify({"message": str(error)}), 400
        except Exception as error:
            # API境界で想定外エラーを500に統一する。SQLパラメータはログに含めない。
            stack = "".join(traceback.format_tb(error.__traceback__))
            source_key = _masked_source_key(dict_request_data)
            logger.error(
                f"営業担当引継登録失敗：{type(error).__name__} "
                f"{source_key}\n{stack}"
            )
            return jsonify({"message": HANDOVER_SYSTEM_ERROR}), 500
        return jsonify({"message": "OK"}), 200


class InclusiveHandoverApi(HandoverApi):
    """共通の登録処理を使って営業担当の一括引継を受け付けるAPI。"""

    handover_type = HANDOVER_TYPE_BULK


contact_person_bp.add_url_rule(
    "/individual_handover",
    view_func=HandoverApi.as_view("individual_handover"),
    methods=["POST"],
)
contact_person_bp.add_url_rule(
    "/inclusive_handover",
    view_func=InclusiveHandoverApi.as_view("inclusive_handover"),
    methods=["POST"],
)
