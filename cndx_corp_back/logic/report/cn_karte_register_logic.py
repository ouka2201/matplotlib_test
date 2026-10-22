import os
from datetime import datetime
from typing import Any, Dict

from flask import abort, current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.ext import db


class CnKarteRegisterLogic:
    """
    CNカルテ登録ロジッククラス
    - t_report_storage_info へのデータ新規登録のみ
    """

    def insert_karte_condition(self, request_dict: Dict[str, Any], logger=None) -> str:
        """
        受け取った条件を t_report_storage_info に新規登録する
        """
        if logger is None:
            logger = current_app.logger

        logger.info(f"{os.path.basename(__file__)} – insert_karte_condition 開始")
        logger.debug(f"Insert params: {request_dict}")

        session = db.session

        try:
            # ------------------------------
            # パラメータ取得
            # ------------------------------
            corporate_number = request_dict["corporate_number"]
            org_id = request_dict["org_id"]
            agreement_category = request_dict["agreement_category"]
            report_selection_period_from = request_dict.get(
                "report_selection_period_from"
            )
            format_type = request_dict["format_type"]
            site_selection_type = request_dict["site_selection_type"]
            report_classify = request_dict["report_classify"]
            report_save_path = request_dict["report_save_path"]
            building_id = request_dict.get("building_id")
            user = request_dict.get("user", "system")
            fiscal_year = str(
                request_dict.get("fiscal_year")
                or request_dict.get("start_year")
                or datetime.now().year
            )

            # building_id 正規化
            if site_selection_type == "企業全体":
                building_id = "0"
            elif (
                site_selection_type == "グループ"
                and building_id
                and not building_id.startswith("GROUP:")
            ):
                building_id = "1:" + building_id
            else:
                # 個別の場合: building_id はそのまま使用（必ず単一IDを想定）
                building_id = str(building_id)

            # ------------------------------
            # registration_seq 採番
            # ------------------------------
            max_seq = (
                session.query(
                    func.coalesce(func.max(TReportStorageInfo.registration_seq), 0)
                )
                .filter(
                    TReportStorageInfo.corporate_number == corporate_number,
                    TReportStorageInfo.agreement_category == agreement_category,
                    TReportStorageInfo.org_id == org_id,
                    TReportStorageInfo.building_id == building_id,
                    TReportStorageInfo.fiscal_year == fiscal_year,
                    TReportStorageInfo.report_classify == report_classify,
                )
                .scalar()
            )

            # ------------------------------
            # creation_id
            # ------------------------------
            creation_id = (
                request_dict.get("creation_id")
                or f"{user}_{datetime.now().timestamp()}"
            )

            # ------------------------------
            # 新規登録
            # ------------------------------
            new_rec = TReportStorageInfo(
                creation_id=creation_id,
                corporate_number=corporate_number,
                agreement_category=agreement_category,
                org_id=org_id,
                building_id=building_id,
                fiscal_year=fiscal_year,
                report_classify=report_classify,
                registration_seq=max_seq + 1,
                target_month=None,
                entry_draft_flag=None,
                company_name=None,
                file_id=None,
                report_save_path=report_save_path,
                report_status=None,
                report_selection_period_from=report_selection_period_from,
                format_type=format_type,
                site_selection_type=site_selection_type,
                report_created_at=func.now(),
                report_created_by=user,
                delete_flg=False,
                created_by=user,
                # created_at=datetime.now(),
            )
            session.add(new_rec)
            session.commit()

            inserted_pk = (
                f"{new_rec.creation_id}-{new_rec.building_id}-{new_rec.report_classify}"
            )

            logger.info(f"{os.path.basename(__file__)} – insert_karte_condition 終了")
            return inserted_pk

        except SQLAlchemyError as exc:
            session.rollback()
            logger.error(f"DBエラー: {exc}")
            abort(500, description="DB登録エラー")
        finally:
            session.close()
