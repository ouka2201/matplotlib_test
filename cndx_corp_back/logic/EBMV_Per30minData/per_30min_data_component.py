from collections import defaultdict
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import and_, exists, func

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.common.decorators import component
from cndx_corp_back.entity.m_building_entity import MBuilding
from cndx_corp_back.entity.t_electricity_data_30min_entity import (
    TElectricityData30min,
)
from cndx_corp_back.utils.datetime_utils import format_datetimes
from cndx_corp_back.utils.utils import get_message


class Per30minDataComponent:

    @component
    def execute(
        self,
        request_dict: dict,
        org_type_code,
        login_org_id,
        user_id,
        role_id,
        logger=None,
    ) -> dict:
        if logger is None:
            logger = current_app.logger

        corp_number_val = request_dict.get("corp_number", "").strip()
        building_id_val = request_dict.get("building_id", "").strip()
        agreement_category_val = request_dict.get("agreement_category", "").strip()
        org_id = request_dict.get("org_id", "").strip()

        logger.info(
            f"30分値登録状況データ取得開始: corporate_number={corp_number_val}, building_id={building_id_val}"
        )

        try:
            with get_scoped_session() as session:
                period_from = func.min(TElectricityData30min.acquisition_date).label(
                    "period_from"
                )

                period_to = func.max(TElectricityData30min.acquisition_date).label(
                    "period_to"
                )
                query = session.query(
                    TElectricityData30min.corp_number,
                    TElectricityData30min.building_name,
                    TElectricityData30min.building_id,
                    period_from,
                    period_to,
                    func.max(TElectricityData30min.file_update_date).label(
                        "file_update_date"
                    ),
                    func.max(TElectricityData30min.arve_corp_name).label("ARVE_CORP_NAME"),
                    func.max(TElectricityData30min.arve_office_code).label("ARVE_OFFICE_CODE"),
                    func.max(TElectricityData30min.arve_customer_number).label("ARVE_CUSTOMER_NUMBER"),
                ).filter(
                    TElectricityData30min.corp_number == corp_number_val,
                    TElectricityData30min.agreement_category == agreement_category_val,
                    TElectricityData30min.delete_flg.is_not(True),
                )

                if building_id_val:  # 値がNoneや空文字でない場合
                    query = query.filter(
                        TElectricityData30min.building_id == building_id_val
                    )

                conditions = [
                    MBuilding.corporate_number == TElectricityData30min.corp_number,
                    MBuilding.agreement_category
                    == TElectricityData30min.agreement_category,
                    MBuilding.building_id == TElectricityData30min.building_id,
                    MBuilding.delete_flg.is_(False),
                ]

                if org_id:
                    conditions.append(MBuilding.agreement_org  == org_id)

                building_org_exists = (
                    exists().select_from(MBuilding).where(and_(*conditions))
                )

                # # 地銀本店ログインの場合
                # if org_type_code == "02":
                #     mUserOrganizationInfo = select(
                #         MUserOrganizationInfo.org_id,
                #     ).where(
                #         MUserOrganizationInfo.parent_org_id == login_org_id,
                #         MUserOrganizationInfo.delete_flg.is_(False),
                #     )
                #     query = query.where(
                #         or_(
                #             TElectricityData30min.org_id.in_([org_id, login_org_id]),
                #             TElectricityData30min.org_id.in_(mUserOrganizationInfo)
                #         )
                #     )
                # # 地銀支店ログインの場合
                # elif org_type_code == "03":
                #     query = query.where(
                #         TElectricityData30min.org_id == org_id,
                #     )
                # elif org_type_code == "01" and role_id == "1":
                #     #EP一般者の場合
                #     stmt = stmt.outerjoin(
                #         MStaffInfo,
                #         and_(
                #             TElectricityData30min.corp_number == MStaffInfo.corporate_number,
                #             TElectricityData30min.agreement_category == MStaffInfo.agreement_category,
                #             TElectricityData30min.org_id == MStaffInfo.org_id,
                #             MStaffInfo.delete_flg.is_(False)
                #         )
                #     ).where(
                #         or_(
                #             and_(
                #                 TElectricityData30min.agreement_category != "01",
                #                 building_org_exists,
                #             ),
                #             and_(
                #                 TElectricityData30min.agreement_category == "01",
                #                 MStaffInfo.user_id == user_id,
                #             ),
                #         )
                #     )
                # else:
                #     #EP、REP、TCSログインの場合
                #     query = query.where(
                #         building_org_exists
                #     )
                query = query.where(building_org_exists)

                res = (
                    query.group_by(
                        TElectricityData30min.corp_number,
                        TElectricityData30min.building_name,
                        TElectricityData30min.building_id,
                    )
                    .order_by(
                        TElectricityData30min.building_name.collate("C"),
                        period_from.asc(),
                    )
                    .all()
                )

            res = [dict(e._mapping) for e in res]
            res = self._split_overlapping_periods(res)
            return {"upload_history": format_datetimes(res)}

        except Exception as e:
            logger.error(f"30分値登録状況の取得失敗: {str(e)}")

            return {
                "upload_history": [],
                "error": get_message("SERVER_ERROR"),
                "message": get_message("UNEXPECTED"),
            }

    def _split_overlapping_periods(self, rows):
        """
        Split overlapping period ranges so each contiguous range maps to a single file_update_date.
        """
        grouped_rows = defaultdict(list)
        for row in rows:
            key = (row.get("corp_number"), row.get("building_id"))
            grouped_rows[key].append(row)

        normalized_rows = []
        for row_group in grouped_rows.values():
            normalized_rows.extend(self._build_segments(row_group))

        normalized_rows.sort(
            key=lambda row: (
                row.get("corp_number"),
                row.get("building_id"),
                row.get("period_from"),
            )
        )
        return normalized_rows

    def _build_segments(self, intervals):
        parsed_intervals = []
        for interval in intervals:
            start = self._to_date(interval.get("period_from"))
            end = self._to_date(interval.get("period_to"))
            if not start or not end or start > end:
                continue
            parsed_intervals.append({**interval, "_start": start, "_end": end})

        if not parsed_intervals:
            return []

        boundaries = set()
        for interval in parsed_intervals:
            boundaries.add(interval["_start"])
            boundaries.add(interval["_end"] + timedelta(days=1))

        sorted_boundaries = sorted(boundaries)
        segments = []
        for index in range(len(sorted_boundaries) - 1):
            segment_start = sorted_boundaries[index]
            segment_end = sorted_boundaries[index + 1] - timedelta(days=1)
            if segment_start > segment_end:
                continue

            covering_intervals = [
                interval
                for interval in parsed_intervals
                if interval["_start"] <= segment_start
                and interval["_end"] >= segment_end
            ]
            if not covering_intervals:
                continue

            covering_intervals.sort(
                key=lambda interval: interval.get("file_update_date") or datetime.min,
                reverse=True,
            )
            chosen_interval = covering_intervals[0]
            segments.append(
                {
                    "corp_number": chosen_interval.get("corp_number"),
                    "building_name": chosen_interval.get("building_name"),
                    "building_id": chosen_interval.get("building_id"),
                    "period_from": segment_start.strftime("%Y%m%d"),
                    "period_to": segment_end.strftime("%Y%m%d"),
                    "file_update_date": chosen_interval.get("file_update_date"),
                    "ARVE_CORP_NAME": chosen_interval.get("ARVE_CORP_NAME"),
                    "ARVE_CUSTOMER_NUMBER": chosen_interval.get("ARVE_CUSTOMER_NUMBER"),
                    "ARVE_OFFICE_CODE": chosen_interval.get("ARVE_OFFICE_CODE"),
                }
            )

        return segments

    @staticmethod
    def _to_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if hasattr(value, "toordinal"):
            return value
        for fmt in ("%Y%m%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        return None
