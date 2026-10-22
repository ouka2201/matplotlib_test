from flask import jsonify, request
from flask.views import MethodView
from pydantic import ValidationError

from cndx_corp_back.api.EBMG_BaseEnergy import base_energy_info_inquiry_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.dto.EBMG.energy_auto_entry_in_dto import (
    EnergyAutoEntryIn,
)
from cndx_corp_back.service.EBMG_BaseEnergy.base_energy_inquiry_service import (
    BaseEnergyInquiryService,
)


class BaseEnergyInfoApi(MethodView):

    @controller
    @jwt_user_context_db(refresh=False)
    def post(self, dict_request_data, user_context=None, logger=None):
        """
        detail: INPUTを元にエネルギーデータ登録編集/照会画面初期表示を取得
        auto: INPUTを元に30分値エネルギーデータの月別データを取得
        """
        url = request.path
        try:
            if dict_request_data is None:
                return jsonify({"error": "リクエストボディが存在しません"}), 400

            if "detail" in url:
                res = BaseEnergyInquiryService().get_base_energy_info(
                    dict_request_data, user_context
                )
                return jsonify({"result": res}), 200
            elif "auto" in url:
                indto = EnergyAutoEntryIn.model_validate(dict_request_data)
                res = BaseEnergyInquiryService().get_base_energy_auto30(indto)
                return jsonify({"result": res}), 200

        except ValidationError as e:
            return jsonify({"errors": e.errors()}), 400
        except Exception as e:
            logger.error(f"データ取得エラー: {str(e)}")
            return jsonify({"error": "データ取得に失敗しました"}), 500


# ルート登録
base_energy_info_view = BaseEnergyInfoApi.as_view("base_energy_info_api")

base_energy_info_inquiry_bp.add_url_rule(
    "/detail", view_func=base_energy_info_view, methods=["POST"]
)
base_energy_info_inquiry_bp.add_url_rule(
    "/auto", view_func=base_energy_info_view, methods=["POST"]
)
