from flask import Blueprint

corp_bp = Blueprint("corp", __name__, url_prefix="/api/corp")

from . import basic_info_api
