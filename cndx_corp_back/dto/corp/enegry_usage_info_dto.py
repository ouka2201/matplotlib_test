from dataclasses import dataclass
from typing import List, Optional

from cndx_corp_back.common.decorators import auto_filter_kwargs


@auto_filter_kwargs
@dataclass
class EnegryUsageInfoDTO:
    """
    エネルギー使用情報DTO
    """

    year: str = ""
    month: str = ""
    import_raw_charcoal: str = ""
    coking_coal: str = ""
    pci_coal: str = ""
    import_ordinary_charcoal: str = ""
    domestic_standard_coal: str = ""
    import_smokeless_coal: str = ""
    coal_coke: str = ""
    petroleum_coke: str = ""
    fcc_coke: str = ""
    coal_tar: str = ""
    petroleum_asphalt: str = ""
    crude_oil_condensate: str = ""
    crude_oil_condensate_except: str = ""
    gasoline: str = ""
    naphtha: str = ""
    jetFuel: str = ""
    kerosene: str = ""
    light_oil: str = ""
    heavy_oil_a: str = ""
    heavy_oil_bc: str = ""
    lubricating_oil: str = ""
    lpg: str = ""
    petroleum_hydrocarbon_gas: str = ""
    lng: str = ""
    natural_gas: str = ""
    coke_oven_gas: str = ""
    blastFurnace_gas: str = ""
    power_generationBlastFurnace_gas: str = ""
    converter_gas: str = ""
    city_gas: str = ""
    industrial_steam: str = ""
    industrial_except_steam: str = ""
    warm_water: str = ""
    cold_water: str = ""
    electric_power: str = ""
    crude_oil_condensate_ngl: str = ""
