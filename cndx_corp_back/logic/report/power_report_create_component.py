from __future__ import annotations

import os
from datetime import datetime
from typing import Dict
from uuid import uuid4

from common.new_logger import NewLogger
from flask import abort, current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.utils.utils import get_message


class PowerReportCreateComponent:
    # 出力先ディレクトリ設定キー／デフォルト
    OUTPUT_DIR_CONFIG_KEY = "POWER_REPORT_OUTPUT_DIR"
    DEFAULT_OUTPUT_DIR = r"C:\HZY\FILE DOWNLOAD\PDF"

    @component
    def execute(self, request_dict: Dict[str, str], logger=None) -> str:
        # ----------------------------------------------
        # ロガー設定（NewLogger でラップ）
        # ----------------------------------------------
        if logger is None or not isinstance(logger, NewLogger):
            logger = NewLogger(current_app.logger)

        logger.info(f"{os.path.basename(__file__)} – 電力レポート作成開始")

        # ----------------------------------------------
        # 必須項目チェック
        # ----------------------------------------------
        required_keys = ["corporate_number", "org_id", "building_id", "target_month"]
        for key in required_keys:
            value = request_dict.get(key)
            if not value:
                logger.error(f"必須フィールドが不足しています: {key}")
                abort(400, description=get_message("FIELD_REQUIRED", key=key))

        # agreement_category は任意。未指定時は '01' を使用
        agreement_category = request_dict.get("agreement_category")
        if not agreement_category:
            agreement_category = "01"
            logger.info(
                "agreement_category が指定されていません。デフォルト '01' を使用します。"
            )
        request_dict["agreement_category"] = agreement_category

        try:
            # 対象年度は target_month (YYYYMM) の先頭4桁
            fiscal_year = request_dict["target_month"][:4]

            with get_scoped_session() as session:
                # ----------------------------------------------
                # 検索キー（新仕様：fiscal_year はキーに含める／target_month を追加）
                # ----------------------------------------------
                query_key = {
                    "corporate_number": request_dict["corporate_number"],
                    "org_id": request_dict["org_id"],
                    "building_id": request_dict["building_id"],
                    "agreement_category": request_dict["agreement_category"],
                    "report_classify": "6",  # 電力見える化レポート固定
                    "target_month": request_dict["target_month"],
                    "fiscal_year": fiscal_year,
                }

                # ----------------------------------------------
                # 既存レコード有無チェック
                # ----------------------------------------------
                rp_info: TReportStorageInfo | None = (
                    session.query(TReportStorageInfo)
                    .filter_by(**query_key, delete_flg=False)
                    .first()
                )

                if rp_info is None:
                    # ------------------------------------------
                    # 新規作成
                    #   ※ PK は (creation_id, building_id, report_classify)
                    #     → creation_id を必ず採番する
                    # ------------------------------------------
                    logger.info(f"該当レコードなし → 新規作成: {query_key}")

                    max_seq = (
                        session.query(
                            func.coalesce(
                                func.max(TReportStorageInfo.registration_seq), 0
                            )
                        )
                        .filter_by(
                            corporate_number=request_dict["corporate_number"],
                            org_id=request_dict["org_id"],
                            building_id=request_dict["building_id"],
                            agreement_category=request_dict["agreement_category"],
                            report_classify="6",
                        )
                        .scalar()
                    )

                    rp_info = TReportStorageInfo(
                        # --- 主キー ---
                        creation_id=uuid4().hex,  # ★ PK の一部：必須
                        building_id=request_dict["building_id"],
                        report_classify="6",
                        # --- 検索キー／属性 ---
                        corporate_number=request_dict["corporate_number"],
                        agreement_category=request_dict["agreement_category"],
                        org_id=request_dict["org_id"],
                        fiscal_year=fiscal_year,
                        target_month=request_dict["target_month"],
                        # --- 管理項目 ---
                        registration_seq=max_seq + 1,
                        delete_flg=False,
                        created_by="system",
                    )
                    session.add(rp_info)
                else:
                    # ------------------------------------------
                    # 既存レコード更新（ファイル出力情報を上書き）
                    # ------------------------------------------
                    logger.info(f"該当レコードあり → 更新: {query_key}")
                    rp_info.updated_by = "system"

                # ----------------------------------------------
                # ファイル名（実体の生成は別コンポーネントを想定）
                # ----------------------------------------------
                file_name = "電力見える化.pdf"

                # ----------------------------------------------
                # 共通更新項目
                # ----------------------------------------------
                rp_info.report_save_path = file_name
                rp_info.report_created_at = func.now()

                # コミット
                # session.commit()
                logger.info(f"report_save_path 更新完了: {file_name}")

        except SQLAlchemyError as exc:
            # DB系エラーは 500 で返却（ログにはスタックトレース）
            logger.exception("DB 更新失敗", exc_info=True)
            abort(500, description=get_message("FAILED", data="DB更新"))

        logger.info(f"{os.path.basename(__file__)} – 電力レポート作成終了")
        return file_name
