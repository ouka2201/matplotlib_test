from flask import current_app, jsonify, request
from flask.views import MethodView

from cndx_corp_back.api.ui import ui_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.service.ui.option_service import UiOptionService

# @ui_bp.route("/option/pref", methods=["GET"])
# def get_pref(logger=None):

#     res = UiOptionService().get_pref()

#     return jsonify({"ok": True, "result_list": res}), 200


@ui_bp.route("/option/industry", methods=["GET"])
def get_industry(logger=None):

    res = UiOptionService().get_industry()

    return jsonify({"ok": True, "result_list": res}), 200


# @ui_bp.route("/option/consent-route", methods=["GET"])
# def get_consent_route():

#     request_dict = request.args.to_dict()

#     res = UiOptionService().get_consent_route(request_dict)

#     return jsonify({"ok": True, "result_list": res}), 200


@ui_bp.route("/option/<master_name>", methods=["GET"])
# @jwt_user_context_db()
def get_option_master(master_name, user_context=None):

    try:
        filters = request.args.to_dict()
        result = UiOptionService().get_master_list(
            master_name, logger=current_app.logger, filters=filters
        )

        return jsonify({"res": result}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
