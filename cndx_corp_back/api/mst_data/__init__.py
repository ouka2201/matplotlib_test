from flask import Blueprint

mst_data_bp = Blueprint("mst_data", __name__, url_prefix="/api/mst_data")

from . import manage_api
