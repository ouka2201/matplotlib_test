from flask import Blueprint

base_energy_info_inquiry_bp = Blueprint("energy-info", __name__, url_prefix="/api/building/energy-info")

from . import base_energy_info_api, electric_company_search, base_energy_delete_api
