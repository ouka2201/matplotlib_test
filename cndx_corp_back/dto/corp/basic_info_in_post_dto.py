from datetime import datetime

from pydantic import BaseModel, Field


class BasicInfoInPostDto(BaseModel):

    corporate_number: str = Field(min_length=13, max_length=13)
    agreement_category:str = Field(max_length=15)
    org_id:str | None = None
    industry_class_major_code: str = Field(min_length=1,max_length=1)
    industry_class_middle_code: str = Field(min_length=2,max_length=2)
    industry_class_minor_code: str = Field(min_length=3,max_length=3)
    industry_class_detail_code: str = Field(min_length=4,max_length=4)
    industry_class_major_name: str = Field(default=None,max_length=50)
    industry_class_middle_name: str = Field(default=None,max_length=50)
    industry_class_minor_name: str = Field(default=None,max_length=50)
    industry_class_detail_name: str = Field(default=None,max_length=50)
    business_office_count: int
    updated_by: str = None
    updated_at: str = Field(default_factory=datetime.now)
