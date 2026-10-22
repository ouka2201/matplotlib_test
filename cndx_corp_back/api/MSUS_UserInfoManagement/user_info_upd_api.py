from flask import current_app, jsonify, request
from flask.views import MethodView
from pydantic import ValidationError

from cndx_corp_back.api.MSUS_UserInfoManagement import mst_user_info_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.MSUS_UserInfoManagement.user_upd_service import (
    UserUpdService,
)
from cndx_corp_back.utils.utils import get_message


class UserInfoUpdApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):
        """
        upd: ユーザー更新を行う
        """
        try:

            url = request.path

            user_id = user_context.get("user_id")

            if dict_request_data is None:
                return (
                    jsonify(
                        {
                            "error": get_message(
                                "NON_EXISTENCE", field="リクエストボディ"
                            )
                        }
                    ),
                    400,
                )

            if "upd" in url:
                UserUpdService.execute_user_upd(dict_request_data, user_id)
                return jsonify({"result": get_message("OK")}), 200

        except ValidationError as e:
            # エラーメッセージ再設定
            error_messages = []
            for err in e.errors():
                msg = err["msg"]
                if msg.startswith("Value error, "):
                    msg = msg[len("Value error, ") :]
                error_messages.append(msg)
            return jsonify({"message": error_messages}), 400

        except Exception as e:
            logger.error(f"ユーザー情報更新エラー: {str(e)}")
            if "このメールアドレスはすでに登録されています" in str(e):
                return (
                    jsonify(
                        {"message": get_message("REGISTERED", data="メールアドレス")}
                    ),
                    400,
                )
            if "選択した企業では、この権限を付与できません" in str(e):
                return (
                    jsonify(
                        {"message": "選択した企業では、この権限を付与できません。"}
                    ),
                    403,
                )
            if "削除ステータスのユーザーは更新できません" in str(e):
                return (
                    jsonify({"message": "削除ステータスのユーザーは更新できません。"}),
                    409,
                )
            if "ステータスを失効中に更新することはできません" in str(e):
                return (
                    jsonify(
                        {"message": "ステータスを失効中に更新することはできません。"}
                    ),
                    409,
                )
            if "削除済のユーザーは更新できません" in str(e):
                return jsonify({"message": "削除済のユーザーは更新できません。"}), 409
            return jsonify({"message": get_message("FAILURE")}), 500


# ルート登録
mst_user_upd_view = UserInfoUpdApi.as_view("user_info_upd_api")
mst_user_info_bp.add_url_rule("/upd", view_func=mst_user_upd_view, methods=["POST"])
