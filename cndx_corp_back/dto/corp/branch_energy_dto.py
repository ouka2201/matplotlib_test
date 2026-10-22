from dataclasses import dataclass, field
from typing import List, Optional

from cndx_corp_back.common.decorators import auto_filter_kwargs
from cndx_corp_back.dto.corp.enegry_usage_info_dto import EnegryUsageInfoDTO


@auto_filter_kwargs
@dataclass
class BasicInfoDTO:
    """
    事業所基本情報DTO
    """

    branch_name: str = ""
    building_name: str = ""
    industrial_sub_classificationcode: str = ""
    industrial_classificationcode: str = ""
    supply_point_number: str = ""
    customer_number_ep: str = ""
    address: str = ""
    building_completionYear: str = ""
    building_seismic_standards: str = ""
    grossFloor_area: str = ""
    electric_power_corporate_name: str = ""
    contracted_power: str = ""
    electricity_usageFee_summer: str = ""
    electricity_usageFeeOther_seasons: str = ""
    fuel_cost_adjustment: str = ""
    renewable_energy_surcharge: str = ""
    employees: str = ""
    annual_working_days: str = ""
    one_dayworking_hours: str = ""


@auto_filter_kwargs
@dataclass
class GasApplicationInfoDTO:
    """
    ガスの使用用途DTO
    """

    water_heating: str = ""
    production_use: str = ""
    air_conditioning_use: str = ""


@auto_filter_kwargs
@dataclass
class RenewableEnergyUsageInfoDTO:
    """
    再エネ利用状況DTO
    """

    power_generation_facilities: str = ""
    renewable_energy_power: str = ""
    environmental_certificate: str = ""


@auto_filter_kwargs
@dataclass
class SolarPowerInfoDTO:
    """
    太陽光情報情報DTO
    """

    roof_area: str = ""
    parking_area: str = ""


@auto_filter_kwargs
@dataclass
class AirConditioningInfoDTO:
    """
    空調情報DTO
    """

    air_conditioning_system: str = ""
    need_air_conditioning_replacement: str = ""
    year_air_conditioning_replacement: str = ""


@auto_filter_kwargs
@dataclass
class LightingInfoDTO:
    """
    照明情報DTO
    """

    fluorescent_lights_percentage: str = ""
    led_lights_percentage: str = ""


@auto_filter_kwargs
@dataclass
class BranchEnergyDTO:
    """
    事業所別エネルギー情報DTO
    """

    basic_info_dto: BasicInfoDTO = field(default_factory=BasicInfoDTO)

    gas_application_info_dto: GasApplicationInfoDTO = field(
        default_factory=GasApplicationInfoDTO
    )

    renewable_energy_usage_info_dto: RenewableEnergyUsageInfoDTO = field(
        default_factory=RenewableEnergyUsageInfoDTO
    )

    solar_power_info_dto: SolarPowerInfoDTO = field(default_factory=SolarPowerInfoDTO)

    air_conditioning_info_dto: AirConditioningInfoDTO = field(
        default_factory=AirConditioningInfoDTO
    )

    lighting_info_dto: LightingInfoDTO = field(default_factory=LightingInfoDTO)

    enegry_usage_info_dto: list[EnegryUsageInfoDTO] = field(default_factory=list)
