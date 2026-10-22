from flask import Blueprint

report_bp = Blueprint("report", __name__, url_prefix="/api/report")

from . import (
    cn_karte_create_vis_api,
    cn_karte_download_api,
    cn_karte_list_api,
    cn_karte_options_api,
    cn_karte_register_api,
    cn_karte_visual_download_api,
    cn_karte_visual_list_api,
    cn_report_backdata_create_api,
    electricity_vis_create_api,
    kesson_report_create_api,
    kpi_report_create_api,
    pdf_create_api,
    power_report_contact_download_api,
    power_report_create_api,
    power_report_download_api,
    power_report_list_api,
    power_report_options_api,
    power_report_target_months_api,
    status_manage_api,
)
