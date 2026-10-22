import io
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.logic.report.energy_kesson_report_create_logic import (
    EnergyKessonReportCreateLogic,
)
from cndx_corp_back.logic.report.kesson_report_create_logic import (
    KessonReportCreateLogic,
)


class KessonReportCreateService:
    """
    欠損レポート生成サービスクラス（PDF版）
    """

    # @log_time
    def execute(
        self,
        df_building,
        request_dict: Dict[str, Any],
        message_list: List[str],
        logger,
        prefetched_data: Dict[str, Any] = None,
    ) -> Dict[str, str]:
        """
        欠損レポートのPDFを2種類生成し、それぞれのパスを返却

        Args:
            request_dict (dict): リクエストボディのデータ
            message_list (list): エラーメッセージ用
            logger: ロガー

        Returns:
            dict: 各PDFの保存先パス
        """

        # ----------- 必須パラメータ取得＆チェック -----------
        required_keys = [
            "corporate_number",
            # "agreement_category",
            "org_id",
            "start_year",
            "start_month",
            "end_year",
            "end_month",
            "consent_route",
        ]

        for key in required_keys:
            if key not in request_dict or request_dict[key] is None:
                message_list.append(f"必須パラメータが不足しています：{key}")

        if message_list:
            return {}

        # ----------- ロジック呼び出し（2種類のPDF生成） -----------

        # 欠損一覧 PDF
        (
            file_name_generate,
            data_generate,
        ) = KessonReportCreateLogic().generate_pdf_report(
            df_building,
            request_dict=request_dict,
            logger=logger,
            prefetched_data=prefetched_data,
        )

        # エネルギーデータ欠損 PDF
        (
            file_name_energy,
            data_energy,
        ) = EnergyKessonReportCreateLogic().generate_energy_kesson_pdf_report(
            df_building,
            request_dict=request_dict,
            logger=logger,
        )

        # ----------- ZIP化 -----------
        zip_name, zip_bytes = make_zip_from_named_bytes(
            [
                (file_name_generate, data_generate),
                (file_name_energy, data_energy),
            ],
            subdir="pdf",
        )
        return zip_name, zip_bytes


# @log_time
def make_zip_from_named_bytes(files, subdir=None):
    """
    - filename: ZIP 内に格納するファイル名（拡張子 .csv 推奨）
    - data    : ファイル内容。bytes / bytearray / str を受け付ける。
                data が str の場合は UTF-8（BOM 付き：utf-8-sig）でエンコードして書き込む
                （Excel で文字化けしにくくするため）。
    return: (zip_filename, zip_bytes)
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        used = set()
        for name, data in files:
            if not isinstance(name, str) or not name:
                raise ValueError(f"ファイル名無効: {name!r}")

            # csv拡張子
            if not name.lower().endswith(".pdf"):
                name += ".pdf"

            # data 兼用処置
            if isinstance(data, str):
                data = data.encode("latin-1")
            elif isinstance(data, bytearray):
                data = bytes(data)
            elif not isinstance(data, bytes):
                raise TypeError(f"{name}: bytes/bytearray/str，型 {type(data)}")

            arcname = f"{subdir}/{name}" if subdir else name
            base, ext = arcname.rsplit(".", 1)
            ext = "." + ext
            i = 1
            while arcname in used:
                arcname = f"{base}({i}){ext}"
                i += 1
            used.add(arcname)

            zf.writestr(arcname, data)

    # 時間のローカライズ
    utc_time = datetime.now(timezone.utc)
    tokyo_time = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
    zip_name = f"kesson_report_bundle_{tokyo_time.strftime('%Y%m%d%H%M%S')}{tokyo_time.microsecond // 1000:03d}.zip"

    return zip_name, buf.getvalue()
