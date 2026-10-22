import os
import tempfile

from flask import abort, current_app, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from cndx_corp_back.api.building import building_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.logic.file.transfer_component import FileTransferComponent
from cndx_corp_back.service.building_energy.building_energy_vis_register_service import (
    BuildingEnergyVisRegisterService,
)
from cndx_corp_back.service.building_energy.vis_file_check_service import (
    VisFileCheckService,
)
from cndx_corp_back.service.file.check_transfer_service import FileCheckTransferService


class VisFileCheckApi(MethodView):

    @jwt_user_context_db(refresh=False)
    @controller
    def post(self, file_type, dict_request_data, user_context=None, logger=None):

        if "file" not in request.files:
            logger.error(f"ファイルが選択されていません。")
            return jsonify({"error": "ファイルが送信されていません"}), 400

        input_file = request.files["file"]

        if input_file.filename == "":
            logger.error(f"ファイルが選択されていません。")
            return jsonify({"error": "ファイルが選択されていません"}), 400

        if logger is None:
            logger = current_app.logger

        # リクエストにファイルが含まれているか確認
        if "file" in request.files:
            input_file = request.files["file"]
            # ファイルが選択されているか確認
            if input_file.filename == "":
                logger.error(f"ファイルが選択されていません。")
                abort(400, description="ファイルが選択されていません")
                return (
                    jsonify({"error_message_list": "ファイルが選択されていません。"}),
                    400,
                )

        # サービスを呼び出す
        user_id = user_context.get("user_id")
        vis_service = VisFileCheckService(
            input_file=input_file,
            org_id=user_context.get("org_id"),
            user_id=user_id,
            request_dict=dict_request_data,
            file_type=file_type,
            logger=logger,
        )
        check_result = vis_service.execute()

        if isinstance(check_result, list) and check_result:
            if check_result[0] != "c":
                return (
                    jsonify(
                        {
                            "result": "error",
                            "status": 400,
                            "message": "<br>".join(check_result),
                            "errorlist": check_result,
                        }
                    ),
                    400,
                )
            else:
                return (
                    jsonify(
                        {
                            "result": "ok",
                            "status": 200,
                            "message": "\n".join(check_result),
                            "errorlist": check_result,
                        }
                    ),
                    200,
                )
        else:
            return (
                jsonify(
                    {
                        "result": "ok",
                        "status": 200,
                        "message": check_result,
                    }
                ),
                200,
            )


vis_file_check_view = VisFileCheckApi.as_view("vis_file_check_api")
building_bp.add_url_rule(
    "/vis/file-check/<file_type>", view_func=vis_file_check_view, methods=["POST"]
)
