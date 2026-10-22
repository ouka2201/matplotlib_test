from flask import jsonify, request
from flask.views import MethodView
from pydantic import ValidationError

from cndx_corp_back.api.EBMG_BaseEnergy import base_energy_info_inquiry_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.dto.EBMG.energy_delete_in_dto import (
    EnergyDeleteIn,
)
from cndx_corp_back.service.EBMG_BaseEnergy.base_energy_delete_service import (
    BaseEnergyDeleteService,
)
from cndx_corp_back.utils.utils import get_message


class BaseEnergyDeleteApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, dict_request_data, user_context=None, logger=None):
        """
        delete: INPUTを元にエネルギーデータ情報登録に関わるテーブルを論理削除
        """
        url = request.path
        try:
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
            if "delete" in url:
                indto = EnergyDeleteIn.model_validate(dict_request_data)
                BaseEnergyDeleteService().delete_building_info(
                    indto,
                    org_id=user_context.get("org_id"),
                    user_id=user_context.get("user_id"),
                )
                return jsonify({"result": get_message("OK")}), 200

        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                # エラーメッセージを取り出す
                loc_str = ""
                for loc in error["loc"]:
                    if isinstance(loc, int):
                        loc_str += f"[{loc}]"
                    else:
                        if loc_str and not loc_str.endswith("]"):
                            loc_str += "."
                        loc_str += str(loc)
                error_messages.append(f"{loc_str}: {error['msg']}")
            return jsonify(description={"error_messages": error_messages}), 400
        except Exception as e:
            logger.error(f"データ削除エラー: {str(e)}")
            return jsonify({"error": get_message("FAILURE", field="データ削除")}), 500


# ルート登録
base_energy_delete_view = BaseEnergyDeleteApi.as_view("base_energy_delete_api")

base_energy_info_inquiry_bp.add_url_rule(
    "/delete", view_func=base_energy_delete_view, methods=["POST"]
)
