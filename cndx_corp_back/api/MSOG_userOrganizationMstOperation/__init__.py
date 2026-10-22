from flask import Blueprint

mst_organization_bp = Blueprint("mst_organization", __name__, url_prefix="/api/user/mst_organization")

from . import mst_user_organization_api