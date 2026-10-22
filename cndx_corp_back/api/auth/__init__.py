from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

from . import auth_api  # noqa
from . import auth_init  # noqa
from . import user_info_init  # noqa
