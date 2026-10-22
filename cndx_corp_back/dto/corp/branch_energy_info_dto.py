from dataclasses import dataclass, field


@dataclass
class BasicInfoDTO:
    """
    事業所基本情報DTO
    """

    branch_name: str = ""
    building_name: str = ""
    industrial_classificationcode: str = ""
    address: str = ""
    gross_floor_area: str = ""
    electric_power_corporate_name: str = ""
    ep_store_number: str = ""
    customer_number_ep: str = ""
    supply_point_number: str = ""
    contracted_power: str = ""
    year: str = ""
    month: str = ""


@dataclass
class EnegryUsageInfoDTO:
    """
    エネルギー使用情報DTO
    """

    import_raw_charcoal: list[str] = field(default_factory=list)
    coking_coal: list[str] = field(default_factory=list)
    pci_coal: list[str] = field(default_factory=list)
    import_ordinary_charcoal: list[str] = field(default_factory=list)
    domestic_standard_coal: list[str] = field(default_factory=list)
    import_smokeless_coal: list[str] = field(default_factory=list)
    coal_coke: list[str] = field(default_factory=list)
    petroleum_coke: list[str] = field(default_factory=list)
    fcc_coke: list[str] = field(default_factory=list)
    coal_tar: list[str] = field(default_factory=list)
    petroleum_asphalt: list[str] = field(default_factory=list)
    crude_oil_condensate: list[str] = field(default_factory=list)
    crude_oil_condensate_except: list[str] = field(default_factory=list)
    gasoline: list[str] = field(default_factory=list)
    naphtha: list[str] = field(default_factory=list)
    jet_fuel: list[str] = field(default_factory=list)
    kerosene: list[str] = field(default_factory=list)
    light_oil: list[str] = field(default_factory=list)
    heavy_oil_a: list[str] = field(default_factory=list)
    heavy_oil_bc: list[str] = field(default_factory=list)
    lubricating_oil: list[str] = field(default_factory=list)
    lpg: list[str] = field(default_factory=list)
    petroleum_hydrocarbon_gas: list[str] = field(default_factory=list)
    lng: list[str] = field(default_factory=list)
    natural_gas: list[str] = field(default_factory=list)
    coke_oven_gas: list[str] = field(default_factory=list)
    blast_furnace_gas: list[str] = field(default_factory=list)
    power_generation_blast_furnace_gas: list[str] = field(default_factory=list)
    converter_gas: list[str] = field(default_factory=list)
    city_gas: list[str] = field(default_factory=list)
    industrial_steam: list[str] = field(default_factory=list)
    industrial_except_steam: list[str] = field(default_factory=list)
    warm_water: list[str] = field(default_factory=list)
    cold_water: list[str] = field(default_factory=list)
    electric_power: list[str] = field(default_factory=list)
    crude_oil_condensate_ngl: list[str] = field(default_factory=list)


@dataclass
class BranchEnergyInfoDTO:
    """
    事業所別エネルギー情報DTO
    """

    basic_info: BasicInfoDTO = field(default_factory=BasicInfoDTO)

    energy_usage_info: EnegryUsageInfoDTO = field(default_factory=EnegryUsageInfoDTO)
