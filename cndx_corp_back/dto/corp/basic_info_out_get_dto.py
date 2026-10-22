from pydantic import BaseModel, Field


class BasicInfoOutGetDto(BaseModel):

    corporate_number: str = Field(min_length=13, max_length=13)
