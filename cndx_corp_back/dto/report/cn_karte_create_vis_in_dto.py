from typing import Literal, Annotated
from pydantic import BaseModel, Field, model_validator
from typing import Optional


class GroupFilterDto(BaseModel):
    """
    グループ化・フィルターDTO
    """
    group_no: Literal["1","2","3","4","5"] = Field(max_length=2)
    option_no: Literal["1","2","3","4","5","6","7"] = Field(max_length=20)

class CreateCnKarteVisInDto(BaseModel):
    """
    CNカルテ作成可視化側用DTO
    """
    corporate_number: str = Field(max_length=13)
    start_year: str = Field(max_length=4)
    start_month: str = Field(max_length=2)
    creation_format: str = Field(max_length=10)
    org_id: str = Field(max_length=20)
    need_data_insufficiency_list: bool = Field(default=False)
    need_report_backdata: bool = Field(default=False)
    need_kpi_list: bool = Field(default=False)
    is_for_multibuilding: bool
    group_for_multibuilding: list[GroupFilterDto] = Field(max_length=2, default_factory=list)
    building_ids_for_single: list[str] = Field(default_factory=list)
    agreement_category: str = Field(max_length=2)
    fiscal_year: Optional[str] = Field(default=None, alias="年度", max_length=4)

    # ★ 追加：後工程で必須チェックされるフィールド
    end_year: Optional[str] = Field(default=None, max_length=4)
    end_month: Optional[str] = Field(default=None, max_length=2) 
    consent_route: Optional[str] = Field(default=None, max_length=100)

    # 登録処理に必要なフィールドを追加　チェック不要
    user_email: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def not_for_single(self):
        if not self.is_for_multibuilding and self.group_for_multibuilding:
            raise ValueError("複数拠点の場合のみグループが設定可能。")
        return self
