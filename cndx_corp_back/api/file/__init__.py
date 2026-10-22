from flask import Blueprint

file_bp = Blueprint("file", __name__, url_prefix="/api/file")

from . import check_transfer_api, file_download_api  # noqa
