from flask import Blueprint

mst_user_info_bp = Blueprint("mst_user", __name__, url_prefix="/api/mst_user")

from . import user_info_search_api, user_related_info_search_api, user_info_insert_api, user_info_csv_api, user_info_upd_api, user_info_logout_api
