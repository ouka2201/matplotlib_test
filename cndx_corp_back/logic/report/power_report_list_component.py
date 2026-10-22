import base64
import os
from datetime import datetime
from typing import Dict, List

from flask import abort, current_app
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import aliased

from cndx_corp_back.common.constants_values import ReportStatus, ReportTypeValue
from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.m_staff_info_entity import MStaffInfo
from cndx_corp_back.entity.m_user_organization_info_entity import MUserOrganizationInfo
from cndx_corp_back.entity.t_report_storage_info_entity import TReportStorageInfo
from cndx_corp_back.entity.user_mst_entity import MUser


class PowerReportListComponent:
    """電力見える化レポート一覧取得用コンポーネント（PNGサムネイル付き）"""

    def execute(
        self, corporate_number: str, org_id: str, agreement_category: str, user_context
    ) -> List[Dict[str, str]]:
        logger = current_app.logger
        logger.debug(f"{os.path.basename(__file__)} execute 開始")

        try:
            login_org_id = user_context.get("org_id")
            org_type_code = user_context.get("org_type_code")
            user_id = user_context.get("user_id")
            role_id = user_context.get("role")

            with get_scoped_session() as session:
                # t_report_storage_info と2つのマスタを結合
                query = (
                    session.query(
                        TReportStorageInfo.corporate_number.label("corporate_number"),
                        TReportStorageInfo.org_id.label("org_id"),
                        TReportStorageInfo.agreement_category,
                        TReportStorageInfo.fiscal_year,
                        TReportStorageInfo.registration_seq,
                        TReportStorageInfo.creation_id,
                        TReportStorageInfo.report_selection_period_from.label(
                            "period_start"
                        ),
                        TReportStorageInfo.report_selection_period_from.label(
                            "period_start_for_calc"
                        ),
                        TReportStorageInfo.target_month.label("target_month"),
                        MBuilding.location_identifier_name.label("building_name"),
                        MUserOrganizationInfo.org_name.label("org_name"),
                        TReportStorageInfo.report_created_at.label("created_at"),
                        TReportStorageInfo.report_save_path.label("report_save_path"),
                        TReportStorageInfo.report_classify.label("report_classify"),
                        TReportStorageInfo.png_bytes.label("png_bytes"),
                        TReportStorageInfo.report_status,
                        TReportStorageInfo.created_by.label("created_by_user_id"),
                        MUser.user_name.label("created_by_user_name"),
                    )
                    .join(
                        MBuilding,
                        and_(
                            TReportStorageInfo.corporate_number
                            == MBuilding.corporate_number,
                            TReportStorageInfo.building_id == MBuilding.building_id,
                        ),
                    )
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
                        TReportStorageInfo.corporate_number == corporate_number,
                        # TReportStorageInfo.org_id == org_id,
                        TReportStorageInfo.agreement_category == agreement_category,
                        # TReportStorageInfo.report_status == ReportStatus.WORKING.value,
                        TReportStorageInfo.report_classify
                        == ReportTypeValue.POWER_VISUAL_PDF.value,
                        TReportStorageInfo.delete_flg.is_not(True),
                    )
                    .order_by(TReportStorageInfo.report_created_at.desc())
                )

                MBuildingSub = aliased(MBuilding)
                building_org_exists = (
                    exists()
                    .select_from(MBuildingSub)
                    .where(
                        and_(
                            MBuildingSub.corporate_number
                            == TReportStorageInfo.corporate_number,
                            MBuildingSub.agreement_category
                            == TReportStorageInfo.agreement_category,
                            MBuildingSub.building_id == TReportStorageInfo.building_id,
                            MBuildingSub.agreement_org == org_id,
                            MBuildingSub.delete_flg.is_(False),
                        )
                    )
                )

                query_queue = (
                    session.query(
                        TReportStorageInfo.corporate_number.label("corporate_number"),
                        TReportStorageInfo.org_id.label("org_id"),
                        TReportStorageInfo.agreement_category,
                        TReportStorageInfo.creation_id,
                        TReportStorageInfo.fiscal_year,
                        TReportStorageInfo.registration_seq,
                        TReportStorageInfo.report_status,
                        TReportStorageInfo.report_created_at.label("created_at"),
                    )
                    .join(
                        MBuilding,
                        and_(
                            TReportStorageInfo.corporate_number
                            == MBuilding.corporate_number,
                            TReportStorageInfo.building_id == MBuilding.building_id,
                        ),
                    )
                    .filter(
                        TReportStorageInfo.report_classify
                        == ReportTypeValue.POWER_VISUAL_PDF.value,
                        TReportStorageInfo.report_status == ReportStatus.WORKING.value,
                        TReportStorageInfo.delete_flg.is_not(True),
                    )
                    .order_by(
                        TReportStorageInfo.report_created_at.desc().nulls_last(),
                        MBuilding.location_identifier_name.collate("C").asc(),
                    )
                )

                results_queue = query_queue.all()

                # 地銀本店ログインの場合
                if org_type_code == "02":
                    query = query.where(
                        and_(
                            TReportStorageInfo.org_id.in_([org_id, login_org_id]),
                            building_org_exists,
                        )
                    )
                # 地銀支店ログインの場合
                elif org_type_code == "03":
                    query = query.where(
                        TReportStorageInfo.org_id == org_id,
                    )
                else:
                    # EP、REP、TCSログインの場合
                    query = query.where(building_org_exists)

                results = session.execute(query).mappings().all()

                # print(
                #     query.statement.compile(
                #         dialect=session.connection().dialect,
                #         compile_kwargs={"literal_binds": True},
                #     )
                # )

                sorted_results = sorted(results, key=lambda r: r.created_at)

                sorted_queue_results = sorted(results_queue, key=lambda r: r.created_at)

                results_with_queue = []
                queue_no = 0

                for r in sorted_queue_results:
                    row = dict(r._mapping)  # SQLAlchemy Row → dict

                    if row.get("report_status") == ReportStatus.WORKING.value:
                        queue_no += 1
                        row["queue_no"] = queue_no
                    else:
                        row["queue_no"] = None  # 0以外は設定しない

                    results_with_queue.append(row)

                filtered_results = [
                    r
                    for r in sorted_results
                    if r["corporate_number"] == corporate_number
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

                report_list: List[Dict[str, str]] = []

                for row in filtered_results:
                    # サムネイル
                    thumbnail_base64 = ""
                    try:
                        if row["png_bytes"]:
                            thumbnail_base64 = base64.b64encode(
                                row["png_bytes"]
                            ).decode("utf-8")
                    except Exception as e:
                        logger.error(f"サムネイルbase64変換失敗: {e}")
                        abort(500)

                    # 対象期間：対象期間開始~終了
                    if row["period_start_for_calc"]:
                        y = int(row["period_start_for_calc"][:4])
                        m = int(row["period_start_for_calc"][4:6])
                        # end_year = y + 1
                        # end_month = m
                        target_period = f"{y:04d}{m:02d}"
                    else:
                        target_period = ""

                    # レポート名
                    report_name = (
                        f"{_format_ym(row["target_month"])}のレポート"
                        if row["target_month"]
                        else ""
                    )

                    report_list.append(
                        {
                            "report_name": report_name,
                            "org_name": row["org_name"],
                            "building_name": row["building_name"],
                            "report_created_at": _dt(row["created_at"]),
                            "target_period": target_period,
                            "report_save_path": row["report_save_path"],
                            "report_classify": row["report_classify"],
                            "thumbnail_base64": thumbnail_base64,
                            "target_month": row["target_month"],
                            "queue_no": row["queue_no"],
                            "report_status": row["report_status"],
                            "sort_time": row["created_at"],
                            "report_created_by_id": row["created_by_user_id"],
                            "report_created_by_name": row["created_by_user_name"],
                        }
                    )
                report_list.sort(key=lambda x: x["sort_time"], reverse=True)

                logger.debug(f"{os.path.basename(__file__)} execute 終了")
                return report_list

        except Exception as e:
            logger.error(f"{os.path.basename(__file__)} 想定外エラー発生: {e}")
            abort(500)


def _dt(dt: datetime | None) -> str | None:
    return dt.strftime("%Y-%m-%d") if isinstance(dt, datetime) else None


def _format_ym(yyyymm: str | None) -> str:
    if not yyyymm or len(yyyymm) != 6:
        return ""
    y = yyyymm[:4]
    m = yyyymm[4:6]
    return f"{y}/{m}"
