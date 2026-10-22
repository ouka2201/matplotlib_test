from flask import Blueprint

per_30m_data_upload_bp = Blueprint(
    "30m_data_upload", __name__, url_prefix="/api/file/per-30m-data"
)

from . import FLUL_30_data_file_api
