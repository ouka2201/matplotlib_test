from flask import Blueprint

help_bp = Blueprint("help", __name__, url_prefix="/api/help")

from . import help_api  # noqa
