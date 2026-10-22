from datetime import datetime

from pydantic import BaseModel, ValidationError, field_validator


class BuildingEnergyInfoListOutBank(BaseModel):
    fiscal_year: str
    # agreement_code: str
    registration_seq: int
    entry_draft_flag: str
    report_period_start_year_month: str
    report_period_end_year_month: str
    staff_org: str
    business_office_count: int
    staff_user_name: str
    created_at: str

    @field_validator("created_at", mode="before")
    @classmethod
    def time_tostr(cls, v:datetime):
        if not isinstance(v, datetime):
            raise ValidationError()
        return v.strftime("%Y/%m/%d")
