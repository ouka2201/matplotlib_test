from flask import Blueprint

ui_bp = Blueprint("ui", __name__, url_prefix="/api/ui")

from . import option_api
