from flask import current_app, jsonify, request
from flask.views import MethodView
from pydantic import ValidationError

from cndx_corp_back.api.MSUS_UserInfoManagement import mst_user_info_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.MSUS_UserInfoManagement.user_insert_service import (
    UserInsertService,
)
from cndx_corp_back.utils.utils import get_message


class UserInfoInsertApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):
        """
        insert: 新規ユーザー登録を行う。地銀とEPで初期登録ステータスを分ける。
        """
        try:

            url = request.path
            user_id = user_context.get("user_id")
            login_org_type_code = user_context.get("org_type_code")

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

            if "insert" in url:
                UserInsertService.execute_user_insert(
                    dict_request_data, user_id, login_org_type_code
                )
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
            logger.error(f"ユーザー情報登録エラー: {str(e)}")
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
            if "ユーザー数が上限に達しています" in str(e):
                return jsonify({"message": "ユーザー数が上限に達しています。"}), 409
            # return jsonify({"message": get_message("FAILURE", field="ユーザー情報登録")}), 500
            return jsonify({"message": "システムエラーが発生しました"}), 500


# ルート登録
mst_user_insert_view = UserInfoInsertApi.as_view("user_info_insert_api")
mst_user_info_bp.add_url_rule(
    "/insert", view_func=mst_user_insert_view, methods=["POST"]
)
