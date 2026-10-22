from typing import Annotated, Literal, Optional

from pydantic import (
    BaseModel,
    Field,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)


class BuildingEnergyInfoListIn(BaseModel):

    corporate_number: StrictStr = Field(min_length=13, max_length=13)
    agreement_category: Annotated[StrictStr | None, Field(min_length=2, max_length=2)] = None
    fiscal_year: Annotated[StrictStr | None, Field(min_length=4, max_length=4)] = None
    org_id: str | None = None

    # @model_validator(mode="after")
    # def year_is_req_when_vis(self):
    #     if self.agreement_code == "2" and not self.fiscal_year:
    #         raise ValidationError()
    #     return self
