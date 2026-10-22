from pydantic import BaseModel


class CorpBasicInfoOutGetDto(BaseModel):

    corporate_number: str
    agreement_category:str
    agreement_name:str
    org_id:str
    company_name: str
    company_address: str
    industry_class_major_name: str
    industry_class_middle_name: str
    industry_class_minor_name: str
    industry_class_detail_name: str
    business_office_count: int
