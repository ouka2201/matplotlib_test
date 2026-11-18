"""個別引継の対象企業と、引継予定がある企業を取得するAPI。"""

import traceback

from flask import current_app, jsonify, request
from flask.views import MethodView

from cndx_corp_back.api.contact_person import contact_person_bp
from cndx_corp_back.common.decorators import controller, jwt_user_context_db
from cndx_corp_back.constant.handover_constants import HANDOVER_SYSTEM_ERROR
from cndx_corp_back.service.contact_person.individual_handover_search_service import (
    search_individual_companies,
    select_scheduled_companies,
)


class _IndividualSearchApi(MethodView):
    @jwt_user_context_db(refresh=False)
    @controller
    def get(self, dict_request_data, user_context=None, logger=None):
        logger = logger if logger is not None else current_app.logger
        try:
            result = self.search(dict_request_data, user_context or {})
        except PermissionError as error:
            return jsonify({"message": str(error)}), 403
        except ValueError as error:
            return jsonify({"message": str(error)}), 400
        except Exception as error:
            logger.error(f"個別引継検索失敗：{type(error).__name__}\n{''.join(traceback.format_tb(error.__traceback__))}")
            return jsonify({"message": HANDOVER_SYSTEM_ERROR}), 500
        return jsonify({self.response_key: result}), 200


class IndividualHandoverSearchApi(_IndividualSearchApi):
    response_key = "manager_list"
    search = staticmethod(search_individual_companies)


class ScheduledCompanyApi(_IndividualSearchApi):
    response_key = "selected_company_list"

    @staticmethod
    def search(data, user_context):
        return select_scheduled_companies(
            {**data, "corp_number_list": request.args.getlist("corp_number_list")}, user_context
        )


contact_person_bp.add_url_rule(
    "/individual_handover_search",
    view_func=IndividualHandoverSearchApi.as_view("individual_handover_search"),
    methods=["GET"],
)
contact_person_bp.add_url_rule(
    "/select_scheduled_company",
    view_func=ScheduledCompanyApi.as_view("select_scheduled_company"),
    methods=["GET"],
)
