from typing import Literal, Optional, ClassVar, Set
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)
from pydantic_core import PydanticCustomError


class EnergyInfoSubDto(BaseModel):
    energy_unit_original: Optional[str] = Field(default=None,max_length=10)
    energy_code: Optional[str] = Field(default=None,max_length=20)
    energy_name_jp: Optional[str] = Field(default=None,max_length=50)
    energy_quantity: list[float] = Field(default_factory=list)
    # energy_usage_sum: str = Field(min_length=13, max_length=13)

    # ロバストネスのため
    # @field_validator("energy_quantity", mode="before")
    # @classmethod
    # def blank_to_0(cls, v):
    #     for i in range(len(v)):
    #         if v[i] == "":
    #             v[i] = "0"
    #     return v

    # 本登録かつ新規登録 のときの必須対象
    REQUIRED_FIELDS_FOR_INSERT: ClassVar[Set[str]] = {
        "energy_unit_original",
        "energy_code",
        "energy_name_jp",
        "energy_quantity",
    }

    @field_validator("energy_quantity")
    @classmethod
    def no_of_months(cls, v, info):
        # サブモデルでは context を参照
        draft_flag = info.context.get("entry_draft_flag") == "1"
        insert_flag  = info.context.get("insert_flag") is True
        # 下書き or 更新 のときはスキップ
        if draft_flag or not insert_flag:
            return v
        # 本登録かつ新規登録 のときだけ 12 ヶ月チェック
        if v is None or len(v) != 12:
            raise PydanticCustomError("period_error", "月のデータは12か月ではない。")
        return v

    @field_validator("*", mode="after")
    @classmethod
    def require_if_not_draft(cls, v, info):
        # サブモデルでは context を参照
        draft_flag = info.context.get("entry_draft_flag") == "1"
        insert_flag  = info.context.get("insert_flag") is True
        # 下書き or 更新 のときは必須チェックをスキップ
        if draft_flag or not insert_flag:
            return v
        # 本登録かつ新規登録 のときだけ、None/空をエラー
        if info.field_name in cls.REQUIRED_FIELDS_FOR_INSERT:
            if v in (None, [], ""):
                raise PydanticCustomError(
                    "field_required",
                    f"{info.field_name} は必須です（本登録かつ新規登録時）"
                )
        return v


class UpdatedBuildingInfoSubDto(BaseModel):
    building_id: Optional[str] = Field(default=None,min_length=19, max_length=113)
    building_name: Optional[str] = Field(default=None,max_length=100)
    industry_class_major_code: Optional[str] = Field(default=None,min_length=1, max_length=1)
    industry_class_middle_code: Optional[str] = Field(default=None,max_length=2)
    industry_class_minor_code: Optional[str] = Field(default=None,max_length=3)
    industry_class_detail_code: Optional[str] = Field(default=None,max_length=4)
    industry_class_major_name: Optional[str] = Field(default=None, max_length=50)
    industry_class_middle_name: Optional[str] = Field(default=None, max_length=50)
    industry_class_minor_name: Optional[str] = Field(default=None, max_length=50)
    industry_class_detail_name: Optional[str] = Field(default=None, max_length=50)
    gross_floor_area: Optional[float]  = Field(default=None)
    electric_company_reg_no: Optional[str] = Field(default=None,max_length=10)
    electricity_supplier_name: Optional[str] = Field(default=None, max_length=50)
    menu_no: Optional[str] = Field(default=None,max_length=50)
    ep_office_code: Optional[str] = Field(default=None,max_length=3)
    ep_customer_number: Optional[str] = Field(default=None, max_length=13)
    supply_point_number: Optional[str] = Field(default=None, max_length=22)
    city_gas_reg_no: Optional[str] | None = Field(default=None,max_length=10)
    city_gas_supplier_name: Optional[str] = Field(default=None, max_length=50)
    heat_supply_reg_no: Optional[str] | None = Field(default=None,max_length=10)
    heat_supplier_name: Optional[str] = Field(default=None, max_length=50)
    energy_info: list[EnergyInfoSubDto] = Field(default_factory=list)

    # 本登録かつ新規登録 のときの必須対象
    REQUIRED_FIELDS_FOR_INSERT: ClassVar[Set[str]] = {
        "building_id",
        "building_name",
        "industry_class_major_code",
        "industry_class_middle_code",
        "industry_class_minor_code",
        "industry_class_detail_code",
        "gross_floor_area",
        "electric_company_reg_no",
        "menu_no",
        "energy_info",
        "electricity_supplier_name"
    }

    # TODO 一時的
#    @field_validator("registration_seq", mode="before")
#    @classmethod
#    def blank_to_null(cls, v):
#        if v == "":
#            v = None
#        return v

    # gross_floor_area が空文字の場合、None に変更する
    @field_validator("gross_floor_area", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

    @field_validator("*", mode="after")
    @classmethod
    def require_if_not_draft(cls, v, info):
        # サブモデルでは context を参照
        draft_flag = info.context.get("entry_draft_flag") == "1"
        insert_flag  = info.context.get("insert_flag") is True
        # 下書き or 更新 のときは必須チェックをスキップ
        if draft_flag or not insert_flag:
            return v
        # 本登録かつ新規登録 のときだけ、None/空をエラー
        if info.field_name in cls.REQUIRED_FIELDS_FOR_INSERT:
            if v in (None, [], ""):
                raise PydanticCustomError(
                    "field_required",
                    f"{info.field_name} は必須です（本登録かつ新規登録時）"
                )
        return v


class BuildingEnergyRegisterInDto(BaseModel):

    corporate_number: str = Field(min_length=13, max_length=13)
    agreement_category: str = Field(max_length=2)
    org_id: str = Field(max_length=20)
    fiscal_year: str = Field(min_length=4, max_length=4)
    start_year_month: str = Field(min_length=6, max_length=6)
    end_year_month: str = Field(min_length=6, max_length=6)
    entry_draft_flag: Literal["0", "1"] = Field(max_length=1, default="")
    registration_seq: Optional[int] = None
    insert_flag:  bool = Field(default=False)
    updated_building_info: list[UpdatedBuildingInfoSubDto] = Field(default_factory=list)

    @field_validator("entry_draft_flag", mode="before")
    @classmethod
    def normalize_entry_flag(cls, v):
        # 文字列を "0"/"1" に正規化
        return "1" if v == "1" else "0"

    @field_validator("insert_flag", mode="before")
    @classmethod
    def normalize_insert_flag(cls, v: bool) -> bool:
        return bool(v)

    @field_validator("start_year_month")
    @classmethod
    def validate_month(cls, v):
        m = int(v[-2:])
        if m > 12 or m < 1:
            raise PydanticCustomError("invalid_month", "年月形式不正。")
        return v

    @field_validator("updated_building_info")
    @classmethod
    def validate_bld_list(cls, v, info):
        # ルートモデルでは data を参照
        draft_flag = info.data.get("entry_draft_flag") == "1"
        insert_flag  = info.data.get("insert_flag") is True
        # 本登録(0)かつ insert=True(新規登録) のときだけ、空リストをエラーにする
        if not draft_flag and insert_flag and not v:
            raise PydanticCustomError(
                "at_least_one","少なくとも1件の建物情報が必要です（本登録かつ新規登録時）")
        return v


