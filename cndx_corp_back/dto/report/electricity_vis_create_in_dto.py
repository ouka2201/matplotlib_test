from pydantic import BaseModel, Field, ValidationError, model_validator
from typing import Optional

class ElectricityVisCreateInDto(BaseModel):
    """
    電力見える化レポート作成用DTO
    """
    corporate_number: str = Field(alias="法人番号", max_length=13)
    agreement_category: str = Field(alias="同意書取得区分", max_length=2, default="11")
    org_id: str = Field(alias="登録組織ID", max_length=20)
    building_id: str = Field(min_length=19, max_length=19)
    month_from: str = Field(max_length=6)
    target_month: str = Field(max_length=6)
    contracted_power:float
    fiscal_year: str = Field(alias="年度", max_length=4)
    user_id: Optional[str] = None
