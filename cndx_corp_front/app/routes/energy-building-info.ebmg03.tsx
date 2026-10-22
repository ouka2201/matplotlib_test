// import { MetaFunction } from "@remix-run/node";
import { useOutletContext } from "@remix-run/react";
import React, { useCallback, useEffect, useMemo, useRef, useState, useLayoutEffect } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import Icon from "~/components/icon";
import { Text } from "~/components/import";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import MasterLayout from "~/components/layout/master-layout";
import { useSession } from "~/components/layout/session-provider";
import Data from "~/components/screen/energy-building/ebmg03/BaseEnergyData";
import Index from "~/components/screen/energy-building/ebmg03/BaseEnergyIndex";
import { Messages } from "~/constants/messages/message";
import {
  BuildingInfo,
  BuildingInfoFormValues,
  EnergyBuildingDataset,
  IndustryClassMinor,
} from "~/types/screen/energy-building/ebmg/ebmgType";
import { CustomerCompany } from "~/types/screen/master/mscs/mscsType";
import { toast } from "../components/ui/use-toast";
import { postData } from "../lib/fetch";

type Option = {
  id: string;
  name: string;
};

// export const meta: MetaFunction = () => {
//   return [{ title: "拠点・エネルギー情報" }, { name: "description", content: "energy info" }];
// };

const ChiginEnergyInfo: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { session, clearSession } = useSession();
  const [corporateData, setCorporateData] = useState<CustomerCompany | null>(null);
  const [token, setToken] = useState<string | null>(session?.token ?? null);
  const [userId, setUserId] = useState<string | null>(null); // ユーザID
  const [orgId, setOrgId] = useState<string | null>(session?.selectedOrgId ?? null); // 組織ID
  const [createOrgId, setCreateOrgId] = useState<string | null>(null);
  const [agreementCategory, setAgreementCategory] = useState(session?.selectedAgreementCategory ?? ""); // 同意書取得区分
  const [registrationSeq, setRegistrationSeq] = useState(0); // 登録回数
  const [displayRegistrationSeq, setDisplayRegistrationSeq] = useState<number | null>(0);
  const [startYearMonth, setStartYearMonth] = useState(""); // 対象年月(始)
  const [endYearMonth, setEndYearMonth] = useState(""); // 対象年月(終)
  const [buildingDataset, setBuildingDataset] = useState<EnergyBuildingDataset | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const [isEditing, setIsEditing] = useState(location.state?.mode === "edit");
  const [isConfirmation, setIsConfirmation] = useState(false);
  const [isGoingToConfirmation, setIsGoingToConfirmation] = useState(false);
  const [pendingConfirmData, setPendingConfirmData] = useState<Record<string, BuildingInfoFormValues> | null>(null);
  const [triggerConfirm, setTriggerConfirm] = useState(false);
  const [confirmedValues, setConfirmedValues] = useState<Record<string, BuildingInfoFormValues>>({});
  const [editedData, setEditedData] = useState<Record<string, Partial<BuildingInfo>>>({});
  const buildingFormRefs = useRef<Record<string, UseFormReturn<BuildingInfo>>>({});
  const [entryDraftFlag, setEntryDraftFlag] = useState("");
  const [initialDraftFlag, setInitialDraftFlag] = useState<string>("");
  const [isFormDirty, setIsFormDirty] = useState(false);
  const [validationMode, setValidationMode] = useState<"nonRequired" | "full">("full");
  const forwardTriggerRef = useRef<
    Record<string, { trigger: () => Promise<boolean>; getValues: () => BuildingInfoFormValues }>
  >({});
  const [resetTrigger, setResetTrigger] = useState(0);
  const resetFuncMap = useRef<Record<string, (values: any | null) => void>>({});
  const scrollRefMap = useRef<Record<string, React.RefObject<HTMLDivElement>>>({});
  const [lastInlineType, setLastInlineType] = useState<"register" | "draft" | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [prefectureOptions, setPrefectureOptions] = useState<PrefectureOption[]>([]);
  const [canEditData, setCanEditData] = useState(false);
  // const [initialBuildingInfoMap, setInitialBuildingInfoMap] = useState<Record<string, BuildingInfo>>({});
  const stateData = location.state as CustomerCompany | undefined;
  const [loginOrgId, setLoginOrgId] = useState<string | null>(null);
  const { setHeaderTitle } = useOutletContext<{
    setHeaderTitle: React.Dispatch<React.SetStateAction<string>>;
  }>();

  interface PrefectureOption {
    id: string;
    name: string;
  }

  useEffect(() => {
    const fetchCorporateData = () => {
      // const stateData = location.state as CustomerCompany | undefined;

      if (stateData) {
        setCorporateData(stateData);
        sessionStorage.setItem("corporateData", JSON.stringify(stateData));
      } else {
        const stored = sessionStorage.getItem("corporateData");
        if (stored) {
          setCorporateData(JSON.parse(stored));
        }
      }
    };

    const fetchTokenAndUserIdFromSessionStorage = () => {
      if (typeof window !== "undefined") {
        const sessionData = sessionStorage.getItem("session");
        const storedOrgId = sessionStorage.getItem("selectedOrgId");
        if (storedOrgId) {
          setOrgId(storedOrgId);
        }
        //const dummyDataId = "test1@example.com";
        //const dummyDataId = "dummy@data.mail";
        // const dummyDataId = "ep0@test.com";
        //onst dummyDataOrgId = "org_000";
        //const dummyDataOrgId = "1";
        // const dummyDataOrgId = "TEP";

        if (sessionData) {
          const sessionObj = JSON.parse(sessionData);

          // トークン処理
          if (sessionObj?.token) {
            setToken(sessionObj.token);
          } else {
            console.log(Messages.VALIDATION.data.token_none);
            setToken(null);
          }

          // email を user_id として扱う
          if (sessionObj?.email) {
            setUserId(sessionObj.email);
          } else {
            setUserId(null);
          }

          if (!storedOrgId) {
            if (sessionObj?.authorityInfo.org_id) {
              setOrgId(sessionObj.authorityInfo.org_id);
            } else {
              console.log(Messages.energy_building_info.ebmg03.org_id_none);
              setOrgId(null);
            }
          }
        } else {
          console.log(Messages.VALIDATION.data.session_none);
          setToken(null);
          setUserId(null);
          if (!storedOrgId) {
            setOrgId(null);
          }
          //setUserId(dummyDataId);
          //setOrgId(dummyDataOrgId);
        }
      }
    };

    const fetchTargetYearMonth = () => {
      const storedReportInfo = sessionStorage.getItem("reportStatusInfo");
      let reportInfo: {
        start_year_month: string;
        end_year_month: string;
        entry_draft_flag?: string;
        registration_seq?: number;
        agreement_category?: string;
        create_org_id?: string;
      } | null = null;

      try {
        reportInfo = storedReportInfo ? JSON.parse(storedReportInfo) : null;
      } catch (e) {
        console.warn(Messages.energy_building_info.ebmg03.json_parse_failed);
      }

      const start = reportInfo?.start_year_month ?? "";
      const end = reportInfo?.end_year_month ?? "";
      const draftFlag = reportInfo?.entry_draft_flag ?? "";
      const registrationSeq = reportInfo?.registration_seq ?? 0;
      const agreementCode = reportInfo?.agreement_category ?? "";
      const createOrgId = reportInfo?.create_org_id ?? "";

      setStartYearMonth(start);
      setEndYearMonth(end);
      setEntryDraftFlag(draftFlag);
      setRegistrationSeq(registrationSeq);
      setAgreementCategory(agreementCode);
      setCreateOrgId(createOrgId);
      setInitialDraftFlag(draftFlag);
    };

    const setLoginUserOrgId = () => {
      const sessionData = sessionStorage.getItem("session");
      if (!sessionData) {
        setLoginOrgId(null);
        return;
      }

      const sessionObj = JSON.parse(sessionData);

      setLoginOrgId(sessionObj?.authorityInfo?.org_id ?? null);
    };

    fetchCorporateData();
    fetchTokenAndUserIdFromSessionStorage();
    fetchTargetYearMonth();
    setLoginUserOrgId();
  }, [location.state]);

  useEffect(() => {
    let isCancelled = false;

    const fetchMaster = async () => {
      if (!token) return;
      const masterEntries = [{ name: "prefecture", params: {} as Record<string, string> }];
      try {
        const data = await getMasterDataForCondition(masterEntries, token);
        if (!isCancelled) {
          setPrefectureOptions(data["prefecture"] ?? []);
        }
      } catch (err) {
        if (!isCancelled) {
          console.error(Messages.VALIDATION.data.fetch_master_error, err);
          setErrorMessage(err instanceof Error ? err.message : Messages.VALIDATION.api.fetch_error);
        }
      }
    };

    fetchMaster();

    return () => {
      isCancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (entryDraftFlag === "") {
      // 新規登録の場合のみ編集可能
      setIsEditing(true);
    } else {
      // 下書き（"1"）または本登録（"0"）の場合は編集不可（閲覧のみ）
      setIsEditing(false);
    }
  }, [entryDraftFlag, orgId, createOrgId]);

  useEffect(() => {
    // 確認画面でなく、かつ編集モードの場合に編集可能
    setCanEditData(!isConfirmation && isEditing);
  }, [isConfirmation, isEditing]);

  const loadItems = useCallback(
    async (overrideRegistrationSeq?: number, overrideEntryDraftFlag?: "0" | "1" | "") => {
      function isErrorWithStatus(error: unknown): error is { status: number; error_message_list?: string } {
        return (
          typeof error === "object" &&
          error !== null &&
          "status" in error &&
          typeof (error as { status: number }).status === "number"
        );
      }

      const params = {
        corporate_number: corporateData?.corporate_number ?? "",
        agreement_category: agreementCategory ?? "",
        user_id: userId ?? "",
        org_id: orgId ?? "",
        start_year_month: startYearMonth ?? "",
        end_year_month: endYearMonth ?? "",
        entry_draft_flag: overrideEntryDraftFlag ?? entryDraftFlag ?? "",
        registration_seq: overrideRegistrationSeq ?? registrationSeq ?? 0,
      };

      const requestUrl = `/api/building/energy-info/detail`;
      try {
        const response = await postData(requestUrl, params, {
          Authorization: `Bearer ${token}`,
        });

        const data = response.result;

        if (
          data &&
          Array.isArray(data.buildings) &&
          data.industry_class_minor &&
          data.industry_class_detail &&
          data.city_gas &&
          data.heat_supplier
        ) {
          const uniqueIndustryClassMinor = Array.from(
            new Map(
              data.industry_class_minor.map((item: IndustryClassMinor) => [
                `${item.group_code}-${item.group_name}`,
                item,
              ]),
            ).values(),
          );

          const dataset: EnergyBuildingDataset = {
            ...data,
            industry_class_minor: uniqueIndustryClassMinor,
          };

          const initialMap: Record<string, BuildingInfo> = {};
          data.buildings.forEach((b) => {
            initialMap[b.building_id] = b.building_info;
          });

          if (data.buildings.length > 0) {
            const seq = data.buildings[0].building_info.registration_seq;
            const normalizedSeq = seq === "" ? null : Number(seq);
            setDisplayRegistrationSeq(normalizedSeq);
          }

          // setInitialBuildingInfoMap(initialMap);

          setBuildingDataset(dataset);
          setErrorMessage("");
          return dataset;
        } else {
          setErrorMessage(Messages.VALIDATION.data.invalid);
          console.error(Messages.VALIDATION.data.invalid, data);
          return null;
        }
      } catch (error: unknown) {
        console.error(Messages.VALIDATION.api.error, error);

        if (isErrorWithStatus(error)) {
          if (error.status === 401) {
            clearSession();
            sessionStorage.removeItem("session");
            return (window.location.href = "/session-expired");
          }

          switch (error.status) {
            case 400:
              setErrorMessage(error.error_message_list || Messages.VALIDATION_ERROR);
              break;
            case 500:
              setErrorMessage((error as any).data?.message || (error as any).message || Messages.SYSTEM_ERROR);
              break;
            default:
              setErrorMessage(Messages.UNKNOWN_ERROR);
              break;
          }
        } else {
          setErrorMessage(Messages.VALIDATION.api.error);
        }
      }

      return null;
    },
    [token, agreementCategory, corporateData, orgId, entryDraftFlag, registrationSeq],
  );

  useEffect(() => {
    if (corporateData) {
      loadItems();
    }
  }, [corporateData, agreementCategory, orgId, loadItems]);

  // buildingDatasetからオプション配列を算出
  const industryClassMinorOptions = useMemo<Option[]>(() => {
    if (!buildingDataset?.industry_class_minor) return [];
    return buildingDataset.industry_class_minor.map((item) => ({
      id: item.group_code,
      name: item.group_name,
    }));
  }, [buildingDataset]);

  const industryClassDetailOptions = useMemo<Option[]>(() => {
    if (!buildingDataset?.industry_class_detail) return [];
    return buildingDataset.industry_class_detail.map((item) => ({
      id: item.industry_code,
      name: item.industry_name,
    }));
  }, [buildingDataset]);

  function getDiff(base: BuildingInfo, updated: BuildingInfo): Partial<BuildingInfo> {
    const diff: Partial<BuildingInfo> = {};

    // 差分関係なく常に送る
    diff.building_name = updated.building_name;
    diff.industry_class_major_code = updated.industry_class_major_code;
    diff.industry_class_middle_code = updated.industry_class_middle_code;
    diff.ep_office_code = updated.ep_office_code;
    diff.ep_customer_number = updated.ep_customer_number;
    diff.supply_point_number = updated.supply_point_number;

    // // 差分がある場合のみ送る
    // if (!isEqual(base.industry_class_minor_code, updated.industry_class_minor_code)) {
    //   diff.industry_class_minor_code = updated.industry_class_minor_code;
    // }
    // if (!isEqual(base.industry_class_detail_code, updated.industry_class_detail_code)) {
    //   diff.industry_class_detail_code = updated.industry_class_detail_code;
    // }
    // if (!isEqual(base.gross_floor_area, updated.gross_floor_area)) {
    //   diff.gross_floor_area = updated.gross_floor_area;
    // }
    // if (!isEqual(base.electricity_supplier_no, updated.electricity_supplier_no)) {
    //   diff.electricity_supplier_no = updated.electricity_supplier_no;
    // }
    // if (!isEqual(base.menu_no, updated.menu_no)) {
    //   diff.menu_no = updated.menu_no;
    // }
    // if (!isEqual(base.city_gas_supplier_no, updated.city_gas_supplier_no)) {
    //   diff.city_gas_supplier_no = updated.city_gas_supplier_no;
    // }
    // if (!isEqual(base.heat_supplier_no, updated.heat_supplier_no)) {
    //   diff.heat_supplier_no = updated.heat_supplier_no;
    // }
    // if (!isEqual(base.energy_info, updated.energy_info)) {
    //   diff.energy_info = updated.energy_info;
    // }
    // 更新時に変更がない場合でも送信する必要がある
    diff.industry_class_minor_code = updated.industry_class_minor_code;
    diff.industry_class_detail_code = updated.industry_class_detail_code;
    diff.gross_floor_area = updated.gross_floor_area;
    diff.electricity_supplier_no = updated.electricity_supplier_no;
    diff.menu_no = updated.menu_no;
    diff.city_gas_supplier_no = updated.city_gas_supplier_no;
    diff.heat_supplier_no = updated.heat_supplier_no;
    diff.energy_info = updated.energy_info;
    diff.electricity_supplier_name = updated.electricity_supplier_name;

    return diff;
  }

  const handleRegister = async (entryDraftFlag: "0" | "1" | "") => {
    if (!buildingDataset) return;

    const allErrors: string[] = [];

    // --- 下書きやバリデーション ---
    const updatedBuildings = await Promise.all(
      buildingDataset.buildings.map(async (original) => {
        const buildingId = original.building_id;
        const ref = buildingFormRefs.current[buildingId];
        if (!ref) return null;

        const formValues = pendingConfirmData?.[buildingId];
        if (!formValues) {
          console.warn(`buildingId=${buildingId} に対する pendingConfirmData が存在しません`);
          return null;
        }

        if (entryDraftFlag !== "1" && pendingConfirmData == null) {
          const isValid = await ref.trigger();
          if (!isValid) {
            const errors = ref.formState.errors;
            const labelMap: Record<string, string> = {
              industry_class_minor_code: "産業分類（小分類）",
              industry_class_detail_code: "産業分類（細分類）",
              gross_floor_area: "延床面積",
              electricity_supplier_no: "契約先電気事業者",
              energy_quantity: "エネルギー使用量",
            };

            const updatedEnergyInfo = formValues.energy_info ?? [];

            let validationErrorToastShown = false;

            Object.entries(errors).forEach(([field, value]) => {
              if (field === "energy_info" && Array.isArray(value)) {
                value.forEach((energyError, energyIndex) => {
                  const energy = updatedEnergyInfo[energyIndex];
                  const energyName = energy?.energy_name_jp ?? `エネルギーの種類【${energyIndex + 1}】`;
                  const baseMonth = Number(startYearMonth.slice(4)); // 1〜12
                  const monthLabels = Array.from({ length: 12 }, (_, i) => {
                    const month = ((baseMonth + i - 1) % 12) + 1;
                    return `${month}月`;
                  });

                  if (Array.isArray(energyError?.energy_quantity)) {
                    energyError.energy_quantity.forEach((monthError: { message?: string }, monthIndex: number) => {
                      if (monthError) {
                        const monthLabel = monthLabels[monthIndex] ?? `${monthIndex + 1}月`;
                        const message =
                          typeof monthError.message === "string" ? monthError.message : Messages.VALIDATION_ERROR;
                        if (message === Messages.VALIDATION_ERROR && !validationErrorToastShown) {
                          setErrorMessage(Messages.VALIDATION_ERROR);
                          validationErrorToastShown = true;
                        }
                        allErrors.push(
                          `【${original.building_info.building_name}】${energyName}（${monthLabel}）：${message}`,
                        );
                      }
                    });
                  } else if (energyError?.energy_quantity?.message) {
                    const message =
                      typeof energyError.energy_quantity.message === "string"
                        ? energyError.energy_quantity.message
                        : Messages.VALIDATION_ERROR;
                    if (message === Messages.VALIDATION_ERROR && !validationErrorToastShown) {
                      setErrorMessage(Messages.VALIDATION_ERROR);
                      validationErrorToastShown = true;
                    }
                    allErrors.push(`【${original.building_info.building_name}】${energyName}：${message}`);
                  }
                });
              } else {
                const label = labelMap[field as keyof BuildingInfo] || field;
                const message = typeof value?.message === "string" ? value.message : Messages.VALIDATION_ERROR;
                if (message === Messages.VALIDATION_ERROR && !validationErrorToastShown) {
                  setErrorMessage(Messages.VALIDATION_ERROR);
                  validationErrorToastShown = true;
                }
                allErrors.push(`【${original.building_info.building_name}】${label}：${message}`);
              }
            });

            return null;
          }
        }

        const base = original.building_info;
        const updated = formValues;

        const diff = getDiff(base, updated);

        // 共通で送るフィールド
        const fixedFields = {
          building_id: buildingId,
          registration_seq: displayRegistrationSeq ?? 0,
          entry_draft_flag: entryDraftFlag,
        };

        // 差分なし → 全件送信
        if (Object.keys(diff).length === 0) {
          return {
            ...fixedFields,
            ...updated,
          };
        }

        // 差分あり → 差分送信
        return {
          ...fixedFields,
          ...diff,
        };
      }),
    );

    if (allErrors.length > 0) {
      setErrorMessage(Messages.CONFIRM_ERROR_ITEMS);
      return;
    }

    const validBuildings = updatedBuildings.filter((b): b is NonNullable<typeof b> => b !== null);

    const industryErrors: string[] = [];

    validBuildings.forEach((b) => {
      if (b.industry_class_major_code === "") {
        industryErrors.push(Messages.energy_building_info.ebmg03.industry_major_error);
      }

      if (b.industry_class_middle_code === "") {
        industryErrors.push(Messages.energy_building_info.ebmg03.industry_middle_error);
      }
    });

    if (industryErrors.length > 0) {
      setErrorMessage(industryErrors);
      return;
    }

    // フィールド名変換
    const mappedBuildings = validBuildings.map((b) => {
      const {
        electricity_supplier_no,
        city_gas_supplier_no,
        heat_supplier_no,
        registration_seq,
        electricity_supplier_name,
        ...rest
      } = b;

      const originalFormData = pendingConfirmData?.[b.building_id];
      const energyInfoWithZeros = Array.isArray(originalFormData?.energy_info)
        ? originalFormData.energy_info.map((ei) => ({
            ...ei,
            energy_quantity: Array.isArray(ei.energy_quantity)
              ? ei.energy_quantity.slice(0, 12).map((val) => (val == null || String(val) === "" ? "0" : String(val)))
              : Array(12).fill("0"),
          }))
        : rest.energy_info;

      return {
        ...rest,
        energy_info: energyInfoWithZeros,
        ...(electricity_supplier_no !== undefined ? { electric_company_reg_no: electricity_supplier_no } : {}),
        ...(city_gas_supplier_no !== undefined ? { city_gas_reg_no: city_gas_supplier_no } : {}),
        ...(heat_supplier_no !== undefined ? { heat_supply_reg_no: heat_supplier_no } : {}),
        ...(electricity_supplier_name !== undefined ? { electricity_supplier_name: electricity_supplier_name } : {}),
      };
    });

    if (mappedBuildings.length === 0) {
      const message = Messages.energy_building_info.ebmg03.changed_data_none;
      console.log(message, { buildingDataset, pendingConfirmData });
      setErrorMessage(message);
      return;
    }

    const insertFlag = initialDraftFlag === "" ? true : false;
    // --- payload 作成 & API 登録 ---
    const fiscalYear = startYearMonth.slice(0, 4);
    const payload = {
      corporate_number: corporateData?.corporate_number,
      agreement_category: agreementCategory ?? "",
      // registration_seq: displayRegistrationSeq != null ? displayRegistrationSeq : null,
      registration_seq: sessionStorage.getItem("new_registrationSeq") ?? "",
      org_id: orgId ?? "",
      start_year_month: startYearMonth ?? "",
      end_year_month: endYearMonth ?? "",
      fiscal_year: fiscalYear,
      entry_draft_flag: entryDraftFlag,
      insert_flag: insertFlag,
      updated_building_info: mappedBuildings,
    };

    setIsSubmitting(true);
    try {
      const response = await postData("/api/building/energy-register", payload, {
        Authorization: `Bearer ${token}`,
      });

      const registrationSeq = response?.registration_seq;

      const storedReportInfo = sessionStorage.getItem("reportStatusInfo");
      if (storedReportInfo) {
        try {
          const reportInfo = JSON.parse(storedReportInfo);
          const updatedReportInfo = {
            ...reportInfo,
            entry_draft_flag: entryDraftFlag,
            registration_seq: registrationSeq ?? reportInfo.registration_seq,
          };
          sessionStorage.setItem("reportStatusInfo", JSON.stringify(updatedReportInfo));
        } catch (e) {
          console.warn(Messages.energy_building_info.ebmg03.json_parse_failed, e);
        }
      }

      if (registrationSeq !== undefined) {
        setRegistrationSeq(registrationSeq);
        setEntryDraftFlag(entryDraftFlag);
        setInitialDraftFlag(entryDraftFlag);
        setEditedData({});
        const refreshed = await loadItems(registrationSeq, entryDraftFlag);
        if (refreshed) setBuildingDataset(refreshed);
        setErrorMessage("");
        toast({
          title: entryDraftFlag ? "保存完了" : "登録完了",
          // description: Messages.REGISTER_SUCCESS,
          duration: 2000,
        });
        setIsConfirmation(false);
        setIsEditing(false);
        scrollToTop();
      }
    } catch (err) {
      console.error(Messages.REGISTER_FAILED, err);
      setErrorMessage(Messages.REGISTER_FAILED);
    } finally {
      setIsSubmitting(false);
    }
  };

  //エラー件数押下後のスクリーン処理
  const topRef = useRef<HTMLDivElement>(null);
  const scrollToTop = () => {
    topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    document.documentElement.scrollTop = 0;
  };

  const containerRef = useRef<HTMLDivElement | null>(null);

  const handleScrollTo = (key: string) => {
    const target = scrollRefMap.current[key];
    const container = containerRef.current;

    if (!target || !target.current || !container) {
      console.warn("ref or container missing", key);
      return;
    }

    requestAnimationFrame(() => {
      const offset = key.includes("熱") ? 5 : 25;

      const containerRect = container.getBoundingClientRect();
      const targetRect = target.current!.getBoundingClientRect();

      const scrollTop = container.scrollTop;

      const top = targetRect.top - containerRect.top + scrollTop - offset;

      const maxScroll = container.scrollHeight - container.clientHeight;

      const finalTop = Math.max(0, Math.min(top, maxScroll));

      container.scrollTo({
        top: finalTop,
        behavior: "smooth",
      });
    });
  };

  //ブラウザ制御
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!isFormDirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isFormDirty]);

  useEffect(() => {
    if (!isFormDirty) return;

    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const anchor = target.closest("a");

      if (anchor && anchor.href && anchor.target !== "_blank") {
        const confirmLeave = window.confirm(Messages.energy_building_info.ebmg03.leave);
        if (!confirmLeave) {
          e.preventDefault();
        }
      }
    };

    document.addEventListener("click", handleClick);

    return () => document.removeEventListener("click", handleClick);
  }, [isFormDirty]);

  //内容を修正
  const handleSetResetFunc = (buildingId: string, func: (values: any | null) => void) => {
    resetFuncMap.current[buildingId] = func;
  };

  // キャンセル時に全てのフォームをリセット
  const handleResetAll = () => {
    Object.entries(resetFuncMap.current).forEach(([buildingId, resetFunc]) => {
      const values = pendingConfirmData?.[buildingId];
      if (values) {
        resetFunc(values);
        resetFunc(values);
      } else {
        resetFunc(null);
        resetFunc(null);
      }
    });

    setIsEditing(true);
    setIsConfirmation(false);
  };

  //削除API
  const handleDeleteBuildingData = async (buildingIds: string[]) => {
    if (!buildingDataset) {
      console.warn("建物データが存在しません");
      return;
    }

    const deletePayload = buildingDataset.buildings
      .filter((b) => buildingIds.includes(b.building_id))
      .map((b) => ({
        building_id: b.building_id,
        energy_info: b.building_info.energy_info?.map((ei) => ({
          ...ei,
          energy_quantity: ei.energy_quantity?.slice(0, 12) ?? [],
        })),
      }));

    const fiscalYear = startYearMonth.slice(0, 4);

    const requestParams = {
      corporate_number: corporateData?.corporate_number,
      agreement_category: agreementCategory,
      fiscal_year: fiscalYear,
      registration_seq: registrationSeq,
      start_year_month: startYearMonth ?? "",
      updated_building_delete: deletePayload,
      lastInlineType: lastInlineType,
      org_id: orgId,
    };

    try {
      const response = await postData("/api/building/energy-info/delete", requestParams, {
        Authorization: `Bearer ${token}`,
      });
      toast({
        title: "削除完了",
        // description: Messages.DELETED_SUCCESS,
        // type: "success",
        duration: 2000,
      });
      console.log("削除成功:", response);
      loadItems();
      navigate("/energy-building/ebrc04");
    } catch (error) {
      console.error("削除エラー:", error);
      setErrorMessage(Messages.FAILED);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 w-full overflow-hidden">
      <MasterLayout
        useFullHeightLayout={true}
        isEditing={isEditing}
        hasSidebar={false}
        showRegisterButton={true}
        showCancelButton={true}
        showDraftButton={true}
        internalModals={true}
        footerType={isConfirmation ? "confirmation" : "default"}
        registerButtonDisabled={isSubmitting}
        draftButtonDisabled={isSubmitting}
        confirmButtonDisabled={isSubmitting}
        cancelConfirmButtonDisabled={isSubmitting}
        errorMessage={errorMessage}
        onClickError={scrollToTop}
        onInlineRegister={async () => {
          setValidationMode("full");

          const triggerResults = await Promise.all(Object.values(forwardTriggerRef.current).map((f) => f.trigger()));

          const allValid = triggerResults.every(Boolean);
          const hasElectricityUsage = Object.values(forwardTriggerRef.current).some((f) => {
            const values = f.getValues();

            return (
              Array.isArray(values.energy_info) &&
              values.energy_info.some(
                (energy) =>
                  energy.energy_code === "0200010011" &&
                  Array.isArray(energy.energy_quantity) &&
                  energy.energy_quantity.some((qty) => {
                    const num = Number(qty);
                    return !Number.isNaN(num) && num > 0;
                  }),
              )
            );
          });

          const errors: string[] = [];

          if (!hasElectricityUsage) {
            errors.push(Messages.energy_building_info.ebmg03.electricity_usage_required);
          }

          if (!allValid) {
            errors.push(Messages.VALIDATION_ERROR);
          }

          if (errors.length > 0) {
            setErrorMessage(errors);
            scrollToTop();
            return;
          }

          const newConfirmed: Record<string, BuildingInfoFormValues> = {};
          for (const [buildingId, f] of Object.entries(forwardTriggerRef.current)) {
            newConfirmed[buildingId] = f.getValues();
          }

          setPendingConfirmData(newConfirmed);
          setTriggerConfirm(true);
          setIsConfirmation(true);
          setIsEditing(false);
          setLastInlineType("register");
          setErrorMessage("");
          scrollToTop();
        }}
        onInlineDraft={async () => {
          setValidationMode("nonRequired");
          setTimeout(async () => {
            if (!forwardTriggerRef.current) return;

            const triggerResults = await Promise.all(Object.values(forwardTriggerRef.current).map((f) => f.trigger()));
            const allValid = triggerResults.every(Boolean);

            const hasElectricityUsage = Object.values(forwardTriggerRef.current).some((f) => {
              const values = f.getValues();

              return (
                Array.isArray(values.energy_info) &&
                values.energy_info.some(
                  (energy) =>
                    energy.energy_code === "0200010011" &&
                    Array.isArray(energy.energy_quantity) &&
                    energy.energy_quantity.some((qty) => {
                      const num = Number(qty);
                      return !Number.isNaN(num) && num > 0;
                    }),
                )
              );
            });

            const errors: string[] = [];

            if (!hasElectricityUsage) {
              errors.push(Messages.energy_building_info.ebmg03.electricity_usage_required);
            }

            if (!allValid) {
              errors.push(Messages.VALIDATION_ERROR);
            }

            if (errors.length > 0) {
              setErrorMessage(errors);
              scrollToTop();
              return;
            }

            // 全ビル分の値を取得
            const newConfirmed: Record<string, BuildingInfoFormValues> = {};
            for (const [buildingId, f] of Object.entries(forwardTriggerRef.current)) {
              newConfirmed[buildingId] = f.getValues();
            }

            setPendingConfirmData(newConfirmed);
            setTriggerConfirm(true);
            setIsConfirmation(true);
            setIsEditing(false);
            setLastInlineType("draft");
            setErrorMessage("");
            scrollToTop();
          }, 0);
        }}
        onInlineCancel={() => {
          setValidationMode("full");
          setResetTrigger((prev) => prev + 1);
          console.log("Resetting all forms...");
          handleResetAll();
          setIsEditing(true);
          setIsConfirmation(false);
        }}
        processClick={() => {
          if (lastInlineType === "register") {
            console.log("登録");
            handleRegister("0");
          } else {
            console.log("下書き処理呼ばれた");
            handleRegister("1");
          }
        }}
        onCancelClick={async () => {
          setValidationMode("full");
          setIsEditing(false);
          setIsConfirmation(false);
          setPendingConfirmData({});
          setTriggerConfirm(false);
          setErrorMessage("");
          setLastInlineType(null);
          setEditedData({});
          const items = await loadItems();
          if (items) {
            setBuildingDataset(items);
          }
        }}
      >
        <div className="flex h-full min-h-0">
          <div className="w-1/5 min-h-0 overflow-auto bg-gray-50 rounded">
            {buildingDataset ? (
              <Index
                buildingDataset={buildingDataset}
                startYearMonth={startYearMonth}
                entryDraftFlag={entryDraftFlag}
                onSelectItem={handleScrollTo}
                setHeaderTitle={setHeaderTitle}
              />
            ) : (
              <div>読み込み中...</div>
            )}
          </div>
          <div className="w-4/5 flex flex-col min-h-0 bg-gray-50 rounded">
            <div ref={containerRef} className="flex-1 min-h-0 overflow-auto">
              {buildingDataset ? (
                <Data
                  buildingDataset={buildingDataset}
                  prefectureOptions={prefectureOptions}
                  industryClassMinorOptions={industryClassMinorOptions}
                  industryClassDetailOptions={industryClassDetailOptions}
                  isEditing={canEditData}
                  setIsEditing={setIsEditing}
                  setEditedData={setEditedData}
                  editedData={editedData}
                  corporateData={corporateData}
                  agreementCategory={agreementCategory}
                  startYearMonth={startYearMonth}
                  endYearMonth={endYearMonth}
                  buildingFormRefs={buildingFormRefs}
                  errorMessage={errorMessage}
                  setErrorMessage={setErrorMessage}
                  scrollTargetRef={topRef}
                  userId={userId ?? ""}
                  orgId={orgId ?? ""}
                  createOrgId={createOrgId ?? ""}
                  token={token ?? ""}
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
                  onSetResetFunc={handleSetResetFunc}
                  resetTrigger={resetTrigger}
                  onDeleteBuildingData={handleDeleteBuildingData}
                  forwardTriggerRef={forwardTriggerRef}
                  validationMode={validationMode}
                  loginOrgId={loginOrgId ?? ""}
                />
              ) : (
                <div>
                  <div>
                    {!buildingDataset && errorMessage && (
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
                  </div>
                  読み込み中...
                </div>
              )}
            </div>
          </div>
        </div>
      </MasterLayout>
    </div>
  );
};

export default ChiginEnergyInfo;
