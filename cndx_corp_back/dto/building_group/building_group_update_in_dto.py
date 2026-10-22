from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

class BuildingGroupUpdateInDto(BaseModel):

    corporate_number: str = Field(min_length=13, max_length=13)
    agreement_category: str = Field(max_length=2)
    org_id: str = Field(max_length=20)
    # building_id: str
    building_ids: list[str]
    selected_options: dict[str, str] # allowed keys : 1-5

    @classmethod
    @field_validator("building_ids")
    def check_bid_lengths(cls, v):
        err_indices = []
        for i, bid in enumerate(v):
            if len(bid) > 19:
                err_indices.append(i)
        if err_indices:
            raise ValueError(f"{", ".join(f"building_ids[{err_indices}]")} is/are too long (max 19 characters)")
        return v
