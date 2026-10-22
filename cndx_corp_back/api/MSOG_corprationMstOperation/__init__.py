from flask import Blueprint

mst_manage_bp = Blueprint("mst_manage", __name__, url_prefix="/api/mst_manage")

from . import mst_manage_api, org_search_api