from flask import Blueprint

report_create_management_bp = Blueprint(
    "report_create_management", __name__, url_prefix="/api/mst_corporate"
    )

from . import info_api
