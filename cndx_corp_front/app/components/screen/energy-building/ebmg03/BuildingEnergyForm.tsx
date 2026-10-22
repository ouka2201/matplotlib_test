import { zodResolver } from "@hookform/resolvers/zod";
import { clsx } from "clsx";
import { addMonths, format, parse } from "date-fns";
import React, { forwardRef, useEffect, useImperativeHandle, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { FormProvider, useFieldArray, useForm, useWatch } from "react-hook-form";
import MasterFormField from "~/components/common/master-form-field";
import { energyOptions } from "~/components/screen/energy-building/ebmg03/energyOptions";
import { Button } from "~/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Dialog, DialogContent, DialogTrigger } from "~/components/ui/dialog";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "~/components/ui/form";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Messages } from "~/constants/messages/message";
import { postData } from "~/lib/fetch";
import { makeBuildingSchema } from "~/lib/validations/ebmg";
import {
  Building,
  BuildingInfo,
  BuildingInfoFormValues,
  BuildingInfoWithMenu,
  ElectricCompanyList,
  ElectricityDataItem,
  EnergyInfo,
} from "~/types/screen/energy-building/ebmg/ebmgType";
import { CustomerCompany } from "~/types/screen/master/mscs/mscsType";
import Icon from "../../../icon";
import SupplierSearchModal from "../ebmg03/SupplierSearchModal";
type Option = {
  id: string;
  name: string;
};

type Props = {
  building: Building;
  prefectureOptions: Option[];
  industryClassMinorOptions: Option[];
  industryClassDetailOptions: Option[];
  isEditing: boolean;
  editedData: Record<number, Partial<BuildingInfo>>;
  setEditedData: React.Dispatch<React.SetStateAction<Record<number, Partial<BuildingInfo>>>>;
  corporateData: CustomerCompany | null;
  agreementCategory: string;
  startYearMonth: string;
  endYearMonth: string;
  buildingFormRefs: React.MutableRefObject<Record<string, UseFormReturn<BuildingInfo>>>;
  userId: string;
  orgId: string;
  token: string | null;
  onError?: (message: string | string[]) => void;
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
  forwardTriggerRef: React.MutableRefObject<{
    [buildingId: string]: {
      trigger: () => Promise<boolean>;
      getValues: () => BuildingInfoFormValues;
    };
  }>;
  validationMode: "nonRequired" | "full";
};

function isErrorWithStatus(error: unknown): error is { status: number; error_message_list?: string } {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    typeof (error as { status: number }).status === "number"
  );
}

export type BuildingEnergyFormHandle = {
  getValues: () => any;
};

const get12MonthLabels = (startMonth: string): string[] => {
  const startDate = parse(startMonth, "yyyyMM", new Date());
  if (isNaN(startDate.getTime())) {
    console.error("Invalid targetYearMonth:", startMonth);
    return [];
  }
  return Array.from({ length: 12 }, (_, i) => format(addMonths(startDate, i), "yyyy/M"));
};

const BuildingEnergyForm = forwardRef<BuildingEnergyFormHandle, Props>(
  (
    {
      building,
      prefectureOptions,
      industryClassMinorOptions,
      industryClassDetailOptions,
      isEditing = false,
      startYearMonth,
      endYearMonth,
      setEditedData,
      buildingFormRefs,
      agreementCategory,
      corporateData,
      token,
      onError,
      setIsFormDirty,
      scrollRefMap,
      isConfirmation,
      confirmedValues,
      setIsConfirmation,
      isGoingToConfirmation,
      setIsGoingToConfirmation,
      pendingConfirmData,
      validationMode,
      triggerConfirm,
      setTriggerConfirm,
      onSetResetFunc,
      resetTrigger,
      forwardTriggerRef,
    },
    ref,
  ) => {
    const info = building.building_info;

    const createEmptyEnergyInfo = (code: string): EnergyInfo => {
      const option = energyOptions.find((e) => e.energy_code === code);

      return {
        energy_code: code,
        energy_unit_original: option?.energy_unit_original?.[0] ?? "",
        energy_name_jp: option?.energy_name_jp ?? "",
        energy_quantity: Array(12).fill(""),
        energy_usage_sum: 0,
      };
    };

    // energy_info[] の各項目を energyOptions に基づき補完（name/unit）
    const enrichEnergyInfo = (ei: EnergyInfo[]): EnergyInfo[] => {
      return ei.map((item) => {
        const option = energyOptions.find((e) => String(e.energy_code) === String(item.energy_code));

        return {
          ...item,
          energy_name_jp: item.energy_name_jp || option?.energy_name_jp || "",
          energy_unit_original: item.energy_unit_original || option?.energy_unit_original?.[0] || "",
        };
      });
    };

    // フォームの初期値を生成
    const getDefaultValues = () => {
      const ei = info.energy_info;
      const cityGasRegNo = info.city_gas_supplier_no ?? "";
      const heatSupplyRegNo = info.heat_supplier_no ?? "";

      const enrichedEnergyInfo = ei && ei.length > 0 ? enrichEnergyInfo(ei) : [createEmptyEnergyInfo("0200010011")];

      return {
        building_name: info.building_name ?? "",
        building_address_prefecture: info.building_address_prefecture ?? "",
        building_address_city: info.building_address_city ?? "",
        industry_class_major_code: info.industry_class_major_code ?? "",
        industry_class_middle_code: info.industry_class_middle_code ?? "",
        industry_class_minor_code: info.industry_class_minor_code ?? "",
        industry_class_detail_code: info.industry_class_detail_code ?? "",
        gross_floor_area: info.gross_floor_area ?? "",
        electricity_supplier_no: info.electricity_supplier_no ?? "",
        menu_name: info.menu_name ?? "",
        menu_no: info.menu_no ?? "",
        ep_office_code: info.ep_office_code ?? "",
        ep_customer_number: info.ep_customer_number ?? "",
        supply_point_number: info.supply_point_number ?? "",
        city_gas_supplier_no: cityGasRegNo,
        heat_supplier_no: heatSupplyRegNo,
        energy_info: enrichedEnergyInfo,
      };
    };

    const defaultValuesRef = useRef(getDefaultValues());

    const form = useForm<BuildingInfoFormValues>({
      resolver: zodResolver(makeBuildingSchema(validationMode)),
      defaultValues: defaultValuesRef.current,
    });

    const [formValuesBeforeReset, setFormValuesBeforeReset] = React.useState<BuildingInfoFormValues | null>(null);
    const watchedValues = useWatch({ control: form.control });

    useEffect(() => {
      if (watchedValues && Object.keys(watchedValues).length > 0) {
        setFormValuesBeforeReset((prev) => {
          if (JSON.stringify(prev) === JSON.stringify(watchedValues)) {
            return prev;
          }
          return watchedValues as BuildingInfoFormValues;
        });
      }
    }, [watchedValues]);

    useEffect(() => {
      if (triggerConfirm && pendingConfirmData) {
        form.reset(pendingConfirmData);
        // フラグはリセット
        setTriggerConfirm(false);
      }
    }, [triggerConfirm, pendingConfirmData]);

    const industryClassMiddleCode = form.getValues("industry_class_middle_code");
    const industryClassMinorCode = form.watch("industry_class_minor_code");
    const filteredIndustryClassMinorOptions = useMemo(() => {
      return industryClassMinorOptions.filter((opt) => opt.id.startsWith(industryClassMiddleCode || ""));
    }, [industryClassMinorOptions, industryClassMiddleCode]);

    const filteredIndustryClassDetailOptions = industryClassDetailOptions.filter((opt) =>
      opt.id.startsWith(industryClassMinorCode || ""),
    );

    useEffect(() => {
      setEditedData((prev) => ({
        ...prev,
        [building.building_id]: watchedValues,
      }));
    }, [watchedValues, building.building_id, setEditedData]);

    useEffect(() => {
      if (isGoingToConfirmation) {
        return;
      }
      if (isEditing) {
        form.reset({
          ...form.getValues(),
          electricity_supplier_name: selectedElectricCompanyName, // または name を保持した state
        });
      }
    }, [building, isEditing, isConfirmation]);

    //TODO 型エラー解決
    useLayoutEffect(() => {
      if (!building.building_id || !buildingFormRefs.current) return;

      buildingFormRefs.current[building.building_id] = form;

      if (forwardTriggerRef) {
        forwardTriggerRef.current[building.building_id] = {
          trigger: form.trigger,
          getValues: form.getValues,
        };
      }
    }, [building.building_id, form]);

    useImperativeHandle(ref, () => ({
      getValues: () => {
        const values = form.getValues();
        const enrichedEnergyInfo =
          values.energy_info && values.energy_info.length > 0 ? enrichEnergyInfo(values.energy_info) : [];
        const enrichedValues = {
          ...values,
          energy_info: enrichedEnergyInfo,
        };
        return enrichedValues;
      },
    }));

    const { fields, append, move, replace } = useFieldArray({
      control: form.control,
      name: "energy_info",
      keyName: "fieldId",
    });

    const watchedEnergyInfo =
      (useWatch({
        control: form.control,
        name: "energy_info",
      }) as EnergyInfo[] | undefined) ?? [];

    const usedEnergyCodes = watchedEnergyInfo.map((e) => e.energy_code);
    const availableEnergyOptions = energyOptions.filter((e) => !usedEnergyCodes.includes(e.energy_code));

    const handleAddEnergy = () => {
      if (availableEnergyOptions.length === 0) {
        alert("追加できるエネルギーはありません。");
        return;
      }

      // 新規行を追加
      append({
        energy_code: "",
        energy_unit_original: "",
        energy_name_jp: "",
        energy_quantity: Array(12).fill(""),
        energy_usage_sum: 0,
      });

      // append 後に RHF 内の配列を取得して電気を先頭にする
      setTimeout(() => {
        const current = form.getValues("energy_info") ?? [];

        const nonEmpty = current.filter((e) => e.energy_code !== "");
        const emptyRows = current.filter((e) => e.energy_code === "");

        // 電気を先頭に
        nonEmpty.sort((a, b) => (a.energy_code === "0200010011" ? -1 : b.energy_code === "0200010011" ? 1 : 0));

        const sorted = [...nonEmpty, ...emptyRows];

        form.setValue("energy_info", sorted, { shouldDirty: true, shouldTouch: true });
      }, 0);
    };

    useEffect(() => {
      if (!isEditing) return;
      const energyInfo = form.getValues("energy_info");
      const hasElectricity = energyInfo.some((e) => e.energy_code === "0200010011");
      if (hasElectricity) {
        const sorted = [
          ...energyInfo.filter((e) => e.energy_code === "0200010011"),
          ...energyInfo.filter((e) => e.energy_code !== "0200010011"),
        ];
        form.setValue("energy_info", sorted, { shouldDirty: false, shouldTouch: false });
      }
    }, [isEditing]);

    const monthLabels = get12MonthLabels(startYearMonth);

    const isInitializedRef = useRef(false);

    useEffect(() => {
      if (!building.building_info || energyOptions.length === 0) return;
      if (isGoingToConfirmation) return;

      const baseValues =
        isEditing && !isConfirmation
          ? pendingConfirmData?.[building.building_id] ?? getDefaultValues()
          : getDefaultValues();

      let energyInfo = baseValues.energy_info ?? [];

      if (energyInfo.length === 0) {
        const electricOption = energyOptions.find((e) => e.energy_code === "0200010011");

        energyInfo = [
          {
            energy_code: "0200010011",
            energy_unit_original: electricOption?.energy_unit_original?.[0] ?? "",
            energy_name_jp: electricOption?.energy_name_jp ?? "",
            energy_quantity: Array(12).fill(""),
            energy_usage_sum: 0,
          },
        ];
      }

      const electricIndex = energyInfo.findIndex((f) => f.energy_code === "0200010011");

      if (electricIndex > 0) {
        const [electric] = energyInfo.splice(electricIndex, 1);
        energyInfo.unshift(electric);
      }

      const enrichedEnergyInfo = enrichEnergyInfo(energyInfo);

      form.reset({
        ...baseValues,
        energy_info: enrichedEnergyInfo,
      });

      replace(enrichedEnergyInfo);
    }, [building, energyOptions, isEditing, isConfirmation, pendingConfirmData]);

    useEffect(() => {
      if (energyOptions.length === 0) return;
      if (fields.length === 0) return;

      fields.forEach((_, index) => {
        const unit = form.getValues(`energy_info.${index}.energy_unit_original`);
        if (!unit) {
          const code = form.getValues(`energy_info.${index}.energy_code`);
          const opt = energyOptions.find((e) => e.energy_code === code);
          const defaultUnit = opt?.energy_unit_original?.[0];

          if (defaultUnit) {
            form.setValue(`energy_info.${index}.energy_unit_original`, defaultUnit, { shouldDirty: false });
          }
        }
      });
    }, [fields, energyOptions]);

    useEffect(() => {
      const electricityIndex = fields.findIndex((f) => f.energy_code === "0200010011");
      if (electricityIndex > 0) {
        move(electricityIndex, 0);
      }
    }, [fields.length, move]);

    const displayFields = fields.slice().sort((a, b) => {
      if (a.energy_code === "0200010011") return -1;
      if (b.energy_code === "0200010011") return 1;
      return 0;
    });

    const [selectedElectricCompanyName, setSelectedElectricCompanyName] = useState<string | null>(null);
    const supplierInputClass =
      "flex items-center gap-2 rounded shadow-[0px_1px_2px_rgba(16,24,40,0.05)] px-3 py-2 min-h-[30px] min-w-[280px]";
    const [menuOptions, setMenuOptions] = useState<Option[]>([]);
    const [open, setOpen] = useState(false);

    const [selectedCityGasSupplierName, setSelectedCityGasSupplierName] = useState<string | null>(null);
    const [cityGasModalOpen, setCityGasModalOpen] = useState(false);

    const [selectedHeatSupplierName, setSelectedHeatSupplierName] = useState<string | null>(null);
    const [heatSupplierModalOpen, setHeatSupplierModalOpen] = useState(false);

    // 電力会社が選ばれたときの処理
    const handleSelectElectricCompany = ({
      id,
      name,
      selectMenu,
    }: {
      id: string;
      name: string;
      selectMenu: { menu_no: string; menu_nm: string }[];
    }) => {
      form.setValue("electricity_supplier_no", id);
      form.setValue("electricity_supplier_name", name);
      form.trigger("electricity_supplier_no");
      setSelectedElectricCompanyName(name);
      setMenuOptions(
        selectMenu.map((m) => ({
          id: String(m.menu_no),
          name: m.menu_nm,
        })),
      );

      form.setValue("menu_no", undefined);
      form.trigger("menu_no");
      setOpen(false);
    };

    // 都市ガス供給事業者が選ばれたときの処理
    const handleSelectCityGasSupplier = ({ id, name }: { id: string; name: string }) => {
      form.setValue("city_gas_supplier_no", id);
      form.setValue("city_gas_supplier_name", name);
      form.trigger("city_gas_supplier_no");
      setSelectedCityGasSupplierName(name);
      setCityGasModalOpen(false);
    };

    // 熱供給事業者が選ばれたときの処理
    const handleSelectHeatSupplier = ({ id, name }: { id: string; name: string }) => {
      form.setValue("heat_supplier_no", id);
      form.setValue("heat_supplier_name", name);
      form.trigger("heat_supplier_no");
      setSelectedHeatSupplierName(name);
      setHeatSupplierModalOpen(false);
    };

    const castedInfo = info as BuildingInfoWithMenu;
    useEffect(() => {
      setSelectedElectricCompanyName(info.electricity_supplier_no ? info.electricity_supplier_name ?? null : null);

      setMenuOptions(
        (castedInfo.select_menu ?? []).map((m) => ({
          id: String(m.menu_no),
          name: m.menu_nm,
        })),
      );

      setSelectedCityGasSupplierName(info.city_gas_supplier_no ? info.city_gas_supplier_name ?? null : null);
      setSelectedHeatSupplierName(info.heat_supplier_no ? info.heat_supplier_name ?? null : null);
    }, [info, castedInfo.select_menu]);

    //電気事業者のセット

    const fetchElectricCompanyInfo = async (supplierName: string) => {
      if (!supplierName) return;

      const targetYear = startYearMonth.slice(0, 4);
      const requestUrl = "/api/building/energy-info/search/electricCo";
      const requestParams = {
        company_name: supplierName,
        target_year: targetYear,
      };

      try {
        const response: ElectricCompanyList[] = await postData(requestUrl, requestParams);

        const matched = response.find(
          (item) => item.electric_co_name.trim().toLowerCase() === supplierName.trim().toLowerCase(),
        );

        if (matched) {
          // メニュー一覧を deduplicate & オプションとしてセット
          const deduplicatedMenus = Array.from(new Map(matched.select_menu.map((m) => [m.menu_nm, m])).values()).map(
            (m) => ({
              id: String(m.menu_no),
              name: m.menu_nm,
            }),
          );

          setMenuOptions(deduplicatedMenus);

          // バックエンドの menu_name を優先して menu_no を取得
          const menuIdFromInfo =
            matched.select_menu.find((m) => m.menu_nm === info.menu_name)?.menu_no || matched.select_menu[0]?.menu_no;

          // フォームに電力会社・メニュー情報をセット
          const selectedMenu = matched.select_menu.find((m) => m.menu_no === menuIdFromInfo) || matched.select_menu[0];

          if (selectedMenu) {
            // フォームに値をセット
            form.setValue("electricity_supplier_no", matched.electric_company_reg_no);
            form.setValue("electricity_supplier_name", matched.electric_co_name);
            form.setValue("menu_no", String(selectedMenu.menu_no));
            form.setValue("menu_name", selectedMenu.menu_nm);

            // フォーム反映を即時
            form.trigger(["electricity_supplier_no", "menu_no", "menu_name"]);
          } else {
            console.warn("[fetchElectricCompanyInfo] No selectedMenu found");
          }
        } else {
          console.warn("[fetchElectricCompanyInfo] No matching company found in API response");
        }
      } catch (error: unknown) {
        console.error("契約先電気事業者の初期取得失敗:", error);

        if (isErrorWithStatus(error)) {
          switch (error.status) {
            case 400:
              onError?.(error.error_message_list || "契約先電気事業者の取得に失敗しました");
              break;
            case 500:
              onError?.("システムエラーが発生しました。システム管理者にご連絡ください。");
              break;
            default:
              onError?.(`契約先電気事業者取得エラー: ステータスコード ${error.status}`);
              break;
          }
        } else {
          onError?.("契約先電気事業者の取得に失敗しました。システム担当者に連絡してください。");
        }
      }
    };

    useEffect(() => {
      const supplierName = form.getValues("electricity_supplier_name") || info.electricity_supplier_name;

      fetchElectricCompanyInfo(supplierName);
    }, [info.electricity_supplier_name, building.building_id, isEditing]);

    const get12MonthYearMonths = (startMonth: string): string[] => {
      const startDate = parse(startMonth, "yyyyMM", new Date());
      if (isNaN(startDate.getTime())) {
        console.error("Invalid targetYearMonth:", startMonth);
        return [];
      }
      return Array.from({ length: 12 }, (_, i) => format(addMonths(startDate, i), "yyyyMM"));
    };

    const handleAutoFillElectricity = async (index: number) => {
      const values = form.getValues();

      const requestParams = {
        corporate_number: corporateData?.corporate_number ?? "",
        agreement_category: agreementCategory,
        start_year_month: startYearMonth,
        end_year_month: endYearMonth,
        ep_customer_number: values.ep_customer_number,
        supply_point_number: values.supply_point_number,
      };

      const requestUrl = "/api/building/energy-info/auto";

      try {
        const response = await postData(requestUrl, requestParams, {
          Authorization: `Bearer ${token}`,
        });

        if (!response?.result?.electricity_data) {
          console.error("不正なレスポンス形式:", response);
          onError?.("電力データの取得に失敗しました（レスポンス不正）");
          return;
        }

        const { electricity_data, unit } = response.result;

        const yearMonths = get12MonthYearMonths(startYearMonth);
        const quantities = yearMonths.map((ym) => {
          const found = electricity_data.find((item: ElectricityDataItem) => item.year_month === ym);
          return found ? found.sum : 0;
        });

        form.setValue(`energy_info.${index}.energy_unit_original`, unit);

        quantities.forEach((value, monthIndex) => {
          form.setValue(`energy_info.${index}.energy_quantity.${monthIndex}`, value);
        });

        form.trigger(`energy_info.${index}`);
      } catch (error: unknown) {
        console.error("自動入力API呼び出しエラー:", error);

        if (isErrorWithStatus(error)) {
          switch (error.status) {
            case 400:
              onError?.(error.error_message_list || "契約情報の自動入力に失敗しました");
              break;
            case 500:
              onError?.("システムエラーが発生しました。システム管理者にご連絡ください。");
              break;
            default:
              onError?.(`契約情報自動入力エラー: ステータスコード ${error.status}`);
              break;
          }
        } else {
          onError?.("契約情報の自動入力に失敗しました。システム担当者に連絡してください。");
        }
      }
    };

    const basicInfoRef = useRef<HTMLDivElement>(null);
    const electricRef = useRef<HTMLDivElement>(null);
    const gasRef = useRef<HTMLDivElement>(null);
    const heatRef = useRef<HTMLDivElement>(null);
    const energyRef = useRef<HTMLDivElement>(null);

    //入力内容の検知
    useEffect(() => {
      const subscription = form.watch((value, { name }) => {
        if (form.formState.isDirty) {
          setIsFormDirty?.(true);
        }

        if (name === "menu_no") {
          const selectedMenu = menuOptions.find((opt) => opt.id === value.menu_no);
          form.setValue("menu_name", selectedMenu?.name || "");
        }
      });

      return () => subscription.unsubscribe();
    }, [form, setIsFormDirty, menuOptions]);

    useEffect(() => {
      if (!isEditing) return;

      const supplierName = form.getValues("electricity_supplier_name") || info.electricity_supplier_name;
      if (!supplierName) return;
      if (menuOptions.length === 0) return;

      // まだ menu_no がセットされていない場合、初期値をセット
      const currentMenuNo = form.getValues("menu_no");
      if (!currentMenuNo) {
        const firstMenu = menuOptions[0];
        if (firstMenu) {
          form.setValue("menu_no", firstMenu.id);
          form.setValue("menu_name", firstMenu.name);
          form.trigger(["menu_no", "menu_name"]);
        }
      }
    }, [menuOptions, isEditing, form, info.electricity_supplier_name]);

    useEffect(() => {
      if (menuOptions.length === 0) return;

      // メニューを選定: info から優先、なければ先頭
      const selectedMenu = menuOptions.find((m) => m.name === info.menu_name) || menuOptions[0];

      if (selectedMenu) {
        // フォーム値をセット
        form.setValue("menu_no", selectedMenu.id, { shouldDirty: true, shouldTouch: true });
        form.setValue("menu_name", selectedMenu.name);
        form.trigger(["menu_no", "menu_name"]);
      }
    }, [menuOptions, info.menu_name, form]);

    //契約先電気料金メニューの非活性判定処理
    const isMenuEnabled = useMemo(() => {
      if (!isEditing) return false;

      const menuAvailable = menuOptions.length > 0;
      const companySelected = !!(selectedElectricCompanyName || form.getValues("electricity_supplier_name"));

      return companySelected && menuAvailable;
    }, [menuOptions, selectedElectricCompanyName, form, isEditing]);

    const id = building.building_id;

    scrollRefMap.current[`拠点基本情報-${id}`] = basicInfoRef;
    scrollRefMap.current[`電気-${id}`] = electricRef;
    scrollRefMap.current[`都市ガス-${id}`] = gasRef;
    scrollRefMap.current[`熱-${id}`] = heatRef;
    scrollRefMap.current[`エネルギー使用量-${id}`] = energyRef;

    useEffect(() => {
      if (onSetResetFunc && building.building_id) {
        onSetResetFunc(building.building_id, (values: any | null) => {
          if (values) {
            form.reset(values);
          } else {
            form.reset(getDefaultValues());
          }
        });
      }
    }, [resetTrigger]);

    useEffect(() => {
      const supplierName = form.getValues("electricity_supplier_name") || info.electricity_supplier_name;

      if ((isEditing || isConfirmation) && supplierName) {
        fetchElectricCompanyInfo(supplierName);
      }
    }, [isEditing, isConfirmation, info.electricity_supplier_name]);

    return (
      <FormProvider {...form}>
        <form
          className="flex w-full flex-col items-start gap-8 rounded-lg border border-[#F2F4F7] bg-white shadow-[0px_2px_4px_-2px_rgba(16,24,40,0.06),0px_4px_8px_-2px_rgba(16,24,40,0.10)] px-6 py-8 mb-6"
          onSubmit={form.handleSubmit((values) => {
            console.log("保存された値:", building.building_id, values);
          })}
        >
          <CardHeader>
            <CardTitle>{info.building_name}</CardTitle>
          </CardHeader>

          <div className="ml-6 text-[#667085] font-bold text-base leading-6 font-sans" ref={basicInfoRef}>
            拠点基本情報
          </div>
          <CardContent className="flex flex-col ">
            <MasterFormField
              control={form.control}
              name="building_name"
              label="拠点名"
              renderCustom={() => <span>{info.building_name}</span>}
              renderUnChange={() => <span>{info.building_name}</span>}
              isEditing={isEditing}
            />
            <MasterFormField
              control={form.control}
              name="building_address_prefecture"
              label="拠点所在地"
              renderCustom={() => {
                const prefectureName =
                  prefectureOptions.find((p) => p.id === info.building_address_prefecture)?.name || "";
                return (
                  <span>
                    {prefectureName}
                    {info.building_address_city}
                  </span>
                );
              }}
              renderUnChange={() => {
                const prefectureName =
                  prefectureOptions.find((p) => p.id === info.building_address_prefecture)?.name || "";
                return (
                  <span>
                    {prefectureName}
                    {info.building_address_city}
                  </span>
                );
              }}
              isEditing={isEditing}
            />
            <MasterFormField
              control={form.control}
              name="industry_class_major_code"
              label="産業分類(大分類)"
              renderCustom={() => <span>{info.industry_class_major_name}</span>}
              renderUnChange={() => <span>{info.industry_class_major_name}</span>}
              isEditing={isEditing}
            />
            <MasterFormField
              control={form.control}
              name="industry_class_middle_code"
              label="産業分類(中分類)"
              renderCustom={() => <span>{info.industry_class_middle_name}</span>}
              renderUnChange={() => <span>{info.industry_class_middle_name}</span>}
              isEditing={isEditing}
            />
            <MasterFormField
              control={form.control}
              name="industry_class_minor_code"
              label="産業分類（小分類）"
              required
              triggerValidation={(name) => form.trigger(name)}
              options={filteredIndustryClassMinorOptions}
              isEditing={isEditing}
              isConfirmation={isConfirmation}
              type="select"
              renderUnChange={() => <span>{info.industry_class_minor_name}</span>}
              renderConfirmChange={() => {
                const buildingId = building.building_id; // buildingIdを適切に取得できるようにpropsで渡す
                const buildingData = pendingConfirmData ? pendingConfirmData[buildingId] : undefined;
                const selectedCode = buildingData?.industry_class_minor_code;
                const selectedOption = filteredIndustryClassMinorOptions.find(
                  (opt) => opt.id === String(selectedCode ?? "").trim(),
                );

                return <span>{selectedOption?.name ?? info.industry_class_minor_name ?? ""}</span>;
              }}
            />
            <MasterFormField
              control={form.control}
              name="industry_class_detail_code"
              label="産業分類（細分類）"
              required
              triggerValidation={(name) => form.trigger(name)}
              options={filteredIndustryClassDetailOptions}
              isEditing={isEditing}
              isConfirmation={isConfirmation}
              type="select"
              disabled={!form.getValues("industry_class_minor_code") || filteredIndustryClassDetailOptions.length === 0}
              renderUnChange={() => <span>{info.industry_class_detail_name}</span>}
              renderConfirmChange={() => {
                const buildingId = building.building_id;
                const buildingData = pendingConfirmData ? pendingConfirmData[buildingId] : undefined;
                const selectedCode = buildingData?.industry_class_detail_code;
                const selectedOption = filteredIndustryClassDetailOptions.find((opt) => opt.id === selectedCode);
                return <span>{selectedOption?.name ?? info.industry_class_detail_name ?? ""}</span>;
              }}
            />
            <MasterFormField
              control={form.control}
              name="gross_floor_area"
              label="延床面積"
              required
              triggerValidation={(name) => form.trigger(name)}
              isEditing={isEditing}
              isConfirmation={isConfirmation}
              unit="m2"
              renderCustom={(field) => {
                const hasError = !!form.formState.errors["gross_floor_area"];
                return (
                  <Input
                    {...field}
                    type="text"
                    inputMode="numeric"
                    className={clsx("w-full", hasError && "input-text-error")}
                    onChange={(e) => {
                      const rawValue = e.target.value;
                      const sanitizedValue = rawValue.replace(/[^0-9.]/g, "");
                      field.onChange(sanitizedValue);
                    }}
                    onBlur={() => {
                      field.onBlur();
                      form.trigger("gross_floor_area");
                    }}
                  />
                );
              }}
              renderUnChange={() => <span>{info.gross_floor_area} m2</span>}
              renderConfirmChange={() => {
                const buildingId = building.building_id;
                const buildingData = pendingConfirmData ? pendingConfirmData[buildingId] : undefined;
                const value = buildingData?.gross_floor_area ?? info.gross_floor_area;
                return <span>{value} m2</span>;
              }}
            />
          </CardContent>

          <div className="h-px w-full bg-[#D0D5DD]" />

          <CardContent className="flex flex-col ">
            <div className="pb-6 text-[#667085] font-bold text-base leading-6 font-sans " ref={electricRef}>
              電気
            </div>
            <MasterFormField
              control={form.control}
              name="electricity_supplier_no"
              label="契約先電気事業者"
              required
              isEditing={isEditing}
              isConfirmation={isConfirmation}
              renderCustom={(field) => {
                //const val = form.getValues("electricity_supplier_no");
                const displayName = form.getValues("electricity_supplier_name") || info.electricity_supplier_name;
                const hasError = !!form.formState.errors["electricity_supplier_no"];

                return isEditing ? (
                  <div
                    className="flex items-center gap-2 w-full"
                    tabIndex={-1}
                    onBlur={() => {
                      field.onBlur();
                      form.trigger("electricity_supplier_no");
                    }}
                  >
                    <div
                      className={clsx(supplierInputClass, hasError ? "input-text-error" : "border border-[#98A2B3]")}
                    >
                      <span>{displayName}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setOpen(true)}
                      className="border w-20 h-10 rounded flex items-center justify-center whitespace-nowrap
             text-teal-600 border-teal-600 cursor-pointer"
                    >
                      選択
                    </button>
                  </div>
                ) : (
                  <div className={clsx(supplierInputClass, hasError ? "input-text-error" : "border border-[#98A2B3]")}>
                    <span>{displayName}</span>
                  </div>
                );
              }}
              renderConfirmChange={() => {
                const buildingId = building.building_id;
                const confirmDataName = pendingConfirmData?.[buildingId]?.electricity_supplier_name;
                const initialName = info.electricity_supplier_name;
                const editedName = form.getValues("electricity_supplier_name");
                const displayName = confirmDataName ?? editedName ?? initialName ?? "";
                return <span>{displayName}</span>;
              }}
              renderUnChange={() => <span>{info.electricity_supplier_name}</span>}
            />
            <MasterFormField
              control={form.control}
              name="menu_no"
              label="契約先電気料金メニュー"
              options={menuOptions}
              type="select"
              isEditing={isEditing}
              isConfirmation={isConfirmation}
              disabled={!isMenuEnabled}
              renderConfirmChange={() => {
                const buildingId = building.building_id;
                const buildingData = pendingConfirmData ? pendingConfirmData[buildingId] : undefined;

                const name = buildingData?.menu_name;
                return <span>{name ?? ""}</span>;
              }}
              renderUnChange={() => {
                const menuNo = info.menu_no || info.menu_name || "";
                const selectedMenu = menuOptions.find((opt) => opt.id === String(menuNo)) || menuOptions[0];
                return <span>{selectedMenu?.name ?? ""}</span>;
              }}
            />
            <MasterFormField
              control={form.control}
              name="ep_office_code"
              label="事業所コード"
              renderCustom={() => <span>{info.ep_office_code}</span>}
              isEditing={isEditing}
              renderUnChange={() => <span>{info.ep_office_code}</span>}
            />
            <MasterFormField
              control={form.control}
              name="ep_customer_number"
              label="お客さま番号"
              renderCustom={() => <span>{info.ep_customer_number}</span>}
              renderUnChange={() => <span>{info.ep_customer_number}</span>}
              isEditing={isEditing}
            />
            <MasterFormField
              control={form.control}
              name="supply_point_number"
              label="供給地点特定番号"
              renderCustom={() => <span>{info.supply_point_number}</span>}
              renderUnChange={() => <span>{info.supply_point_number}</span>}
              isEditing={isEditing}
            />
          </CardContent>

          <div className="h-px w-full bg-[#D0D5DD]" />

          <CardContent className="flex flex-col ">
            <div className="pb-6 text-[#667085] font-bold text-base leading-6 font-sans " ref={gasRef}>
              都市ガス
            </div>
            <MasterFormField
              control={form.control}
              name="city_gas_supplier_no"
              label="契約先都市ガス供給事業者"
              isEditing={isEditing}
              isConfirmation={isConfirmation}
              renderCustom={({ hasError }) => {
                const editedName = form.getValues("city_gas_supplier_name");
                const initialName = info.city_gas_supplier_name;
                const displayName = selectedCityGasSupplierName ?? editedName ?? initialName ?? "";

                return isEditing ? (
                  <div
                    className="flex items-center gap-2 w-full"
                    tabIndex={-1}
                    onBlur={() => {
                      form.trigger("city_gas_supplier_no");
                    }}
                  >
                    <div
                      className={clsx(supplierInputClass, hasError ? "input-text-error" : "border border-[#98A2B3]")}
                    >
                      <span>{displayName}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setCityGasModalOpen(true)}
                      className="border w-20 h-10 rounded flex items-center justify-center whitespace-nowrap
             text-teal-600 border-teal-600 cursor-pointer"
                    >
                      選択
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 w-full">
                    <div
                      className={clsx(supplierInputClass, hasError ? "input-text-error" : "border border-[#98A2B3]")}
                    >
                      <span>{displayName}</span>
                    </div>
                  </div>
                );
              }}
              renderConfirmChange={() => {
                const buildingId = building.building_id;
                const confirmDataName = pendingConfirmData?.[buildingId]?.city_gas_supplier_name;
                const initialName = info.city_gas_supplier_name;
                const editedName = form.getValues("city_gas_supplier_name");
                const displayName = confirmDataName ?? editedName ?? initialName ?? "";
                return <span>{displayName}</span>;
              }}
              renderUnChange={() => <span>{info.city_gas_supplier_name ?? ""}</span>}
            />
            <Dialog open={cityGasModalOpen} onOpenChange={setCityGasModalOpen}>
              <DialogTrigger hidden />
              <DialogContent className="w-[45vw] max-w-[800px] h-[530px]">
                <SupplierSearchModal
                  title="都市ガス供給事業者の選択"
                  expLabel="都市ガス供給事業者が見つからない場合は「代替値」を選択してください。"
                  searchNone={Messages.CITYGAS_SEARCH_NONE}
                  searchLabel="都市ガス供給事業者名"
                  apiPath="/api/building/energy-info/search/cityGas"
                  startYearMonth={startYearMonth}
                  mapItem={(item) => ({
                    id: item.city_gas_supplier_cd,
                    name: item.city_gas_supplier_nm,
                  })}
                  onSelect={(item) => handleSelectCityGasSupplier({ id: item.id, name: item.name })}
                />
              </DialogContent>
            </Dialog>
            <div className="pt-6 pb-6 text-[#667085] font-bold text-base leading-6 font-sans " ref={heatRef}>
              熱
            </div>
            <MasterFormField
              control={form.control}
              name="heat_supplier_no"
              label="契約先熱供給事業者"
              isEditing={isEditing}
              isConfirmation={isConfirmation}
              renderCustom={({ hasError }) => {
                const editedName = form.getValues("heat_supplier_name");
                const initialName = info.heat_supplier_name;
                const displayName = selectedHeatSupplierName ?? editedName ?? initialName ?? "";

                return isEditing ? (
                  <div
                    className="flex items-center gap-2 w-full"
                    tabIndex={-1}
                    onBlur={() => {
                      form.trigger("heat_supplier_no");
                    }}
                  >
                    <div
                      className={clsx(supplierInputClass, hasError ? "input-text-error" : "border border-[#98A2B3]")}
                    >
                      <span>{displayName}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setHeatSupplierModalOpen(true)}
                      className="border w-20 h-10 rounded flex items-center justify-center whitespace-nowrap
             text-teal-600 border-teal-600 cursor-pointer"
                    >
                      選択
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 w-full">
                    <div
                      className={clsx(supplierInputClass, hasError ? "input-text-error" : "border border-[#98A2B3]")}
                    >
                      <span>{displayName}</span>
                    </div>
                  </div>
                );
              }}
              renderConfirmChange={() => {
                const buildingId = building.building_id;
                const confirmDataName = pendingConfirmData?.[buildingId]?.heat_supplier_name;
                const initialName = info.heat_supplier_name;
                const editedName = form.getValues("heat_supplier_name");
                const displayName = confirmDataName ?? editedName ?? initialName ?? "";
                return <span>{displayName}</span>;
              }}
              renderUnChange={() => <span>{info.heat_supplier_name ?? ""}</span>}
            />
            <Dialog open={heatSupplierModalOpen} onOpenChange={setHeatSupplierModalOpen}>
              <DialogTrigger hidden />
              <DialogContent className="w-[45vw] max-w-[800px] h-[530px]">
                <SupplierSearchModal
                  title="熱供給事業者の選択"
                  expLabel="熱供給事業者が見つからない場合は「代替値」を選択してください。"
                  searchNone={Messages.HEAT_SEARCH_NONE}
                  searchLabel="熱供給事業者名"
                  apiPath="/api/building/energy-info/search/heatSupplier"
                  startYearMonth={startYearMonth}
                  mapItem={(item) => ({
                    id: item.heat_supplier_cd,
                    name: item.heat_supplier_name,
                  })}
                  onSelect={(item) => handleSelectHeatSupplier({ id: item.id, name: item.name })}
                />
              </DialogContent>
            </Dialog>
          </CardContent>

          <div className="h-px  w-full bg-[#D0D5DD]" />
          <div className="pl-6 text-[#667085] font-bold text-base leading-6 font-sans" ref={energyRef}>
            エネルギー使用量
          </div>
          <div className="flex pl-6 w-full flex-col items-start gap-6 rounded-lg border border-[#D0D5DD] bg-white shadow-[0px_2px_4px_-2px_rgba(16,24,40,0.06),0px_4px_8px_-2px_rgba(16,24,40,0.10)] p-6 mb-6">
            {isEditing
              ? fields.map((fieldItem, index) => {
                const energyInfoItem = form.watch(`energy_info.${index}`);
                const energyCode = energyInfoItem?.energy_code ?? "";

                const selectedOption = energyOptions.find((opt) => opt.energy_code === energyCode);

                const unitOptions = selectedOption?.energy_unit_original ?? [];
                const watchedEnergyInfo = form.watch("energy_info") ?? [];

                const selectedCodes = watchedEnergyInfo
                  .map((item, i) => (i !== index ? item?.energy_code : null))
                  .filter((code): code is string => !!code);

                const availableEnergyOptions = energyOptions.filter(
                  (opt) => !selectedCodes.includes(opt.energy_code) || opt.energy_code === energyCode,
                );

                return (
                  <div key={fieldItem.id} className="w-full border-b border-gray-300 pb-6">
                    <div className="grid w-full px-1 gap-x-4 gap-y-2 grid-cols-[minmax(12rem,max-content)_8rem] items-start">
                      <FormLabel className="text-left input-item-title whitespace-nowrap">
                        エネルギーの種類【{index + 1}】
                      </FormLabel>
                      <FormLabel className="text-left input-item-title whitespace-nowrap">単位</FormLabel>
                      {/* エネルギー種別 */}
                      <FormField
                        control={form.control}
                        name={`energy_info.${index}.energy_code`}
                        render={({ field }) => {
                          const safeValue = field.value ?? "";

                          return (
                            <FormItem>
                              <Select
                                value={safeValue}
                                onValueChange={(value) => {
                                  if (!value) return;

                                  field.onChange(value);

                                  const matched = energyOptions.find((e) => e.energy_code === value);

                                  form.setValue(`energy_info.${index}.energy_name_jp`, matched?.energy_name_jp ?? "");

                                  form.setValue(
                                    `energy_info.${index}.energy_unit_original`,
                                    matched?.energy_unit_original?.[0] ?? "",
                                  );
                                }}
                                disabled={field.value === "0200010011"}
                              >
                                <FormControl>
                                  <SelectTrigger className="w-fit min-w-[16rem] whitespace-nowrap">
                                    <SelectValue placeholder="選択してください" />
                                  </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                  {availableEnergyOptions.map((option) => (
                                    <SelectItem key={option.energy_code} value={option.energy_code}>
                                      {option.energy_name_jp}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </FormItem>
                          );
                        }}
                      />

                      {/* 単位 */}
                      <FormField
                        control={form.control}
                        name={`energy_info.${index}.energy_unit_original`}
                        render={({ field }) => (
                          <FormItem>
                            <Select
                              value={field.value ?? ""}
                              onValueChange={(value) => field.onChange(value)}
                              disabled={unitOptions.length === 0}
                            >
                              <FormControl>
                                <SelectTrigger className="w-32 whitespace-nowrap">
                                  {field.value || "単位を選択"}
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                {unitOptions.map((unit) => (
                                  <SelectItem key={unit} value={unit}>
                                    {unit}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </FormItem>
                        )}
                      />
                    </div>
                    {energyCode === "0200010011" && (
                      <div className="w-full flex mt-2">
                        <Button
                          variant="second"
                          size="lg"
                          onClick={() => handleAutoFillElectricity(index)}
                          iconLeft={<Icon name="download" />}
                        >
                          契約情報から使用量を自動入力する
                        </Button>
                      </div>
                    )}

                    <div className="mt-4 grid grid-cols-6 gap-0 w-full">
                      {Array.from({ length: 12 }, (_, monthIndex) => {
                        const fieldName = `energy_info.${index}.energy_quantity.${monthIndex}` as const;

                        const error = form.formState.errors?.energy_info?.[index]?.energy_quantity?.[monthIndex];

                        return (
                          <FormField
                            key={monthIndex}
                            control={form.control}
                            name={fieldName}
                            render={({ field }) => (
                              <FormItem className="flex flex-col text-base w-full border border-gray-200">
                                <div className="w-full bg-[#F2F4F7] text-gray-600 px-3 py-2 text-sm">
                                  {monthLabels[monthIndex]}
                                </div>

                                <FormControl>
                                  <div className="w-full bg-white px-3 py-2">
                                    <Input
                                      {...field}
                                      type="number"
                                      step="any"
                                      className={clsx(
                                        "w-full h-8 px-2 text-sm bg-white border-none",
                                        error && "border border-red-500",
                                      )}
                                      placeholder="0"
                                      disabled={!isEditing}
                                      onBlur={() => {
                                        field.onBlur();
                                        form.trigger(fieldName);
                                      }}
                                    />
                                  </div>
                                </FormControl>

                                <FormMessage className="px-3 pt-1 text-sm text-red-500" />
                              </FormItem>
                            )}
                          />
                        );
                      })}
                    </div>
                    <div className="text-left w-full mt-2 pr-2 not-italic font-normal leading-[150%] text-gray-700">
                      合計:{" "}
                      {Array.isArray(energyInfoItem?.energy_quantity)
                        ? (() => {
                          const quantities = energyInfoItem.energy_quantity ?? [];

                          const sum = quantities.slice(0, 12).reduce((acc, val) => acc + (Number(val) || 0), 0);

                          const sumStr = sum % 1 === 0 ? String(sum) : sum.toFixed(2);

                          const [intPart, decPart = ""] = sumStr.split(".");
                          const isValid = intPart.length <= 15 && decPart.length <= 10;

                          return (
                            <>
                              {sum}

                              {!isValid && (
                                <div className="text-red-500 text-sm mt-1 font-bold">
                                  合計が15桁以内の整数および10桁以内の小数になるよう入力してください
                                </div>
                              )}

                              {form.formState.errors?.energy_info?.[index]?.energy_quantity &&
                                !Array.isArray(form.formState.errors.energy_info[index].energy_quantity) && (
                                  <div className="text-red-500 text-sm mt-1 font-bold">
                                    {form.formState.errors.energy_info[index].energy_quantity?.message}
                                  </div>
                                )}
                            </>
                          );
                        })()
                        : "0"}
                    </div>
                  </div>
                );
              })
              : (() => {
                const rawList = isConfirmation
                  ? pendingConfirmData?.[building.building_id]?.energy_info ?? []
                  : form.watch("energy_info") ?? [];

                const energyList = [...rawList].sort((a, b) => {
                  if (a.energy_code === "0200010011") return -1;
                  if (b.energy_code === "0200010011") return 1;
                  return 0;
                });

                return energyList.map((energyInfoItem, displayIndex) => {
                  const energyCode = energyInfoItem?.energy_code ?? "";
                  const selectedOption = energyOptions.find((opt) => opt.energy_code === energyCode);
                  const normalizedQuantities = Array.from({ length: 12 }, (_, i) => {
                    const val = energyInfoItem?.energy_quantity?.[i];
                    if (val == null) return 0;
                    return typeof val === "number" ? val : Number(val) || 0;
                  });

                  const sum = normalizedQuantities.reduce((acc, val) => acc + val, 0);
                  const sumDisplay = sum % 1 === 0 ? String(sum) : sum.toFixed(2);

                  return (
                    <div
                      key={`display-${displayIndex}`}
                      className="flex flex-col items-start gap-2 w-full border-b border-gray-300 pb-6"
                    >
                      <div className="flex gap-6 w-full">
                        <div className="w-52">
                          <div className="text-sm text-gray-500">エネルギーの種類【{displayIndex + 1}】</div>
                          <div>{selectedOption?.energy_name_jp}</div>
                        </div>
                        <div className="w-32">
                          <div className="text-sm text-gray-500">単位</div>
                          <div>{energyInfoItem?.energy_unit_original}</div>
                        </div>
                      </div>

                      <div className="mt-4 grid grid-cols-6 gap-0 w-full">
                        {normalizedQuantities.map((value, monthIndex) => (
                          <div key={monthIndex} className="flex flex-col text-base w-full border border-gray-200">
                            <div className="w-full bg-[#F2F4F7] text-gray-600 px-3 py-2 text-sm">
                              {monthLabels[monthIndex]}
                            </div>
                            <div className="w-full bg-white px-3 py-2 text-sm text-gray-800">{value}</div>
                          </div>
                        ))}
                      </div>

                      {/* ===== 合計表示 ===== */}
                      <div className="text-left w-full mt-2 pr-2 not-italic font-normal leading-[150%] text-gray-700">
                        合計: {sumDisplay}
                      </div>
                    </div>
                  );
                });
              })()}

            {/* ===== 追加ボタン ===== */}
            {isEditing && (
              <Button
                variant="outline"
                type="button"
                size="lg"
                onClick={handleAddEnergy}
                disabled={energyOptions.length === 0}
                iconLeft={<Icon name="plus" />}
              >
                エネルギー追加
              </Button>
            )}
          </div>
          <div className="w-[400px]">
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger hidden />
              <DialogContent className="w-[45vw] max-w-[800px] h-[530px]">
                <SupplierSearchModal
                  title="電気事業者の選択"
                  expLabel="電気事業者が見つからない場合は「代替値」を選択してください。"
                  searchNone={Messages.ELECTRIC_SEARCH_NONE}
                  searchLabel="電気事業者名"
                  apiPath="/api/building/energy-info/search/electricCo"
                  startYearMonth={startYearMonth}
                  mapItem={(item) => ({
                    id: item.electric_company_reg_no,
                    name: item.electric_co_name,
                    extra: { selectMenu: item.select_menu },
                  })}
                  onSelect={(item) =>
                    handleSelectElectricCompany({
                      id: item.id,
                      name: item.name,
                      selectMenu:
                        (item.extra as { selectMenu?: { menu_no: string; menu_nm: string }[] })?.selectMenu ?? [],
                    })
                  }
                />
              </DialogContent>
            </Dialog>
          </div>
        </form>
      </FormProvider>
    );
  },
);

BuildingEnergyForm.displayName = "BuildingEnergyForm";

export default BuildingEnergyForm;
