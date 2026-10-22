from pydantic import BaseModel, Field


class UiOptionInPrefDto(BaseModel):

    pref_cd: str = Field(min_length=2, max_length=2)
