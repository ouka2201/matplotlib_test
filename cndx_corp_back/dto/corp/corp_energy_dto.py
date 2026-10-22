from dataclasses import dataclass, field
from typing import List, Optional

from cndx_corp_back.dto.corp.branch_energy_dto import BranchEnergyDTO

from ...common.decorators import auto_filter_kwargs


@auto_filter_kwargs
@dataclass
class FinancialInstitutionInfo:
    """金融機関情報"""

    bank_name: str = ""
    bank_code: str = ""
    branch_name: str = ""
    branch_code: str = ""
    bank_staff_name: str = ""
    bank_staff_tel_no: str = ""
    bank_staff_email: str = ""


@auto_filter_kwargs
@dataclass
class CorporateInfo:
    """企業情報"""

    corporate_name: str = ""
    corporate_number: str = ""
    headquarters_address: str = ""
    number_offices: str = ""
    industry_broad_categorization: str = ""
    industry_intermediate_classification: str = ""
    financial_year: str = ""
    start_period: str = ""
    end_period: str = ""
    corp_staff_name: str = ""
    corp_staff_phone_number: str = ""
    data_usage_permission_date: str = ""


@auto_filter_kwargs
@dataclass
class CorpEnergyDTO:
    """入力シートDTO"""

    financial_institution_info: FinancialInstitutionInfo = field(
        default_factory=FinancialInstitutionInfo
    )
    corporate_info: CorporateInfo = field(default_factory=CorporateInfo)
    # id: Optional[int] = None

    # 金融機関情報．基本情報
    bank_name: str = ""
    band_code: str = ""
    # 金融機関情報．ご担当者様情報
    bank_branch_name: str = ""
    bank_branch_code: str = ""
    bank_staff_name: str = ""
    bank_phone_number: str = ""
    bank_email_address: str = ""
    # 企業情報．基本情報
    company_name: str = ""
    corporate_number: str = ""
    office_address: str = ""
    number_offices: str = ""
    # industry_broad_category: str = ""
    # industry_intermediate_classification: str = ""
    industry_cate_large: str = ""
    industry_cate_middle: str = ""
    reporting_year: str = ""
    start_period: str = ""
    end_period: str = ""
    # 企業情報．データ授受に関する情報
    corp_staff_name: str = ""
    corp_staff_phone_number: str = ""
    data_usage_permission_date: str = ""

    branch_energy_dto_list: list[BranchEnergyDTO] = field(default_factory=list)
