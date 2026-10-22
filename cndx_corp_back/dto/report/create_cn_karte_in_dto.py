from pydantic import BaseModel, Field

class CreateCnKarteInDto(BaseModel):
    """
    CNカルテ作成用DTO
    """
    org_id: str = Field(alias="組織ID", max_length=20)
    corporate_number: str = Field(alias="法人番号", max_length=13)
    agreement_category: str = Field(alias="同意書取得区分", max_length=2)
    fiscal_year: str = Field(alias="年度", max_length=4)
    registration_seq: int = Field(alias="登録回数")
