import pytest
from pydantic import ValidationError

from cndx_corp_back.dto.building.energy_register_in_dto import (
    BuildingEnergyRegisterInDto,
    EnergyInfoSubDto,
    UpdatedBuildingInfoSubDto,
)

# 正常系: 必要なフィールドが全て揃っている場合


def test_valid_dto():
    dto = BuildingEnergyRegisterInDto(
        corporate_number="1234567890123",
        agreement_category="01",
        org_id="ORGID",
        fiscal_year="2024",
        start_year_month="202404",
        end_year_month="202503",
        entry_draft_flag="1",
        updated_building_info=[
            UpdatedBuildingInfoSubDto(
                building_id="1234567890123456789",
                building_name="テストビル",
                industry_class_major_code="A",
                industry_class_middle_code="01",
                industry_class_minor_code="011",
                industry_class_detail_code="0110",
                gross_floor_area=100.0,
                electric_company_reg_no="A0001",
                menu_no="1",
                ep_office_code="EP1",
                ep_customer_number="1111122222001",
                supply_point_number="1111100000111112220101",
                city_gas_reg_no="G0001",
                heat_supply_reg_no="H0001",
                energy_info=[
                    EnergyInfoSubDto(
                        energy_unit_original="kWh",
                        energy_code="0200010011",
                        energy_name_jp="電気",
                        energy_quantity=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                    )
                ],
            )
        ],
    )
    assert dto.corporate_number == "1234567890123"
    assert dto.updated_building_info[0].building_id == "1234567890123456789"


# 異常系: energy_usageが12未満


def test_energy_usage_length_error():
    with pytest.raises(ValidationError) as exc:
        EnergyInfoSubDto(
            energy_unit_original="kWh",
            energy_code="0200010011",
            energy_name_jp="電気",
            energy_quantity=[1, 2, 3],
        )
    assert "月のデータは12か月ではない" in str(exc.value)


# 異常系: building_idの長さ不正


def test_building_id_length_error():
    with pytest.raises(ValidationError) as exc:
        UpdatedBuildingInfoSubDto(
            building_id="123",
            building_name="テストビル",
            industry_class_major_code="A",
            industry_class_middle_code="01",
            industry_class_minor_code="011",
            industry_class_detail_code="0110",
            gross_floor_area=100.0,
            electric_company_reg_no="A0001",
            menu_no="1",
            ep_office_code="EP1",
            ep_customer_number="1111122222001",
            supply_point_number="1111100000111112220101",
            city_gas_reg_no="G0001",
            heat_supply_reg_no="H0001",
            energy_info=[],
        )
    assert "should have at least 19 characters" in str(exc.value)


# 異常系: updated_building_infoが空


def test_building_list_empty():
    with pytest.raises(ValidationError) as exc:
        BuildingEnergyRegisterInDto(
            corporate_number="1234567890123",
            agreement_category="01",
            org_id="ORGID",
            fiscal_year="2024",
            start_year_month="202404",
            end_year_month="202503",
            entry_draft_flag="1",
            updated_building_info=[],
        )
    assert "少なくとも1件の建物情報が必要" in str(exc.value)


# 異常系: start_year_monthの月が不正


def test_start_year_month_invalid():
    with pytest.raises(ValidationError) as exc:
        BuildingEnergyRegisterInDto(
            corporate_number="1234567890123",
            agreement_category="01",
            org_id="ORGID",
            fiscal_year="2024",
            start_year_month="202413",
            end_year_month="202503",
            entry_draft_flag="1",
            updated_building_info=[
                UpdatedBuildingInfoSubDto(
                    building_id="1234567890123456789",
                    building_name="テストビル",
                    industry_class_major_code="A",
                    industry_class_middle_code="01",
                    industry_class_minor_code="011",
                    industry_class_detail_code="0110",
                    gross_floor_area=100.0,
                    electric_company_reg_no="A0001",
                    menu_no="1",
                    ep_office_code="EP1",
                    ep_customer_number="1111122222001",
                    supply_point_number="1111100000111112220101",
                    city_gas_reg_no="G0001",
                    heat_supply_reg_no="H0001",
                    energy_info=[],
                )
            ],
        )
    assert "年月形式不正" in str(exc.value)


def test_entry_draft_flag_normalizes_to_0():
    dto = BuildingEnergyRegisterInDto(
        corporate_number="1234567890123",
        agreement_category="01",
        org_id="ORGID",
        fiscal_year="2024",
        start_year_month="202404",
        end_year_month="202503",
        entry_draft_flag=None,
        updated_building_info=[
            UpdatedBuildingInfoSubDto(
                building_id="1234567890123456789",
                building_name="テストビル",
                industry_class_major_code="A",
                industry_class_middle_code="01",
                industry_class_minor_code="011",
                industry_class_detail_code="0110",
                gross_floor_area=100.0,
                electric_company_reg_no="A0001",
                menu_no="1",
                ep_office_code="EP1",
                ep_customer_number="1111122222001",
                supply_point_number="1111100000111112220101",
                city_gas_reg_no="G0001",
                heat_supply_reg_no="H0001",
                energy_info=[],
            )
        ],
    )
    assert dto.entry_draft_flag == "0"


def test_entry_draft_flag_is_1():
    dto = BuildingEnergyRegisterInDto(
        corporate_number="1234567890123",
        agreement_category="01",
        org_id="ORGID",
        fiscal_year="2024",
        start_year_month="202404",
        end_year_month="202503",
        entry_draft_flag="1",
        updated_building_info=[
            UpdatedBuildingInfoSubDto(
                building_id="1234567890123456789",
                building_name="テストビル",
                industry_class_major_code="A",
                industry_class_middle_code="01",
                industry_class_minor_code="011",
                industry_class_detail_code="0110",
                gross_floor_area=100.0,
                electric_company_reg_no="A0001",
                menu_no="1",
                ep_office_code="EP1",
                ep_customer_number="1111122222001",
                supply_point_number="1111100000111112220101",
                city_gas_reg_no="G0001",
                heat_supply_reg_no="H0001",
                energy_info=[],
            )
        ],
    )
    assert dto.entry_draft_flag == "1"


def test_blank_to_null_registration_seq():
    dto = UpdatedBuildingInfoSubDto(
        building_id="1234567890123456789",
        building_name="テストビル",
        industry_class_major_code="A",
        industry_class_middle_code="01",
        industry_class_minor_code="011",
        industry_class_detail_code="0110",
        gross_floor_area=100.0,
        electric_company_reg_no="A0001",
        menu_no="1",
        ep_office_code="EP1",
        ep_customer_number="1111122222001",
        supply_point_number="1111100000111112220101",
        city_gas_reg_no="G0001",
        heat_supply_reg_no="H0001",
        energy_info=[],
        registration_seq="",
    )
    assert dto.registration_seq is None


def test_gross_area_in_draft():

    request_dict = {
        "corporate_number": "2025062401001",
        "agreement_category": "01",
        "org_id": "TEP",
        "start_year_month": "202404",
        "end_year_month": "202503",
        "fiscal_year": "2024",
        "entry_draft_flag": "0",
        "updated_building_info": [
            {
                "building_id": "1234567890123456789",
                "building_name": "テストビル",
                "industry_class_major_code": "A",
                "industry_class_middle_code": "01",
                "industry_class_minor_code": "011",
                "industry_class_detail_code": "0110",
                "gross_floor_area": None,
                "electric_company_reg_no": "A0001",
                "menu_no": "1",
                "ep_office_code": "EP1",
                "ep_customer_number": "1111122222001",
                "supply_point_number": "1111100000111112220101",
                "city_gas_reg_no": "G0001",
                "heat_supply_reg_no": "H0001",
                "energy_info": [],
            }
        ],
    }

    dto = BuildingEnergyRegisterInDto.model_validate(
        request_dict,
        context={
            "entry_draft_flag": "1",
            "insert_flag": True,
        },
    )
    assert dto.updated_building_info[0].gross_floor_area is None
