from flask import Blueprint

building_bp = Blueprint("building", __name__, url_prefix="/api/building")

from . import building_group_api, energy_info_api, energy_info_vis_api, energy_info_list_api, info_api, energy_register_api, vis_file_check_api, building_mst_info_api
