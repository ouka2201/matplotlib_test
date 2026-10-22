from flask import Blueprint

user_bp = Blueprint("user", __name__, url_prefix="/api/user")

from . import msus_user_api  # noqa
