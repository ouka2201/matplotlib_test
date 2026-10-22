from flask import Blueprint

per_30min_data_bp = Blueprint("per_30min_data", __name__, url_prefix="/api/building")

corp_building_info_bp = Blueprint(
    "corp_building_info", __name__, url_prefix="/api/corp/building"
)

from . import corp_building_info_api, per_30min_data_api
