import os
import tempfile
import traceback

from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.building import building_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db, log_time
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent
from cndx_corp_back.service.building_energy.building_energy_vis_register_service import (
    BuildingEnergyVisRegisterService,
)
from cndx_corp_back.service.file.check_transfer_service import FileCheckTransferService


class BuildingEnergyInfoVisApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    # @log_time
    def post(self, file_type, dict_request_data, user_context=None, logger=None):

        if "file" not in request.files:
            return jsonify({"error": "ファイルが送信されていません"}), 400

        input_file = request.files["file"]

        if input_file.filename == "":
            return jsonify({"error": "ファイルが選択されていません"}), 400

        if logger is None:
            logger = current_app.logger

        user_id = user_context.get("user_id")
        logger.user_id = user_id
        logger.info(f"{os.path.basename(__file__)}処理開始。")
        # リクエストにファイルが含まれているか確認
        if "file" in request.files:

            input_file = request.files["file"]

            # ファイルが選択されているか確認
            if input_file.filename == "":
                return (
                    jsonify({"error_message_list": "ファイルが選択されていません。"}),
                    400,
                )

        # サービスを呼び出す
        try:
            vis_service = BuildingEnergyVisRegisterService(
                input_file=input_file,
                logger=logger,
                org_id=user_context.get("org_id"),
                user_id=user_id,
                request_dict=dict_request_data,
                file_type=file_type,
            )
            message_list = vis_service.execute()
        except Exception as e:
            logger.error("ファイルアップロード処理に想定外のエラーが発生されました。")
            # logger.error(traceback.format_exc())
            raise

        response = {
            # "path": path,
            # "file_name": file_name,
            "error_message_list": message_list
        }
        if message_list:
            return jsonify(response), 400

        logger.info(f"{os.path.basename(__file__)}処理終了。")
        return jsonify(response), 200


building_energy_info_vis_view = BuildingEnergyInfoVisApi.as_view("energy_info_vis_api")
building_bp.add_url_rule(
    "/energy-info-vis/info/regist/<file_type>",
    view_func=building_energy_info_vis_view,
    methods=["POST"],
)
