import base64
import os
import traceback

from flask import abort, current_app
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import aliased

from cndx_corp_back.common.constants_values import ReportStatus, ReportTypeValue
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.entity.t_building_info_entity import TBuildingInfo
from cndx_corp_back.entity.t_cn_application_info_entity import TCnApplicationInfo
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.entity.user_mst_entity import MUser


class CnKarteListComponent:
    @component
    def execute(
        self,
        corporate_number: str,
        org_id: str,
        agreement_category: str,
        user_context,
        logger=None,
    ) -> list:
        if logger is None:
            logger = current_app.logger

        logger.info(
            f"{os.path.basename(__file__)} execute 開始 法人番号={corporate_number}, 組織ID={org_id}"
        )

        login_org_id = user_context.get("org_id")
        org_type_code = user_context.get("org_type_code")

        try:
            with get_scoped_session() as session:
                T2 = aliased(TCnApplicationInfo)

                building_org_exists = exists(
                    select(1)
                    .select_from(TBuildingInfo)
                    .join(
                        MBuilding,
                        and_(
                            TBuildingInfo.corporate_number
                            == MBuilding.corporate_number,
                            TBuildingInfo.agreement_category
                            == MBuilding.agreement_category,
                            TBuildingInfo.building_id == MBuilding.building_id,
                            MBuilding.delete_flg.is_(False),
                        ),
                    )
                    .where(
                        TBuildingInfo.corporate_number == T2.corporate_number,
                        TBuildingInfo.agreement_category == T2.agreement_category,
                        TBuildingInfo.org_id == T2.org_id,
                        TBuildingInfo.fiscal_year == T2.fiscal_year,
                        TBuildingInfo.registration_seq == T2.registration_seq,
                        TBuildingInfo.delete_flg.is_(False),
                        MBuilding.agreement_org == org_id,
                    )
                    .correlate(T2)
                )
                query = (
                    session.query(
                        T2.corporate_number,
                        T2.org_id,
                        T2.agreement_category,
                        T2.fiscal_year,
                        TReportStorageInfo.report_created_at,
                        TReportStorageInfo.report_save_path,
                        TReportStorageInfo.png_bytes,
                        TReportStorageInfo.report_status,
                        TReportStorageInfo.report_classify,
                        TReportStorageInfo.creation_id,
                        T2.registration_seq,
                        T2.report_period_start_year_month,
                        T2.report_period_end_year_month,
                        T2.entry_draft_flag,
                        MUserOrganizationInfo.org_name.label("org_name"),
                        MUser.user_name.label("created_by_user_name"),
                    )
                    .outerjoin(
                        TReportStorageInfo,
                        and_(
                            TReportStorageInfo.corporate_number == T2.corporate_number,
                            # TReportStorageInfo.org_id == T2.org_id,
                            TReportStorageInfo.fiscal_year == T2.fiscal_year,
                            TReportStorageInfo.registration_seq == T2.registration_seq,
                            TReportStorageInfo.report_classify == "1",
                            TReportStorageInfo.agreement_category
                            == T2.agreement_category,
                        ),
                    )
                    # Join m_user_organization_info
                    .outerjoin(
                        MUserOrganizationInfo,
                        TReportStorageInfo.org_id == MUserOrganizationInfo.org_id,
                    )
                    .outerjoin(
                        MUser,
                        and_(
                            MUser.user_id == TReportStorageInfo.created_by,
                            MUser.delete_flg.is_(False),
                        ),
                    )
                    .filter(
                        T2.corporate_number == corporate_number,
                        # T2.org_id.in_([org_id, login_org_id]),
                        T2.agreement_category == agreement_category,
                        T2.delete_flg.is_not(True),
                    )
                    # .order_by(TReportStorageInfo.report_created_at.desc())
                    .order_by(
                        TReportStorageInfo.fiscal_year.asc(),
                        TReportStorageInfo.registration_seq.asc(),
                    )
                )

                query_queue = (
                    session.query(
                        TReportStorageInfo.report_created_at,
                        TReportStorageInfo.report_save_path,
                        TReportStorageInfo.png_bytes,
                        TReportStorageInfo.report_status,
                        TReportStorageInfo.report_classify,
                        TReportStorageInfo.creation_id,
                    )
                    .filter(
                        TReportStorageInfo.report_classify
                        == ReportTypeValue.CN_REPORT_PDF.value,
                        TReportStorageInfo.report_status == ReportStatus.WORKING.value,
                        TReportStorageInfo.delete_flg.is_not(True),
                    )
                    .order_by(
                        TReportStorageInfo.report_created_at.desc().nulls_last(),
                        TReportStorageInfo.fiscal_year.desc(),
                        TReportStorageInfo.registration_seq.desc(),
                    )
                )

                result_queue = query_queue.all()

                # 地銀本店ログインの場合
                if org_type_code == "02":
                    query = query.where(
                        T2.org_id.in_([org_id, login_org_id]),
                    )
                # 地銀支店ログインの場合
                elif org_type_code == "03":
                    query = query.where(
                        T2.org_id == org_id,
                    )
                else:
                    # EP、REP、TCSログインの場合
                    query = query.where(building_org_exists)

                # result = query.all()
                result = session.execute(query).mappings().all()

                sorted_results = sorted(
                    result,
                    key=lambda r: (r.report_created_at is None, r.report_created_at),
                )

                sorted_queue_results = sorted(
                    result_queue,
                    key=lambda r: (r.report_created_at is None, r.report_created_at),
                )

                results_with_queue = []
                queue_no = 0

                for r in sorted_queue_results:
                    row = dict(r._mapping)  # SQLAlchemy Row → dict

                    if (
                        row.get("report_status") == ReportStatus.WORKING.value
                        and row.get("report_classify")
                        == ReportTypeValue.CN_REPORT_PDF.value
                    ):
                        queue_no += 1
                        row["queue_no"] = queue_no
                    else:
                        row["queue_no"] = None  # 0以外は設定しない

                    results_with_queue.append(row)

                # listからdictへ変換
                # filtered_results = [dict(row._mapping) for row in sorted_results]

                filtered_results = [
                    r
                    for r in sorted_results
                    if r["corporate_number"] == corporate_number
                    # and (r["org_id"] == org_id or r["org_id"] == login_org_id)
                    # and r["agreement_category"] == agreement_category
                ]

                # joinキー定義
                join_keys = ("creation_id",)

                # sorted_queue_results = [dict(r._mapping) for r in sorted_queue_results]

                # sorted_queue_results を lookup辞書化
                queue_lookup = {
                    tuple(row[k] for k in join_keys): row.get("queue_no")
                    for row in results_with_queue
                }

                # filtered_results に queue_no を追加
                merged_results = []
                for row in filtered_results:
                    key = tuple(row[k] for k in join_keys)  # RowMapping は参照はOK
                    d = dict(row)  # ここで編集可能な dict にする
                    d["queue_no"] = queue_lookup.get(key)  # 追加OK
                    merged_results.append(d)

                filtered_results = merged_results  # 見つからない場合は None

                def build_row(row_dict: dict) -> dict:
                    fiscal_year = row_dict["fiscal_year"]
                    report_created_at = (
                        row_dict["report_created_at"].strftime("%Y/%m/%d %H:%M:%S")
                        if row_dict["report_created_at"]
                        else ""
                    )
                    report_path = row_dict["report_save_path"]
                    png_bytes = row_dict["png_bytes"]
                    report_status = row_dict["report_status"]
                    thumbnail_base64 = None
                    if png_bytes is not None:
                        thumbnail_base64 = base64.b64encode(png_bytes).decode("utf-8")
                    # try:
                    #     if report_path:
                    #         png_path = report_path.replace(".pdf", ".png")
                    #         # local_path = os.path.join(report_path, os.path.basename(png_path))
                    #         # if os.path.exists(png_path):
                    #         process = subprocess.run(
                    #             ["hadoop", "fs", "-cat", png_path],
                    #             stdout=subprocess.PIPE,
                    #             stderr=subprocess.PIPE,
                    #             check=True,
                    #         )

                    #         png_io = io.BytesIO(process.stdout)
                    #         # base64 に変換
                    #         thumbnail_base64 = base64.b64encode(png_io.getvalue()).decode("utf-8")
                    #         # with open(png_path, "rb") as f:
                    #         #     thumbnail_base64 = base64.b64encode(f.read()).decode("utf-8")
                    # except Exception as e:
                    #     logger.warning(f"サムネイルbase64変換失敗: {e}")

                    return {
                        "fiscal_year": fiscal_year,
                        "report_created_at": report_created_at,
                        "report_save_path": report_path,
                        "thumbnail_base64": thumbnail_base64,
                        "report_status": report_status,
                        "report_period_start_year_month": row_dict[
                            "report_period_start_year_month"
                        ],
                        "report_period_end_year_month": row_dict[
                            "report_period_end_year_month"
                        ],
                        "org_name": row_dict["org_name"],
                        "registration_seq": row_dict["registration_seq"],
                        "queue_no": row_dict["queue_no"],
                        "register_org_id": row_dict["org_id"],
                        "entry_draft_flag": row_dict["entry_draft_flag"],
                        "report_created_by_name": row_dict["created_by_user_name"],
                    }

                return [build_row(row) for row in filtered_results]

        except Exception as e:
            logger.error("CNカルテ一覧取得失敗\n" + traceback.format_exc())
            abort(500)
