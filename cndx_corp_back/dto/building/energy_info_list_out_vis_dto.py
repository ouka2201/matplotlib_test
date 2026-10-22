from pydantic import BaseModel, Field

# class EnergyInfoSubDto(BaseModel):
#     item_no: int
#     energy_name: str
#     start_year_month: str
#     primary_energy_data: list[float] = [0] * 12
#     co2_emissions: list[float] = [0] * 12

class DataBuildingSubDto(BaseModel):
    # item_no: int
    building_id: str
    building_name: str
    start_year_month: str # The first month of period of data list
    primary_energy_data: list[float] = [0] * 12
    co2_emissions: list[float] = [0] * 12
    # energy_infos: list[EnergyInfoSubDto] = Field(default_factory=list)

class DataYearSubDto(BaseModel):
    fiscal_year: str
    data_buildings: list[DataBuildingSubDto] = Field(default_factory=list)

class DataVendorSubDto(BaseModel):
    vis_vendor_name: str
    data_years: list[DataYearSubDto] = Field(default_factory=list)

class BuildingEnergyInfoListOutVisDto(BaseModel):
    data_vendors: list[DataVendorSubDto] = Field(default_factory=list)
    org_id:str
    agreement_category:str