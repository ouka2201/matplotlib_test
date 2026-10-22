from dataclasses import dataclass
from typing import Optional

from ..common.decorators import auto_filter_kwargs


@auto_filter_kwargs
@dataclass
class InquiryDTO:
    """
    調査表DTO
    """

    id: Optional[int] = None
    reportingYear: str = ""
    companyName: str = ""
    deploymentName: str = ""
    reptName: str = ""
    internalNumber: str = ""
    industryClassification: str = ""
    electricitySupply: str = ""
    gasBusinessName: str = ""
    otherGasBusinessName: str = ""

    @staticmethod
    def for_insert(data: dict) -> "InquiryDTO":
        """
        登録用のデータをInquiryDTOに変換
        """
        data = {k: v for k, v in data.items() if k != "id"}
        return InquiryDTO(**data)

    @staticmethod
    def for_update(data: dict) -> "InquiryDTO":
        """
        更新用のデータをInquiryDTOに変換
        """
        return InquiryDTO(**data)

    @staticmethod
    def for_delete(data: dict) -> "InquiryDTO":
        """
        削除用のデータをInquiryDTOに変換
        """
        return InquiryDTO(**data)

    @staticmethod
    def for_search(data: dict) -> "InquiryDTO":
        """
        検索用のデータをInquiryDTOに変換
        """
        return InquiryDTO(**data)
