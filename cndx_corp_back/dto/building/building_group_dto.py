from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class BuildingGroupUpdateDTO:
    """
    建物グループ一括更新用DTO
    """
    building_ids: List[str] = field(default_factory=list)
    group_fields: Dict[str, str] = field(default_factory=dict)
    updated_by: str = ""
