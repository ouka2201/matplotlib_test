from typing import Optional

from flask import abort
from pydantic import BaseModel, Field, model_validator


class UiOptionConsentInDto(BaseModel):

    group_code: Optional[str] = Field(min_length=1,max_length=1,default=None)
    org_id: Optional[str] = Field(max_length=20,default=None)

    @model_validator(mode="after")
    def only_with_vis_allowed(self):
        if self.org_id and self.group_code is not "1":
            abort(400)
        return self