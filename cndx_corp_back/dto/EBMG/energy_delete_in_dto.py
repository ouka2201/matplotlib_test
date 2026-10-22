from typing import Annotated, Literal, Optional

from pydantic import (
    BaseModel,
    Field,
    StrictStr,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

class EnergyInfoDto(BaseModel):
    energy_code: StrictStr = Field(
        min_length=1, max_length=19
    )

class UpdatedBuildingDeleteDto(BaseModel):
    building_id: StrictStr = Field(
        ..., min_length=1, max_length=19, description="必須チェック"
    )
    energy_info: Optional[list[EnergyInfoDto]] = None

class EnergyDeleteIn(BaseModel):

    corporate_number: StrictStr = Field(
        ..., min_length=13, max_length=13, description="13桁の必須"
    )
    agreement_category: StrictStr = Field(
        ..., description="必須チェック"
    )
    fiscal_year: StrictStr = Field(
        ..., min_length=4, max_length=4, description="YYYY 形式（4桁）の必須"
    )
    registration_seq: StrictInt = Field(
        ..., description="必須チェック"
    )
    start_year_month: StrictStr = Field(
        ..., min_length=6, max_length=6, description="YYYYMM 形式（6桁）の必須"
    )
    org_id: str 
    updated_building_delete: list[UpdatedBuildingDeleteDto] = Field(default_factory=list)

