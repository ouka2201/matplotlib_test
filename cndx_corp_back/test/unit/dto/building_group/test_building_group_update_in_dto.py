import pytest
from pydantic import ValidationError

from cndx_corp_back.dto.building_group.building_group_update_in_dto import (
    BuildingGroupUpdateInDto,
)


def test_valid_building_group_update_in():
    """正常系: 必要なフィールドが全て揃っている場合"""

    dto = BuildingGroupUpdateInDto(
        corporate_number="1234567890123",
        agreement_category="01",
        org_id="ORGID",
        building_ids=["1234567890123456789"],
        selected_options={"1": "2"},
    )
    assert dto.corporate_number == "1234567890123"
    assert dto.selected_options == {"1": "2"}


def test_corporate_number_length_error():
    """異常系: corporate_numberが13桁未満"""

    with pytest.raises(ValidationError) as exc:
        BuildingGroupUpdateInDto(
            corporate_number="123",
            agreement_category="01",
            org_id="ORGID",
            building_ids=["1234567890123456789"],
            selected_options={"1": "2"},
        )
    assert "should have at least 13 characters" in str(exc.value)


def test_option_code_invalid_value():
    """異常系: option_codeに不正な値"""

    with pytest.raises(ValidationError) as exc:
        BuildingGroupUpdateInDto(
            corporate_number="1234567890123",
            agreement_category="01",
            org_id="ORGID",
            building_ids=["1234567890123456789"],
            selected_options={"1": "9"},
        )
    assert "Input should be '1', '2', '3', '4', '5', '6' or '7'" in str(exc.value)


def test_building_id_too_long():
    """異常系: building_idが19桁超"""

    with pytest.raises(ValidationError) as exc:
        BuildingGroupUpdateInDto(
            corporate_number="1234567890123",
            agreement_category="01",
            org_id="ORGID",
            building_ids=["12345678901234567890"],
            selected_options={"1": "1"},
        )
    assert "should have at most 19 characters" in str(exc.value)
