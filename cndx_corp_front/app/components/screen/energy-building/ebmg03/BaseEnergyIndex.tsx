import React, { useEffect } from "react";
import { Icon } from "~/components/import";
import { EnergyBuildingDataset } from "~/types/screen/energy-building/ebmg/ebmgType";
import "../../../../styles/screen/energy-building/baseEnergyIndex.css";
import BaseEnergyIndexForm from "./BaseEnergyIndexForm";

type Props = {
  buildingDataset: EnergyBuildingDataset;
  startYearMonth: string;
  entryDraftFlag: string;
  onSelectItem: (key: string) => void;
  setHeaderTitle: (value: string) => void;
};

const BaseEnergyIndex: React.FC<Props> = ({
  buildingDataset,
  startYearMonth,
  entryDraftFlag,
  onSelectItem,
  setHeaderTitle,
}) => {
  const info = buildingDataset.buildings[0].building_info;
  const startYear = startYearMonth.slice(0, 4);
  const companyName = JSON.parse(sessionStorage.getItem("corporateData") ?? "")["company_name"];
  const draftStatusLabel = entryDraftFlag === "1" ? "下書き" : entryDraftFlag === "0" ? "登録済み" : "未登録";

  const isRegistered = entryDraftFlag === "0";

  const getSeq = () => {
    if (info.registration_seq == null) return 0;

    if (draftStatusLabel === "未登録") {
      return info.registration_seq + 1;
    }

    if (draftStatusLabel === "登録済み" || draftStatusLabel === "下書き") {
      return info.registration_seq;
    }

    return 1;
  };

  const isUnregistered = draftStatusLabel === "未登録";

  const displayBuildings = Object.values(
    buildingDataset.buildings.reduce((acc, building) => {
      const id = building.building_id;
      const current = acc[id];

      if (!current) {
        acc[id] = building;
        return acc;
      }
      if (isUnregistered) {
        if (building.building_info.registration_seq > current.building_info.registration_seq) {
          acc[id] = building;
        }
      } else {
        if (building.building_info.registration_seq === info.registration_seq) {
          acc[id] = building;
        }
      }

      return acc;
    }, {} as Record<string, (typeof buildingDataset.buildings)[number]>),
  );

  useEffect(() => {
    const title = `${startYear}-${getSeq()}`;
    setHeaderTitle(title);
  }, [startYear, info.registration_seq, draftStatusLabel]);

  return (
    <div className="index-comp h-full flex flex-col overflow-hidden">
      <div className="ml-1 flex-1 overflow-auto pt-[60px] pb-[110px]">
        <div className="index-title mb-1">
          <div
            className={
              isRegistered
                ? "register-index-status mb-1 border-[#5FE9D0] text-[#107569] justify-center"
                : "index-status mb-1 text-gray-400 border-gray-400"
            }
          >
            {draftStatusLabel}
          </div>
          <div>{companyName}</div>
          <h1 className="text-xl font-bold">{`${startYear}-${getSeq()}`}</h1>
        </div>

        <div className="flex justify-between w-[115px] items-center m-2">
          <Icon name="list" /> インデックス
        </div>

        {displayBuildings.map((building) => (
          <BaseEnergyIndexForm key={building.building_id} building={building} onSelectItem={onSelectItem} />
        ))}
      </div>
    </div>
  );
};
export default BaseEnergyIndex;
