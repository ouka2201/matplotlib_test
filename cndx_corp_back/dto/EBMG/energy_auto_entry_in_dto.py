from typing import Annotated, Literal, Optional

from pydantic import (
    BaseModel,
    Field,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)


class EnergyAutoEntryIn(BaseModel):

    corporate_number: StrictStr = Field(
        ..., min_length=13, max_length=13, description="13桁の必須"
    )
    agreement_category: StrictStr = Field(
        ..., min_length=1, description="必須チェック"
    )
    start_year_month: StrictStr = Field(
        ..., min_length=6, max_length=6, description="YYYYMM 形式（6桁）の必須"
    )
    end_year_month: StrictStr = Field(
        ..., min_length=6, max_length=6, description="YYYYMM 形式（6桁）の必須"
    )
    ep_customer_number: StrictStr = Field(
        ..., max_length=16, description="最大16桁の必須"
    )
    supply_point_number: StrictStr = Field(
        ..., min_length=1, max_length=27, description="最大27桁の必須"
    )
