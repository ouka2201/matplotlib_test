from pydantic import BaseModel


class UiOptionOutDto(BaseModel):
    code: str
    text: str
