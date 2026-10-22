# cndx_corp_back/logic/report/cn_report_backdata_bundle_logic.py
# -*- coding: utf-8 -*-
"""
CNレポート・バックデータ生成ロジック（バンドル版）
- 入力チェック → 各CSV生成（4種）→ ZIP作成 → パス返却 を本クラスで完結
- 生成対象：
    1) CNバックデータ
    2) 生データ
    3) 拠点ランキング
    4) エネルギーランキング
- 返却：各CSVのパスとZIPのパスを dict で返却
"""

from __future__ import annotations

import io
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from flask import abort, current_app

from cndx_corp_back.common.decorators import component, log_time
from cndx_corp_back.logic.report.cn_energy_ranking_report_logic import (
    CnEnergyRankingReportLogic,
)
from cndx_corp_back.logic.report.cn_raw_data_report_logic import CnRawDataReportLogic

# ▼ 既存の「個別CSV生成」ロジックを利用
from cndx_corp_back.logic.report.cn_report_backdata_create_logic import (
    CnReportBackdataCreateLogic,
)
from cndx_corp_back.logic.report.cn_site_ranking_report_logic import (
    CnSiteRankingReportLogic,
)


class CnReportBackdataBundleLogic:
    """
    CNレポート・バックデータ生成ロジック（複数CSV + ZIP）統合版
    - 旧ロジック（個別CSV生成）を内部で呼び出し、まとめてZIP化して返却する。
    """

    # 必須キー定義（従来どおり）
    REQUIRED_KEYS = [
        "corporate_number",
        # "agreement_category",
        "org_id",
        "start_year",
        "start_month",
        "end_year",
        "end_month",
        "consent_route",  # CN特有
    ]

    # @log_time
    def generate_all_reports(
        self,
        df_building,
        request_dict: Dict[str, Any],
        logger=None,
        message_list: Optional[List[str]] = None,
    ) -> Dict[str, Optional[str]]:
        """
        4種類のCSVを生成し、ZIPに束ねた上でパスを返却するメイン処理。

        Args:
            request_dict (dict): リクエストボディ
            logger: ロガー（省略時は current_app.logger）
            message_list (list|None): 入力チェックのエラーを積むためのリスト（任意）

        Returns:
            dict[str, Optional[str]]: 生成ファイルのパス群
                {
                  "cn_report_backdata": <path or None>,
                  "raw_data_report": <path or None>,
                  "site_ranking_report": <path or None>,
                  "energy_ranking_report": <path or None>,
                  "zip_path": <zip path>  # ZIPは常に作成（中身が少なくても作成）
                }
        """
        if logger is None:
            logger = current_app.logger
        if message_list is None:
            message_list = []

        logger.info("[BackdataBundle] 開始: CNバックデータ一括生成")

        # 1) 入力チェック
        self._validate_request(request_dict, message_list, logger)
        if message_list:
            logger.error(f"[BackdataBundle] 必須パラメータ不足: {message_list}")
            # 形式は崩さず返す（空ZIPを作成）
            return {
                "cn_report_backdata": None,
                "raw_data_report": None,
                "site_ranking_report": None,
                "energy_ranking_report": None,
                "zip_path": self._create_empty_zip(logger),
            }

        # 2-1. CNバックデータ
        (
            filename_backdata,
            csv_bytes_backdata,
        ) = CnReportBackdataCreateLogic().generate_csv_report(
            df_building=df_building, request_dict=request_dict, logger=logger
        )

        # 2-2. 生データ
        (
            filename_rawdata,
            csv_bytes_rawdata,
        ) = CnRawDataReportLogic().generate_raw_data_csv(
            df_building=df_building, request_dict=request_dict, logger=logger
        )

        # 2-3. 拠点ランキング
        (
            filename_buildingdata,
            csv_bytes_buildingdata,
        ) = CnSiteRankingReportLogic().generate_site_ranking_csv(
            df_building=df_building, request_dict=request_dict, logger=logger
        )

        # 2-4. エネルギーランキング
        (
            filename_enegrydata,
            csv_bytes_enegrydata,
        ) = CnEnergyRankingReportLogic().generate_energy_ranking_csv(
            df_building=df_building, request_dict=request_dict, logger=logger
        )

        zip_name, zip_bytes = make_zip_from_named_bytes(
            [
                (filename_backdata, csv_bytes_backdata),
                (filename_rawdata, csv_bytes_rawdata),
                (filename_buildingdata, csv_bytes_buildingdata),
                (filename_enegrydata, csv_bytes_enegrydata),
            ],
            subdir="csv",
        )
        return zip_name, zip_bytes

    # ------------------------------------------------------------------ #
    # 内部ユーティリティ
    # ------------------------------------------------------------------ #

    def _validate_request(
        self, request_dict: Dict[str, Any], message_list: List[str], logger
    ) -> None:
        """必須キーの存在チェック（値が None の場合もNG）。"""
        for key in self.REQUIRED_KEYS:
            if key not in request_dict or request_dict[key] is None:
                message_list.append(f"必須パラメータが不足しています：{key}")

    def _safe_generate(
        self,
        name: str,
        func,
        df_building: object,
        request_dict: Dict[str, Any],
        logger,
    ) -> Optional[str]:
        """
        個別生成関数を安全に実行し、例外時はログ出力して None を返す。
        個別関数のシグネチャは (request_dict, logger) を想定。
        """
        try:
            path = func(
                df_building=df_building, request_dict=request_dict, logger=logger
            )
            if not path:
                logger.warning(f"[BackdataBundle] 生成結果が空のためスキップ: {name}")
                return None
            if not os.path.exists(path):
                logger.warning(
                    f"[BackdataBundle] パスが存在しないためスキップ: {name}={path}"
                )
                return None
            logger.info(f"[BackdataBundle] 生成OK: {name} -> {path}")
            return path
        except Exception as e:
            logger.error(f"[BackdataBundle] 生成中に例外発生: {name}: {e}")
            abort(500)


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
            if not name.lower().endswith(".csv"):
                name += ".csv"

            # data 兼用処置
            if isinstance(data, str):
                data = data.encode("utf-8-sig")
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
    now_local = utc_time.astimezone(ZoneInfo("Asia/Tokyo"))
    zip_name = f"cn_report_bundle_{now_local.strftime('%Y%m%d%H%M%S')}{now_local.microsecond // 1000:03d}.zip"

    return zip_name, buf.getvalue()

    # def _create_zip(self, file_paths: Dict[str, Optional[str]], logger) -> str:
    #     """
    #     指定された複数ファイルを ZIP にまとめる。
    #     - None や存在しないパスはスキップ
    #     - ZIP ファイル名: cn_report_bundle_YYYYMMDDHHMMSS.zip
    #     """
    #     os.makedirs(self.ZIP_OUTPUT_DIR, exist_ok=True)

    #     zip_name = f"cn_report_bundle_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    #     zip_path = os.path.join(self.ZIP_OUTPUT_DIR, zip_name)

    #     with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    #         for name, path in file_paths.items():
    #             if not path:
    #                 logger.warning(f"[BackdataBundle] ZIP対象外（None）: {name}")
    #                 continue
    #             if not os.path.exists(path):
    #                 logger.warning(f"[BackdataBundle] ZIP対象外（存在しない）: {name}={path}")
    #                 continue
    #             arcname = os.path.basename(path)
    #             zipf.write(path, arcname)
    #             logger.info(f"[BackdataBundle] ZIPに追加: {path} → {arcname}")

    #     logger.info(f"[BackdataBundle] ZIPファイル作成完了: {zip_path}")
    #     return zip_path

    # def _create_empty_zip(self, logger) -> str:
    #     """
    #     入力エラー時でも返却形式を崩さないため、空のZIPを作成して返す。
    #     """
    #     os.makedirs(self.ZIP_OUTPUT_DIR, exist_ok=True)
    #     zip_name = f"cn_report_bundle_{datetime.now().strftime('%Y%m%d%H%M%S')}_empty.zip"
    #     zip_path = os.path.join(self.ZIP_OUTPUT_DIR, zip_name)
    #     with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED):
    #         pass
    #     logger.info(f"[BackdataBundle] 空ZIPを作成しました: {zip_path}")
    #     return zip_path
