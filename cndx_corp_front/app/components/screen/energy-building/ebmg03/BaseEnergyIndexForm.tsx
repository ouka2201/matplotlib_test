import BaseEnergyIndexComp from "./BaseEnergyIndexComp";
import "../../../../styles/screen/energy-building/baseEnergyIndex.css";
import { Building } from "~/types/screen/energy-building/ebmg/ebmgType";

type Props = {
  building: Building;
  onSelectItem: (key: string) => void;
};

const BaseEnergyIndexForm: React.FC<Props> = ({ building, onSelectItem, }) => {
  const info = building.building_info;

  return (
    <div>
      <BaseEnergyIndexComp buildingName={info.building_name} buildingId={building.building_id} onSelectItem={onSelectItem} />
    </div>
  );
};
export default BaseEnergyIndexForm;
