import pytest
from pydantic import ValidationError

from cndx_corp_back.dto.report.cn_karte_create_vis_in_dto import (
    CreateCnKarteVisInDto as InDto,
)
from cndx_corp_back.dto.report.cn_karte_create_vis_in_dto import GroupFilterDto


def test_valid_cn_karte_create_vis_in_dto_1():
    """正常系: 複数拠点カルテ作成 & 企業全体"""
    request = {
        "corporate_number": "1234567890123",
        "start_year": "2024",
        "start_month": "04",
        "creation_format": "A",
        "org_id": "ORGID",
        "agreement_category": "01",
        "need_data_insufficiency_list": True,
        "need_report_backdata": False,
        "need_kpi_list": True,
        "is_for_multibuilding": True,
    }
    dto = InDto.model_validate(request, by_alias=False, by_name=True)
    assert dto.corporate_number == "1234567890123"
    assert dto.is_for_multibuilding is True


def test_valid_cn_karte_create_vis_in_dto_2():
    """正常系: 複数拠点カルテ作成 & グループ"""
    request = {
        "corporate_number": "1234567890123",
        "start_year": "2024",
        "start_month": "04",
        "creation_format": "A",
        "org_id": "ORGID",
        "agreement_category": "01",
        "need_data_insufficiency_list": True,
        "need_report_backdata": False,
        "need_kpi_list": True,
        "is_for_multibuilding": True,
        "group_for_multibuilding": [
            {"group_no": "1", "option_no": "2"},
            {"group_no": "2", "option_no": "1"},
        ],
    }

    dto = InDto.model_validate(request, by_alias=False, by_name=True)

    assert dto.corporate_number == "1234567890123"
    assert dto.is_for_multibuilding is True
    assert len(dto.group_for_multibuilding) == 2


def test_valid_cn_karte_create_vis_in_dto_3():
    """正常系: 単拠点カルテ作成"""

    request = {
        "corporate_number": "1234567890123",
        "start_year": "2024",
        "start_month": "04",
        "creation_format": "A",
        "org_id": "ORGID",
        "agreement_category": "01",
        "need_data_insufficiency_list": True,
        "need_report_backdata": False,
        "need_kpi_list": True,
        "is_for_multibuilding": False,
        "building_ids_for_single": ["1234567890123456789", "9876543210123456789"],
    }
    dto = InDto.model_validate(request, by_alias=False, by_name=True)

    assert dto.corporate_number == "1234567890123"
    assert dto.is_for_multibuilding is False
    assert len(dto.building_ids_for_single) == 2


def test_corporate_number_length_error():
    """異常系: corporate_numberが13桁未満"""
    with pytest.raises(ValidationError) as exc:
        request = {
            "corporate_number": "123",
            "fiscal_year": "2024",
            "period_from": "202404",
            "creation_format": "A",
            "org_id": "ORGID",
            "agreement_category": "01",
            "need_data_insufficiency_list": True,
            "need_report_backdata": False,
            "need_kpi_list": True,
            "is_for_multibuilding": True,
            "group_for_multibuilding": [],
            "building_ids_for_single": ["1234567890123456789"],
        }
        dto = InDto.model_validate(request, by_alias=False, by_name=True)

    assert "ensure this value has at least 13 characters" in str(exc.value)


# 異常系: group_noが2桁超


def test_group_no_too_long():
    with pytest.raises(ValidationError) as exc:
        InDto(
            corporate_number="1234567890123",
            fiscal_year="2024",
            period_from="202404",
            creation_format="A",
            org_id="ORGID",
            agreement_category="01",
            need_data_insufficiency_list=True,
            need_report_backdata=False,
            need_kpi_list=True,
            is_for_multibuilding=True,
            group_for_multibuilding=[GroupFilterDto(group_no="012", option_no="A1")],
            building_ids_for_single=["1234567890123456789"],
        )
    assert "ensure this value has at most 2 characters" in str(exc.value)


# 異常系: building_ids_for_singleのbuilding_idが19桁超


def test_building_id_too_long():
    with pytest.raises(ValidationError) as exc:
        InDto(
            corporate_number="1234567890123",
            fiscal_year="2024",
            start_year="2024",
            start_month="04",
            creation_format="A",
            org_id="ORGID",
            agreement_category="01",
            need_data_insufficiency_list=True,
            need_report_backdata=False,
            need_kpi_list=True,
            is_for_multibuilding=True,
            group_for_multibuilding=[],
            building_ids_for_single=["12345678901234567890", "1", "2"],
        )
    assert "ensure this value has at most 19 characters" in str(exc.value)
