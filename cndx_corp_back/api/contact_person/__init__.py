from flask import Blueprint

contact_person_bp = Blueprint(
    "contact_person", __name__, url_prefix="/api/contact-person"
)

from . import info_api, get_user_api, detail_api, update_api, agreement_user_get_api
