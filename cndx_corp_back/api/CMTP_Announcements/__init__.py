from flask import Blueprint

announcements_bp = Blueprint(
    "announcements", __name__, url_prefix="/api/announcements"
)

from . import info_api
