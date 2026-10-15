from enum import Enum


class ReportType(Enum):
    """CNレポートPDF"""
    CN_REPORT_PDF = "1"

    """電力見える化レポート"""
    ELEC_VISUAL_PDF = "6"


class ReportStatus(Enum):
    """作成中"""
    WORKING = "0"
    
    """作成済"""
    DONE = "1"

    """作成エラー"""
    ERROR = "9"