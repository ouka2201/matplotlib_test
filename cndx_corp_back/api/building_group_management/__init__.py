from flask import Blueprint

building_group_management_bp = Blueprint("building_group_management", __name__, url_prefix="/api/building/group")

from . import info_api, update_api
