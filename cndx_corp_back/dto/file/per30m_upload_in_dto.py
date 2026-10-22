from pydantic import BaseModel, Field


class Per30mUploadInDto(BaseModel):

    # corporate_number: str = Field(min_length=13, max_length=13)
    corp_number: str = Field(min_length=13, max_length=13)
    building_id: str = Field(max_length=113)
    corp_name: str = Field(max_length=100)
    building_name: str = Field(max_length=100)
    ep_customer_number: str = Field(max_length=13)
    supply_point_number: str = Field(max_length=27)
    org_id: str = Field(max_length=20)
    agreement_category: str = Field(max_length=2)
    ep_office_code: str = Field(max_length=3)
