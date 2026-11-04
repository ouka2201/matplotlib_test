"""営業担当引継予定の登録を同一トランザクションで実行する。"""

from sqlalchemy import text

from cndx_corp_back.common.database_manager import get_scoped_session
from cndx_corp_back.constant.handover_constants import (
    HANDOVER_ALREADY_PROCESSED,
    HANDOVER_STATUS_PLANNED,
    HANDOVER_TYPE_BULK,
    HANDOVER_TYPE_INDIVIDUAL,
    HANDOVER_UNASSIGNED_COMPANY,
)
from cndx_corp_back.logic.contact_person.handover_validation_logic import (
    validate_handover,
)
from cndx_corp_back.query.handover_query import (
    DELETE_PLANNED_HANDOVER,
    SELECT_ASSIGNED_COMPANIES,
    SELECT_PLANNED_COMPANIES,
    UPSERT_HANDOVER,
)


def register_handover(data: dict, user_context: dict, handover_type: str) -> None:
    numbers = validate_handover(data, user_context, handover_type)
    params = {
        "from_org": data["handover_from_org_id"],
        "from_user": data["handover_from_user_id"],
        "to_org": data["handover_to_org_id"],
        "to_user": data["handover_to_user_id"],
        "schedule": data["handover_schedule_date"],
        "report_flg": data["report_data_flg"],
        "type": handover_type,
        "status": HANDOVER_STATUS_PLANNED,
        "user_id": user_context["user_id"],
        "org_id": user_context["org_id"],
    }
    with get_scoped_session() as session:
        assigned = (
            session.execute(text(SELECT_ASSIGNED_COMPANIES), params).scalars().all()
        )
        if handover_type == HANDOVER_TYPE_BULK:
            numbers = assigned
        elif not set(numbers) <= set(assigned):
            raise ValueError(HANDOVER_UNASSIGNED_COMPANY)

        for number in numbers:
            saved = session.execute(
                text(UPSERT_HANDOVER), {**params, "corporate_number": number}
            ).first()
            if saved is None:
                raise ValueError(HANDOVER_ALREADY_PROCESSED)

        if handover_type == HANDOVER_TYPE_INDIVIDUAL:
            existing = (
                session.execute(text(SELECT_PLANNED_COMPANIES), params).scalars().all()
            )
            for number in set(existing) - set(numbers):
                session.execute(
                    text(DELETE_PLANNED_HANDOVER),
                    {**params, "corporate_number": number},
                )
