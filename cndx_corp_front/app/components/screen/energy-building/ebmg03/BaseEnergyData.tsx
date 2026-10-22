import React, { RefObject, useCallback, useMemo, useRef, useState } from "react";
import { UseFormReturn } from "react-hook-form";
import { Text } from "~/components/import";
import { AlertModal } from "~/components/modal/alert-modal";
import BuildingEnergyForm from "~/components/screen/energy-building/ebmg03/BuildingEnergyForm";
import { Button } from "~/components/ui/button";
import {
  BuildingInfo,
  BuildingInfoFormValues,
  EnergyBuildingDataset,
} from "~/types/screen/energy-building/ebmg/ebmgType";
import { CustomerCompany } from "~/types/screen/master/mscs/mscsType";
import Icon from "../../../icon";

type Option = {
  id: string;
  name: string;
};

type Props = {
  buildingDataset: EnergyBuildingDataset;
  prefectureOptions: Option[];
  industryClassMinorOptions: Option[];
  industryClassDetailOptions: Option[];
  cityGasOptions: Option[];
  heatSupplyOptions: Option[];
  isEditing: boolean;
  setIsEditing: (v: boolean) => void;
  setEditedData: React.Dispatch<React.SetStateAction<Record<string, Partial<BuildingInfo>>>>;
  editedData: Record<string, Partial<BuildingInfo>>;
  corporateData: CustomerCompany | null;
  agreementCategory: string;
  startYearMonth: string;
  endYearMonth: string;
  buildingFormRefs: React.MutableRefObject<Record<string, UseFormReturn<BuildingInfo>>>;
  errorMessage: string | string[];
  setErrorMessage: React.Dispatch<React.SetStateAction<string | string[]>>;
  scrollTargetRef: RefObject<HTMLDivElement>;
  userId: string;
  orgId: string;
  createOrgId: string;
  token: string | null;
  setIsFormDirty: (dirty: boolean) => void;
  scrollRefMap: React.MutableRefObject<Record<string, React.RefObject<HTMLDivElement>>>;
  isConfirmation: boolean;
  setIsConfirmation: React.Dispatch<React.SetStateAction<boolean>>;
  confirmedValues: Record<string, BuildingInfoFormValues>;
  isGoingToConfirmation: boolean;
  setIsGoingToConfirmation: React.Dispatch<React.SetStateAction<boolean>>;
  pendingConfirmData: Record<string, BuildingInfoFormValues> | null;
  setPendingConfirmData: React.Dispatch<React.SetStateAction<Record<string, BuildingInfoFormValues> | null>>;
  triggerConfirm: boolean;
  setTriggerConfirm: React.Dispatch<React.SetStateAction<boolean>>;
  onSetResetFunc?: (buildingId: string, func: (values: any | null) => void) => void;
  resetTrigger: number;
  onDeleteBuildingData: (buildingIds: string[]) => void;
  forwardTriggerRef: React.MutableRefObject<{
    [buildingId: string]: {
      trigger: () => Promise<boolean>;
      getValues: () => BuildingInfoFormValues;
    };
  }>;
  validationMode: "nonRequired" | "full";
  loginOrgId: string;
};

export type BuildingEnergyFormHandle = {
  getValues: () => BuildingInfo;
  validate: () => boolean;
};

const BaseEnergyData: React.FC<Props> = ({
  buildingDataset,
  prefectureOptions,
  industryClassMinorOptions: passedIndustryClassMinorOptions,
  industryClassDetailOptions: passedIndustryClassDetailOptions,
  cityGasOptions: passedCityGasOptions,
  heatSupplyOptions: passedHeatSupplyOptions,
  isEditing = false,
  setIsEditing,
  setEditedData,
  editedData,
  corporateData,
  agreementCategory,
  startYearMonth,
  endYearMonth,
  buildingFormRefs,
  errorMessage,
  setErrorMessage,
  scrollTargetRef,
  userId,
  orgId,
  createOrgId,
  token,
  setIsFormDirty,
  scrollRefMap,
  isConfirmation,
  setIsConfirmation,
  confirmedValues,
  isGoingToConfirmation,
  setIsGoingToConfirmation,
  pendingConfirmData,
  setPendingConfirmData,
  triggerConfirm,
  setTriggerConfirm,
  onSetResetFunc,
  resetTrigger,
  onDeleteBuildingData,
  validationMode,
  forwardTriggerRef,
  loginOrgId,
}) => {
  const formRefs = useRef<Record<string, React.RefObject<BuildingEnergyFormHandle>>>({});
  const getFormRef = useCallback((buildingId: string) => {
    if (!formRefs.current[buildingId]) {
      formRefs.current[buildingId] = React.createRef<BuildingEnergyFormHandle>();
    }
    return formRefs.current[buildingId];
  }, []);

  const industryClassMinorOptions = useMemo(() => {
    if (passedIndustryClassMinorOptions) return passedIndustryClassMinorOptions;
    if (!buildingDataset?.industry_class_minor) return [];
    return buildingDataset.industry_class_minor.map(({ group_code, group_name }) => ({
      id: group_code,
      name: group_name,
    }));
  }, [passedIndustryClassMinorOptions, buildingDataset]);

  const industryClassDetailOptions = useMemo(() => {
    if (passedIndustryClassDetailOptions) return passedIndustryClassDetailOptions;
    if (!buildingDataset?.industry_class_detail) return [];
    return buildingDataset.industry_class_detail.map(({ industry_code, industry_name }) => ({
      id: industry_code,
      name: industry_name,
    }));
  }, [passedIndustryClassDetailOptions, buildingDataset]);

  const cityGasOptions = useMemo(() => {
    if (passedCityGasOptions) return passedCityGasOptions;
    if (!buildingDataset?.city_gas) return [];
    return buildingDataset.city_gas.map(({ city_gas_supplier_cd, city_gas_supplier_nm }) => ({
      id: city_gas_supplier_cd,
      name: city_gas_supplier_nm,
    }));
  }, [passedCityGasOptions, buildingDataset]);

  const heatSupplyOptions = useMemo(() => {
    if (passedHeatSupplyOptions) return passedHeatSupplyOptions;
    if (!buildingDataset?.heat_supplier) return [];
    return buildingDataset.heat_supplier.map(({ heat_supplier_cd, heat_supplier_name }) => ({
      id: heat_supplier_cd,
      name: heat_supplier_name,
    }));
  }, [passedHeatSupplyOptions, buildingDataset]);

  const [showConfirm, setShowConfirm] = useState(false);

  const handleClickDelete = () => {
    // モーダルを表示（実行はモーダルで確認してから）
    setShowConfirm(true);
  };

  const handleConfirm = () => {
    const allBuildingIds = buildingDataset.buildings.map((building) => building.building_id);

    if (allBuildingIds.length === 0) {
      console.warn("削除対象の建物が存在しません");
      return;
    }

    onDeleteBuildingData(allBuildingIds);
    setShowConfirm(false); // モーダル閉じる
  };

  return (
    <div className="flex flex-col min-h-max">
      <div className="flex-1 min-h-0 overflow-auto w-full mt-[0px] mb-[30px]">
        <div className="flex flex-col space-y-1 w-full">
          <div ref={scrollTargetRef} />
          {!isConfirmation &&
            (isEditing ? (
              <div className="flex justify-end flex-shrink-0"></div>
            ) : (
              orgId === createOrgId &&
              loginOrgId === createOrgId && (
                <div className="flex gap-2 justify-end py-3 flex-shrink-0">
                  <Button variant="lineerror" onClick={handleClickDelete}>
                    データを削除
                  </Button>
                  <AlertModal
                    isOpen={showConfirm}
                    onClose={() => setShowConfirm(false)}
                    onConfirm={handleConfirm}
                    loading={false}
                    title="削除の確認"
                    description="拠点・エネルギー情報を削除します。よろしいですか？"
                    cancelText="いいえ"
                    continueText="はい"
                  />
                  <Button
                    variant="primary"
                    size="default"
                    onClick={() => {
                      if (setIsEditing) setIsEditing(true);
                    }}
                    // iconLeft={<Icon name="edit" />}
                  >
                    内容を編集
                  </Button>
                </div>
              )
            ))}
          {errorMessage && (
            <div className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden mt-5 mb-5 flex-shrink-0">
              <div className="flex flex-row items-center bg-red-500 px-4 py-2 gap-1">
                <Icon name="error-pink" />
                <Text content="エラーがあります" color="white" weight="bold" />
              </div>
              <div className="flex flex-col items-start bg-[#fee4e2] border border-[#d92d20] px-4 py-6 rounded-b text-[#d92d20] cursor-pointer gap-[25px]">
                {Array.isArray(errorMessage) ? (
                  <ul>
                    {errorMessage.map((message, index) => (
                      <li key={index}>{message}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-[#d92d20] text-[14px] font-normal leading-[21px] text-left whitespace-nowrap ">
                    {errorMessage}
                  </div>
                )}
              </div>
            </div>
          )}
          {buildingDataset.buildings.map((building) => (
            <BuildingEnergyForm
              key={`${building.building_id}_${isConfirmation ? "confirm" : "edit"}`}
              ref={getFormRef(building.building_id)}
              building={building}
              prefectureOptions={prefectureOptions}
              industryClassMinorOptions={industryClassMinorOptions}
              industryClassDetailOptions={industryClassDetailOptions}
              cityGasOptions={cityGasOptions}
              heatSupplyOptions={heatSupplyOptions}
              isEditing={isEditing}
              editedData={editedData}
              setEditedData={setEditedData}
              corporateData={corporateData}
              agreementCategory={agreementCategory}
              startYearMonth={startYearMonth}
              endYearMonth={endYearMonth}
              buildingFormRefs={buildingFormRefs}
              userId={userId}
              orgId={orgId}
              token={token ?? ""}
              onError={(msg) => setErrorMessage(msg)}
              setIsFormDirty={setIsFormDirty}
              scrollRefMap={scrollRefMap}
              isConfirmation={isConfirmation}
              setIsConfirmation={setIsConfirmation}
              confirmedValues={confirmedValues}
              isGoingToConfirmation={isGoingToConfirmation}
              setIsGoingToConfirmation={setIsGoingToConfirmation}
              pendingConfirmData={pendingConfirmData}
              setPendingConfirmData={setPendingConfirmData}
              triggerConfirm={triggerConfirm}
              setTriggerConfirm={setTriggerConfirm}
              onSetResetFunc={onSetResetFunc}
              resetTrigger={resetTrigger}
              validationMode={validationMode}
              forwardTriggerRef={forwardTriggerRef}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default BaseEnergyData;
