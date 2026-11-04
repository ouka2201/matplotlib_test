from flask import Blueprint

contact_person_bp = Blueprint(
    "contact_person", __name__, url_prefix="/api/contact-person"
)

# Blueprintへ各エンドポイントを登録するために読み込む。
from . import (  # noqa: E402,F401 - Blueprint作成後にルートを登録する。
    agreement_user_get_api,
    detail_api,
    get_user_api,
    handover_register_api,
    info_api,
    search_api,
    update_api,
)
