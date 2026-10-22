import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import CustomDialog from "~/components/modal/common-dialog";
import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle
} from "~/components/ui/dialog";
import { PageableTable } from "~/components/ui/pageable-table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Messages } from "~/constants/messages/message";
import { useScrollToError } from "~/hooks/useScrollToError";
import { cn } from "~/lib/utils";
import { ebrcReportCreateSchema } from "~/lib/validations/ebrc";
import "~/styles/CNTable.css";
import "~/styles/popup.css";
import CommonLayout from "../components/CommonLayout";
import { Icon, Text } from "../components/import";
import { AlertModal } from "../components/modal/alert-modal";
import { TabName } from "../components/tab-navigator";
import { saveSuccessToast, toast } from "../components/ui/use-toast";
import { getData, postData } from "../lib/fetch";

const REQUEST_TIMEOUT_MS: number = 300_000;
const REQUEST_TIMEOUT_ERROR_MESSAGE: string =
  "現在、カルテ作成に時間がかかっています。少し時間をおいてから、再度アクセスしてください。";

const CONSENT_CHANGED_EVENT = "eb_consent_changed";

const withTimeout = <T,>(promise: Promise<T>, timeoutMs: number): Promise<T> => {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => {
      const timeoutError = new Error(REQUEST_TIMEOUT_ERROR_MESSAGE) as Error & {
        isTimeout?: boolean;
        data?: { message: string };
      };
      timeoutError.isTimeout = true;
      timeoutError.data = { message: REQUEST_TIMEOUT_ERROR_MESSAGE };
      reject(timeoutError);
    }, timeoutMs);

    promise
      .then((result) => {
        clearTimeout(timer);
        resolve(result);
      })
      .catch((error) => {
        clearTimeout(timer);
        reject(error);
      });
  });
};

// function isErrorWithStatus(err: unknown): err is { status: number } {
//   return typeof err === "object" && err !== null && "status" in err;
// }

function LoadingDots() {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return <span className="inline-block ml-1 text-blue-600">{dots}</span>;
}

const REPORT_TYPES = {
  SIMPLE_CN: "00", // CNカルテ(簡易版)
  STANDARD_CN: "01", // CNカルテ(標準版)
} as const;

const GROUP_SELECTION_ERROR_MESSAGE = "少なくとも1つのグループと拠点タイプを選択してください";
const VALID_LOCATION_TYPES = ["1", "2", "3", "4", "5", "6", "7"];

type ReportType = (typeof REPORT_TYPES)[keyof typeof REPORT_TYPES];

type ReportCreationCondition = {
  period: {
    start: string;
    end: string;
    display: string;
  };
  reportType: ReportType;
};

type AcceptedDialogType = "accepted" | "creating";

// タイプ定義
type Group = {
  id: string;
  name: string;
  options: { no: string; label: string }[];
  agreementCategory?: string | null;
  groupNo?: string | null;
};

// type ConsentRouteRecord = {
//   agreementCategory?: string | null;
//   agreement_category?: string | null;
//   agreement_name?: string;
//   [key: string]: unknown;
// };

// type ConsentRouteOption = {
//   value: string;
//   label: string;
//   record?: ConsentRouteRecord;
// };

type Location = {
  id: string;
  name: string;
  agreement_org: string | null;
  agreementCategory: string | null;
  group1: string | null;
  group2: string | null;
  group3: string | null;
  group4: string | null;
  group5: string | null;
  target_year_months: string;
  org_id: string
};

type ReportCondition = {
  period: {
    start: string;
    end: string;
    display: string;
  };
  reportType: ReportType;
  orgName: string;
  building_id?: string | null;
  agreementCategory: string;
  orgId: string;
  agreementCategoryName: string;
  corporateNumber: string;
  downloads: {
    cnKartePdf: boolean;
    cnKarteCsv: boolean;
    missingData: boolean;
    kpi: boolean;
    backData: boolean;
  };
  multiCondition?: {
    entireCompany?: boolean;
    groupOption?: boolean;
    groupItem?: { groupId: string; locationType: string }[];
  };
  singleCondition?: {
    groupId?: string;
    locationType?: string;
    locationId?: string;
  };
  targetType?: "全体" | "グループ" | "個別";
};

const GROUP_KEYS = ["group1", "group2", "group3", "group4", "group5"] as const;
type GroupKey = (typeof GROUP_KEYS)[number];

type Report = {
  conditionId: string;
  period: {
    display: string;
    start?: string;
    end?: string;
  };
  reportType: string;
  agreementCategory?: string;
  orgName: string;
  targetType: "全体" | "グループ" | "個別";
  building_id?: string | null;
  building_name?: string;
  createdDate: string;
  author: string;
  group1?: string;
  group2?: string;
  group3?: string;
  group4?: string;
  group5?: string;
  cnKarte: { pdf: boolean; csv: boolean };
  missingData: { pdf: boolean };
  kpi: { csv: boolean };
  status: "作成済" | "作成中" | "未作成";
  locationId?: string;
  report_save_path?: string;

  // 画面表示用（既存実装に合わせて追加で載せてる）
  pdf?: string;
  csv?: string;
  loss_pdf?: string;
  kpi_csv?: string;
};
type OrgOption = {
  value: string;
  label: string;
  agreement_category: string;
};
type ReportCreationPopupProps = {
  showPopup: boolean;
  onClose: () => void;
  onAccepted: () => void;
  onSave: (report?: Report) => void;
  setAcceptedCondition: (condition: ReportCreationCondition) => void;
  corporateNumber: string;
  orgId: string;
  orgName?: string;

  // ★ CommonLayout の選択値を固定で渡す
  fixedAgreementCategory: string;
  fixedAgreementCategoryName: string;
};
const sectionStyle = "p-6 bg-white rounded-xl shadow border border-gray-200 mb-6";
const titleStyle = "text-lg font-bold mb-4 text-blue-800 border-b pb-2";
const gridStyle = "grid grid-cols-1 md:grid-cols-2 gap-4";

// ポップアップコンポーネント
const ReportCreationPopup = ({
  showPopup,
  onClose,
  onAccepted,
  onSave,
  setAcceptedCondition,
  corporateNumber,
  orgId,
  orgName = "",
  fixedAgreementCategory,
  fixedAgreementCategoryName,
}: ReportCreationPopupProps) => {
  const buildAcceptedCondition = (): ReportCreationCondition => ({
    period: condition.period,
    reportType: condition.reportType!,
  });
  const popupContentRef = useRef<HTMLDivElement>(null);

  const [condition, setCondition] = useState<ReportCondition>({
    period: { start: "", end: "", display: "" },
    reportType: "" as any,
    downloads: {
      cnKartePdf: false,
      cnKarteCsv: false,
      missingData: false,
      kpi: false,
      backData: false,
    },
    agreementCategory: fixedAgreementCategory || "",
    agreementCategoryName: fixedAgreementCategoryName || "",
    corporateNumber,
    orgId,
    orgName,
    targetType: "" as any,
    multiCondition: { entireCompany: false, groupOption: false, groupItem: [] },
  });

  const [groups, setGroups] = useState<Group[]>([]);
  const getOptionLabel = (groupId: string, optionNo: string) => {
    const g = groups.find((gg) => gg.id === groupId);
    return g?.options.find((o) => o.no === optionNo)?.label ?? "";
  };

  useEffect(() => {
    setCondition((prev) => ({ ...prev, corporateNumber, orgId, orgName }));
  }, [corporateNumber, orgId, orgName]);

  // ★ CommonLayout で切り替わった値が来たら、popup 内も必ず固定値へ追従
  useEffect(() => {
    setCondition((prev) => ({
      ...prev,
      agreementCategory: fixedAgreementCategory || "",
      agreementCategoryName: fixedAgreementCategoryName || "",
    }));
  }, [fixedAgreementCategory, fixedAgreementCategoryName]);

  const [allLocations, setAllLocations] = useState<Location[]>([]);
  const [years, setYears] = useState<string[]>([]);
  const [months, setMonths] = useState<string[]>([]);
  const [filteredLocations, setFilteredLocations] = useState<Location[]>([]);
  const [creationType, setCreationType] = useState<"multi" | "single">("multi");
  const [submitting, setSubmitting] = useState(false);

  const [selectedLocationType, setSelectedLocationType] = useState("");
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [selectedLocationIds, setSelectedLocationIds] = useState<string[]>([]);
  const [isFiltered, setIsFiltered] = useState(false);
  const [startMonth, setStartMonth] = useState("");
  const [endOptions, setEndOptions] = useState<string[]>([]);
  // const [endYmLimit, setEndYmLimit] = useState<string>("");
  const [startYmMap, setStartYmMap] = useState<Record<string, string[]>>({});
  const [selectedStartYear, setSelectedStartYear] = useState<string>("");

  // const [fiscalYears, setFiscalYears] = useState<string[]>([]);

  const [targetYearMonths, setTargetYearMonths] = useState<string[]>([]);

  const [token, setToken] = useState<string | null>(null);

  // const [orgNames, setOrgNames] = useState<{ value: string; label: string }[]>([]);
  const [orgNames, setOrgNames] = useState<OrgOption[]>([]);

  const [errorMessage, setErrorMessage] = useState<string | string[]>("");

  const errorTopRef = useScrollToError(errorMessage);
  const clearGroupSelectionError = () => {
    setErrorMessage((prev) => {
      if (typeof prev === "string" && prev === GROUP_SELECTION_ERROR_MESSAGE) return "";
      return prev;
    });
  };

  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  // const [confirmAction, setConfirmAction] = useState<() => Promise<void>>(() => Promise.resolve());
  const [isCloseConfirmOpen, setIsCloseConfirmOpen] = useState(false);
  // const { isVis } = useRoleFlags();

  const [errors, setErrors] = useState<Record<string, string[] | undefined>>({});
  // const navigate = useNavigate();

  useEffect(() => {
    const sessionData = sessionStorage.getItem("session");
    if (!sessionData) return;
    // const fetchConsentRoute = async () => {
    //   const url = `/api/corp/basic-info?corporate_number=${corporateNumber}`;
    //   const response = await getData(url);

    try {
      const session = JSON.parse(sessionData);
      setToken(session.token);
    } catch (e) {
      console.error("Error parsing session data:", e);
    }
  }, []);

  // agreementCategory で locations/groups をフィルタ
  const agreementFilteredLocations = useMemo(() => {
    return allLocations.filter((loc) => {
      const matchOrg =
        !condition.orgId || (loc.org_id ?? "") === condition.orgId;

      const locMonths = (loc.target_year_months ?? "")
        .split(",")
        .map((y) => y.trim());

      // const matchFiscalYear =
      //   fiscalYears.length === 0 ||
      //   locYears.some((y) => fiscalYears.includes(y));

      const matchTargetYearMonths =
        targetYearMonths.length === 0 ||
        locMonths.some((m) => targetYearMonths.includes(m));

      return matchOrg && matchTargetYearMonths;
    });
  }, [allLocations, targetYearMonths, condition.orgId]);


  const agreementFilteredGroups = useMemo(() => {
    if (!condition.agreementCategory) return groups;
    return groups.filter((group) => {
      if (!group.agreementCategory) return true;
      return group.agreementCategory === condition.agreementCategory;
    });
  }, [groups, condition.agreementCategory]);

  useEffect(() => {
    setFilteredLocations(agreementFilteredLocations);
    setSelectedLocationIds([]);
    setSelectedGroupId("");
    setSelectedLocationType("");
    setIsFiltered(false);
  }, [agreementFilteredLocations]);

  const extractYm = (raw: string): string | null => {
    const m = String(raw).match(/\d{6}/);
    return m ? m[0] : null;
  };

  useEffect(() => {
    const fetchOptions = async () => {
      if (!corporateNumber || !orgId) return;
      try {
        const url = `/api/report/cn-karte/options?corporate_number=${corporateNumber}&org_id=${orgId}&agreement_category=${fixedAgreementCategory}`;
        const data = await getData(url);

        const transformedGroups: Group[] = Object.entries(
          data.group_options as Record<
            string,
            {
              group_name: string;
              options: Record<string, string>;
              agreement_category?: string | null;
              group_no?: string | number | null;
            }
          >,
        ).map(([groupId, groupData]) => ({
          id: groupId,
          name: groupData.group_name,
          options: Object.entries(groupData.options).map(([no, label]) => ({ no, label })),
          agreementCategory: groupData.agreement_category ?? null,
          groupNo: groupData.group_no != null ? String(groupData.group_no) : null,
        }));
        type BuildingApiResponse = {
          building_id: string;
          location_identifier_name: string;
          agreement_org: string | null;
          agreement_category?: string | null;
          group1?: string | null;
          group2?: string | null;
          group3?: string | null;
          group4?: string | null;
          group5?: string | null;
          target_year_months: string,
          org_id: string
        };

        const transformedLocations: Location[] = (data.building_list as BuildingApiResponse[]).map((building) => ({
          id: building.building_id,
          name: building.location_identifier_name,
          agreement_org: building.agreement_org,
          agreementCategory: building.agreement_category ?? null,
          group1: building.group1 ?? null,
          group2: building.group2 ?? null,
          group3: building.group3 ?? null,
          group4: building.group4 ?? null,
          group5: building.group5 ?? null,
          target_year_months: building.target_year_months,
          org_id: building.org_id
        }));
        // const dedupedLocations = Array.from(new Map(transformedLocations.map((loc) => [loc.id, loc])).values());
        const dedupedLocations = Array.from(
          new Map(
            transformedLocations.map((loc) => [
              `${loc.id}_${loc.agreementCategory}_${loc.org_id}`,
              loc,
            ])
          ).values()
        );

        const transformedOrgNames = Array.from(
          new Map(
            (data.org_names ?? []).map((org: any) => [
              org.org_id,
              {
                value: org.org_id,
                label: org.org_name,
                agreement_category: org.agreement_category
              }
            ])
          ).values()
        );

        const startYmList = (data.start_year_months as string[]).map(extractYm).filter((x): x is string => !!x);

        const ymMap: Record<string, string[]> = {};
        for (const ym of startYmList) {
          const y = ym.slice(0, 4);
          const m = ym.slice(4, 6);
          if (!ymMap[y]) ymMap[y] = [];
          if (!ymMap[y].includes(m)) ymMap[y].push(m);
        }
        Object.keys(ymMap).forEach((y) => ymMap[y].sort());

        setOrgNames(transformedOrgNames);

        updateCondition({
          orgId: transformedOrgNames[0].value,
          orgName: transformedOrgNames[0].label || "",
        });
        setGroups(transformedGroups);
        setAllLocations(dedupedLocations);
        setStartYmMap(ymMap);
        setYears(Object.keys(ymMap).sort());
        setMonths([]);

        setSelectedStartYear("");
        setStartMonth("");
        setEndOptions([]);

        // setEndYmLimit(extractYm(data.end_year_month) ?? "");
      } catch (error: any) {
        console.error("オプション取得失敗:", error);
        setErrorMessage(error.data?.message);
      }
    };

    fetchOptions();
    // token が入る前に走ると Authorization が空になるので token も依存に入れる
  }, [corporateNumber, orgId, token]);

  const handleStartYearChange = (year: string) => {
    setSelectedStartYear(year);
    setStartMonth("");
    setErrorMessage("");
    setEndOptions([]);
    setMonths(startYmMap[year] ?? []);
    // const fiscalYears: string[] = [
    //   ...new Set(
    //     (startYmMap[year] ?? []).map(m =>
    //       Number(m) >= 4
    //         ? String(year)
    //         : String(Number(year) - 1)
    //     )
    //   )
    // ].sort();
    // setFiscalYears(fiscalYears)
    const targetMonths = startYmMap[year];
    const targetYearMonths = targetMonths.map((m) =>
      `${year}${m.padStart(2, "0")}`
    );

    setTargetYearMonths(targetYearMonths);
    setCondition((prev) => ({ ...prev, period: { start: "", end: "", display: "" } }));
  };

  const onChangeGroupId = (idx: number, groupId: string) => {
    updateGroupItem(idx, "groupId", groupId);
    updateGroupItem(idx, "locationType", "");
  };

  const updateGroupItem = (index: number, field: "groupId" | "locationType", value: string) => {
    clearGroupSelectionError();
    updateCondition((prev) => {
      const current = prev.multiCondition?.groupItem ?? [];
      const next = [...current];
      while (next.length <= index) {
        next.push({ groupId: "", locationType: "" });
      }
      next[index] = { ...next[index], [field]: value };

      return {
        multiCondition: {
          ...prev.multiCondition,
          groupItem: next,
        },
      };
    });
  };

  const updateCondition = (
    update: Partial<ReportCondition> | ((prev: ReportCondition) => Partial<ReportCondition>),
  ) => {
    setCondition((prev) => {
      const nextUpdate = typeof update === "function" ? update(prev) : update;
      return { ...prev, ...nextUpdate };
    });
  };

  // 同意書取得経路
  useEffect(() => {
    // 同意書取得経路が切り替わったら、group 選択をリセット
  }, [condition.agreementCategory]);

  useEffect(() => {
    if (!condition.multiCondition?.groupOption) return;
    const hasSelection = (condition.multiCondition?.groupItem ?? []).some((item) => item.groupId || item.locationType);
    if (!hasSelection) return;

    // 径路が切り替わっても group 選択をリセットしたい場合はここでやるが、
    // 今回は UI 変えずに維持（必要なら既存ロジックを戻してOK）
  }, [condition.agreementCategory, condition.multiCondition?.groupOption]);

  const handleEntireCompanyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const isChecked = e.target.checked;
    clearGroupSelectionError();
    updateCondition((prev) => ({
      multiCondition: {
        ...prev.multiCondition,
        entireCompany: isChecked,
        groupOption: !isChecked,
        groupItem: isChecked ? undefined : prev.multiCondition?.groupItem ?? [],
      },
    }));
  };

  const handleGroupSelectionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const isChecked = e.target.checked;
    clearGroupSelectionError();
    updateCondition((prev) => ({
      multiCondition: {
        ...prev.multiCondition,
        entireCompany: !isChecked,
        groupOption: isChecked,
        groupItem: isChecked
          ? [
            { groupId: "", locationType: "" },
            { groupId: "", locationType: "" },
          ]
          : [],
      },
    }));
  };

  const parseYm = (src: any, key?: "start" | "end") => {
    const v = key ? src?.[key] ?? {} : src ?? {};
    if (typeof v === "string") {
      const [y, m] = v.split("/");
      return { year: y ? String(y) : "", month: m ? String(m).padStart(2, "0") : "" };
    }
    const year = v?.year ?? v?.startYear ?? v?.endYear ?? "";
    const monthRaw = v?.month ?? v?.startMonth ?? v?.endMonth ?? "";
    return { year: year ? String(year) : "", month: monthRaw ? String(monthRaw).padStart(2, "0") : "" };
  };

  const createCnKarteVisReport = async (
    cond: ReportCondition,
    mode: "multi" | "single",
    singleBuildingIds: string[] = [],
  ) => {
    const isMulti = mode === "multi";

    const resolveGroupNo = (groupId: string) => {
      const matched = groups.find((group) => group.id === groupId);
      if (matched?.groupNo) return matched.groupNo;
      const legacyMatch = groupId.match(/_group(\d+)$/);
      if (legacyMatch) return legacyMatch[1];
      return "";
    };

    const groupList =
      isMulti && cond.multiCondition?.groupOption
        ? (cond.multiCondition.groupItem ?? [])
          .filter((item) => item.groupId && VALID_LOCATION_TYPES.includes(item.locationType))
          .map((item) => {
            const groupNo = resolveGroupNo(item.groupId);
            if (!groupNo) return null;
            return { group_no: groupNo, option_no: item.locationType };
          })
          .filter((item): item is { group_no: string; option_no: string } => item !== null)
        : [];

    const singleList: string[] = mode === "single" ? singleBuildingIds : [];

    const { year: start_year, month: start_month } = parseYm(cond.period, "start");
    const { year: end_year, month: end_month } = parseYm(cond.period, "end");

    try {
      const requestBody = {
        corporate_number: cond.corporateNumber,
        agreement_category: cond.agreementCategory,
        org_id: cond.orgId,

        start_year,
        start_month,
        end_year,
        end_month,

        consent_route: cond.agreementCategoryName || "",
        creation_format: cond.reportType || "00",
        need_data_insufficiency_list: cond.downloads?.missingData || false,

        need_report_backdata: cond.downloads?.cnKarteCsv || false,
        need_kpi_list: cond.downloads?.kpi || false,
        is_for_multibuilding: isMulti,
        group_for_multibuilding: groupList,
        building_ids_for_single: singleList,
      };

      await withTimeout(
        postData("/api/report/cn-karte/create/vis", requestBody, { Authorization: `Bearer ${token}` }),
        REQUEST_TIMEOUT_MS,
      );

      saveSuccessToast();
    } catch (error: any) {
      console.error("CNカルテ可視化データ作成エラー:", error);
      const isTimeoutError = (error as { isTimeout?: boolean })?.isTimeout;
      toast({
        title: "エラー",
        description: isTimeoutError ? REQUEST_TIMEOUT_ERROR_MESSAGE : error.data?.message || error.message,
        type: "error",
        duration: 5000,
      });
      throw error;
    }
  };

  const refreshReportsSafely = async (report?: Report) => {
    if (typeof onSave !== "function") return;
    try {
      await onSave(report);
    } catch (refreshError) {
      console.error("カルテ一覧の再取得に失敗しました:", refreshError);
    }
  };

  const handleCreateAndSave = async (mode: "multi" | "single") => {
    // 固定径路を condition に確実に反映（念押し）
    const nextCondition: ReportCondition = {
      ...condition,
      agreementCategory: fixedAgreementCategory || condition.agreementCategory,
      agreementCategoryName: fixedAgreementCategoryName || condition.agreementCategoryName,
      // orgId,
      corporateNumber,
      orgName,
    };

    const validationResult = ebrcReportCreateSchema.safeParse({
      startYear: selectedStartYear || "",
      startMonth: startMonth || "",
      reportType: nextCondition.reportType || "",
      agreementCategory: nextCondition.agreementCategory || "",
      orgId: nextCondition.orgId || "",
    });

    if (!validationResult.success) {
      const fieldErrors = validationResult.error.flatten().fieldErrors;

      setErrors({
        startYear: fieldErrors.startYear,
        startMonth: fieldErrors.startMonth,
        reportType: fieldErrors.reportType,
        agreementCategory: fieldErrors.agreementCategory,
        orgId: fieldErrors.orgId,
      });

      popupContentRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    if (mode === "multi") {
      const groupItems = nextCondition.multiCondition?.groupItem ?? [];
      const hasValidGroups = groupItems.some((it) => it.groupId && VALID_LOCATION_TYPES.includes(it.locationType));
      const hasIncompleteSelection = groupItems.some((item) => {
        const hasGroup = !!item.groupId;
        const hasLocation = !!item.locationType;
        if (!hasGroup && !hasLocation) return false;
        return !(hasGroup && VALID_LOCATION_TYPES.includes(item.locationType));
      });

      if (nextCondition.multiCondition?.groupOption && (!hasValidGroups || hasIncompleteSelection)) {
        setErrorMessage(GROUP_SELECTION_ERROR_MESSAGE);
        popupContentRef.current?.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }
    }

    onAccepted();

    try {
      setSubmitting(true);
      await createCnKarteVisReport(nextCondition, mode, mode === "single" ? selectedLocationIds : []);
      // toast({
      //   title: "保存成功",
      //   description: "カルテ作成後、保存に成功しました",
      //   type: "success",
      //   duration: 3000,
      // });
      setAcceptedCondition(buildAcceptedCondition());
    } catch (error: any) {
      console.error("カルテ作成・保存エラー:", error);
      const isTimeoutError = (error as { isTimeout?: boolean })?.isTimeout;
      toast({
        title: "エラー",
        description: isTimeoutError ? error.data?.message || error.message : error.data?.message || error.message,
        type: "error",
        duration: 5000,
        variant: "destructive",
      });
      // Error 時は modal を閉じる
      onClose();
      return;
    } finally {
      setSubmitting(false);
    }
    await refreshReportsSafely();
  };

  const multiGroupItems = condition.multiCondition?.groupItem ?? [];
  const g0 = multiGroupItems[0] ?? { groupId: "", locationType: "" };
  const g1 = multiGroupItems[1] ?? { groupId: "", locationType: "" };

  const handleConfirmMultiSubmit = async () => {
    try {
      setSubmitting(true);
      setCreationType("multi");

      const isEntireCompany = condition.multiCondition?.entireCompany;

      if (isEntireCompany) {
        await createCnKarteVisReport(
          {
            ...condition,
            agreementCategory: fixedAgreementCategory || condition.agreementCategory,
            agreementCategoryName: fixedAgreementCategoryName || condition.agreementCategoryName,
          },
          "multi",
        );
        await refreshReportsSafely();
        setAcceptedCondition(buildAcceptedCondition());
        onAccepted();
      } else {
        await handleConfirmSingleSubmit();
        return;
      }

      //onClose();
    } catch (error: any) {
      console.error("レポート作成エラー:", error);
      setErrorMessage(error.data?.message);
    } finally {
      setSubmitting(false);
      setIsConfirmModalOpen(false);
    }
  };

  const handleConfirmSingleSubmit = async () => {
    try {
      setSubmitting(true);
      setCreationType("single");

      const now = new Date();
      const reportTypeName = REPORT_TYPES[condition.reportType];
      const newReport: Report = {
        conditionId: `cond-${Date.now()}`,
        period: condition.period,
        reportType: reportTypeName,
        agreementCategory: fixedAgreementCategory || condition.agreementCategory || "",
        orgName: condition.orgName || "",
        targetType: "個別",
        createdDate: `${now.getFullYear()}/${(now.getMonth() + 1).toString().padStart(2, "0")}/${now
          .getDate()
          .toString()
          .padStart(2, "0")}`,
        author: "可視化",
        cnKarte: { pdf: condition.downloads.cnKartePdf, csv: condition.downloads.cnKarteCsv },
        missingData: { pdf: condition.downloads.missingData },
        kpi: { csv: condition.downloads.kpi },
        status: "作成済",
      };

      await refreshReportsSafely(newReport);
      setAcceptedCondition(buildAcceptedCondition());
      onAccepted();
      //onClose();
    } catch (error) {
      console.error("レポート作成エラー:", error);
      setErrorMessage("レポートの作成に失敗しました");
    } finally {
      setSubmitting(false);
      setIsConfirmModalOpen(false);
    }
  };

  const handleConfirmAction = () => {
    if (creationType === "single") {
      handleConfirmSingleSubmit();
    } else if (creationType === "multi") {
      handleConfirmMultiSubmit();
    }
  };

  const handleFilterToggle = () => {
    if (isFiltered) {
      setFilteredLocations(agreementFilteredLocations);
      setSelectedGroupId("");
      setSelectedLocationType("");
      setIsFiltered(false);
      setSelectedLocationIds([]);
      return;
    } else {
      if (!selectedGroupId) {
        setErrorMessage("グループを選択してください");
        return;
      }
      if (!selectedLocationType) {
        setErrorMessage("拠点タイプを選択してください");
        return;
      }
      const label = getOptionLabel(selectedGroupId, selectedLocationType);
      if (!label) {
        setErrorMessage("拠点タイプの取得に失敗しました");
        return;
      }

      try {
        const match = selectedGroupId.match(/_group(\d+)$/);
        const groupIndex = match ? match[1] : null;
        if (!groupIndex) {
          setErrorMessage("グループIDの形式が正しくありません");
          return;
        }
        const groupField = `group${groupIndex}` as keyof Location;

        const selectedLabel = getOptionLabel(selectedGroupId, selectedLocationType);
        if (!selectedLabel) {
          setErrorMessage("拠点タイプの取得に失敗しました");
          return;
        }

        const filtered = agreementFilteredLocations.filter((loc) => {
          return (loc[groupField] ?? "") === selectedLabel;
        });

        setFilteredLocations(filtered);
        setIsFiltered(true);
      } catch (error) {
        console.error("絞り込みエラー:", error);
        setErrorMessage("絞り込み処理中にエラーが発生しました");
      }
    }
  };

  const handleMonthChange = (month: string) => {
    if (!selectedStartYear) return;
    setStartMonth(month);
    setErrorMessage("");
    updatePeriod(selectedStartYear, month);
  };

  const updatePeriod = (year: string, month: string) => {
    if (!year || !month) return;

    const startDate = new Date(Number(year), Number(month) - 1);
    const endDate = new Date(startDate);
    endDate.setMonth(endDate.getMonth() + 11);

    const endYear = String(endDate.getFullYear());
    const endMonth = String(endDate.getMonth() + 1).padStart(2, "0");
    const endFormatted = `${endYear}/${endMonth}`;

    setCondition((prev) => ({
      ...prev,
      period: {
        start: `${year}/${month}`,
        end: `${endYear}/${endMonth}`,
        display: `${year}/${month}-${endYear}/${endMonth}`,
      },
    }));
    setEndOptions([endFormatted]);
  };

  const handleLocationSelect = (id: string) => {
    setSelectedLocationIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  };

  const handleSelectAll = () => {
    if (selectedLocationIds.length === filteredLocations.length) {
      setSelectedLocationIds([]);
    } else {
      setSelectedLocationIds(filteredLocations.map((loc) => loc.id));
    }
  };

  const handleBlur = (field: "startYear" | "startMonth" | "reportType" | "agreementCategory" | "orgId") => {
    const result = ebrcReportCreateSchema.safeParse({
      startYear: selectedStartYear || "",
      startMonth: startMonth || "",
      reportType: condition.reportType || "",
      agreementCategory: fixedAgreementCategory || condition.agreementCategory || "",
      orgId: condition.orgId || "",
    });

    const fieldErrors = result.success ? {} : result.error.flatten().fieldErrors;

    setErrors((prev) => ({
      ...prev,
      [field]: fieldErrors[field]?.length ? fieldErrors[field] : undefined,
    }));
  };

  return (
    <Dialog open={showPopup} onOpenChange={(open) => !open && onClose()} >
      <DialogContent className="flex flex-col w-[800px] h-[90vh]">
        {submitting && (
          <div className="absolute inset-0 bg-opacity-90 flex flex-col items-center justify-center z-50 cursor-not-allowed px-6 text-center">
            <div className="bg-white shadow-lg rounded-lg p-6 max-w-md w-full border border-gray-200">
              <p className="text-gray-800 text-lg font-semibold mb-2">
                CNレポート作成中
                <LoadingDots />
              </p>
              <p className="text-gray-600 text-sm">2～3分ほどかかります、しばらくお待ちください</p>
            </div>
          </div>
        )}
        <DialogTitle className="hidden">

        </DialogTitle>
        <div className="popup-header pt-4 pb-3 px-4 border-b border-gray-200  w-full">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-bold text-gray-800">詳細設定エリア</h3>
          </div>
        </div>
        <div ref={popupContentRef} className="flex-1 overflow-y-auto py-4 px-4">
          <section className={sectionStyle}>
            <h2 className={titleStyle}>1. カルテ作成条件設定（共通）</h2>
            <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />
            {errorMessage && (
              <div className="flex flex-col border border-red-500 rounded  overflow-hidden">
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

            <div className={gridStyle}>
              <div className="space-y-2">
                <label className="font-medium">
                  <span className="required-mark mr-1">必須</span>
                  期間選択（開始）
                </label>
                <div className="flex gap-4">
                  <Select
                    value={selectedStartYear}
                    onValueChange={(value) => handleStartYearChange(value)}
                    onOpenChange={(isOpen) => {
                      if (!isOpen) handleBlur("startYear");
                    }}
                  >
                    <SelectTrigger className={cn("w-32", errors.startYear ? "input-text-error" : "border-gray-300")}>
                      <SelectValue placeholder="年を選択" />
                    </SelectTrigger>
                    <SelectContent position="popper" className="z-[10000]">
                      {years.map((year) => (
                        <SelectItem key={year} value={year}>
                          {year}年
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Select
                    value={startMonth}
                    onValueChange={handleMonthChange}
                    disabled={!selectedStartYear}
                    onOpenChange={(isOpen) => {
                      if (!isOpen) handleBlur("startMonth");
                    }}
                  >
                    <SelectTrigger className={cn("w-32", errors.startMonth ? "input-text-error" : "border-gray-300")}>
                      <SelectValue placeholder="月を選択" />
                    </SelectTrigger>
                    <SelectContent position="popper" className="z-[10000]">
                      {months.map((month) => (
                        <SelectItem key={month} value={month}>
                          {month}月
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {(errors.startYear || errors.startMonth) && (
                  <p className="text-red-500 text-sm font-medium mt-1">
                    {errors.startYear?.[0] ? (
                      <span className="block">{errors.startYear[0]}</span>
                    ) : (
                      errors.startMonth?.[0] && <span className="block">{errors.startMonth[0]}</span>
                    )}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="font-medium">期間選択（終了）</label>
                <Select value={endOptions[0] || ""} disabled>
                  <SelectTrigger>
                    <SelectValue placeholder="終了期間" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[10000]">
                    {endOptions.map((option) => (
                      <SelectItem key={option} value={option}>
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="font-medium">
                  <span className="required-mark mr-1">必須</span>
                  フォーマット選択
                </label>
                <Select
                  value={condition.reportType || ""}
                  onValueChange={(value) => updateCondition({ reportType: value as ReportType })}
                  onOpenChange={(isOpen) => {
                    if (!isOpen) handleBlur("reportType");
                  }}
                >
                  <SelectTrigger className={cn(errors.reportType ? "input-text-error" : "border-gray-300")}>
                    <SelectValue placeholder="選択してください" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[10000]">
                    <SelectItem value={REPORT_TYPES.SIMPLE_CN}>CNカルテ (簡易版)</SelectItem>
                    <SelectItem value={REPORT_TYPES.STANDARD_CN}>CNカルテ (標準版)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-red-500 text-sm font-medium mt-1">{errors.reportType?.[0] || ""}</p>
              </div>

              {/* 同意書取得経路（選択不可） */}
              <div className="space-y-2">
                <label className="font-medium">
                  <span className="required-mark mr-1">必須</span>
                  同意書取得経路
                </label>
                <div className="px-3 py-2 w-full md:w-80 rounded-md border bg-gray-100 text-gray-700">
                  {fixedAgreementCategoryName || fixedAgreementCategory || "-"}
                </div>
                {/* schema 側で必須なら、ここでエラー表示しても OK（UI変えたくないなら空で良い） */}
                <p className="text-red-500 text-sm font-medium mt-1">{errors.agreementCategory?.[0] || ""}</p>
              </div>

              <div className="space-y-2">
                <label className="font-medium">
                  <span className="required-mark mr-1">必須</span>
                  作成組織名
                </label>
                <Select
                  value={condition.orgId || ""}
                  onValueChange={(value) => {
                    const selectedOrg = orgNames.find((org) => org.value === value);
                    updateCondition({
                      orgId: value,
                      orgName: selectedOrg?.label || "",
                    });
                  }}
                  onOpenChange={(isOpen) => {
                    if (!isOpen) handleBlur("orgId");
                  }}
                >
                  <SelectTrigger className={cn(errors.orgId ? "input-text-error" : "border-gray-300")}>
                    <SelectValue placeholder="選択してください" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[10000]">
                    {orgNames.map((name) => (
                      <SelectItem key={name.value} value={name.value}>
                        {name.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-red-500 text-sm font-medium mt-1">{errors.orgId?.[0] || ""}</p>
            </div>

            <div className="w-full">
              <div className="mt-6 space-y-2">
                <label className="font-medium"> (任意)作成する補足資料を選択してください</label>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={condition.downloads.cnKarteCsv}
                      onChange={(e) =>
                        updateCondition({
                          downloads: {
                            ...condition.downloads,
                            cnKarteCsv: e.target.checked,
                          },
                        })
                      }
                      className="accent-black"
                    />
                    <span>レポートバックデータ（csv）</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={condition.downloads.missingData}
                      onChange={(e) =>
                        updateCondition({
                          downloads: {
                            ...condition.downloads,
                            missingData: e.target.checked,
                          },
                        })
                      }
                      className="accent-black"
                    />
                    <span>データ欠損一覧（pdf）</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={condition.downloads.kpi}
                      onChange={(e) =>
                        updateCondition({
                          downloads: {
                            ...condition.downloads,
                            kpi: e.target.checked,
                          },
                        })
                      }
                      className="accent-black"
                    />
                    <span>KPI一覧（csv）</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 複数拠点作成 */}
          <section className={sectionStyle}>
            <div className="flex justify-between items-center mb-4">
              <h2 className={titleStyle}>2-1. 複数拠点カルテ作成</h2>
              <Button
                variant="primary"
                size="third"
                className="gap-1"
                onClick={() => handleCreateAndSave("multi")}
                disabled={
                  submitting ||
                  isConfirmModalOpen ||
                  (!condition.multiCondition?.entireCompany && !condition.multiCondition?.groupOption)
                }
              >
                {submitting && creationType === "multi" ? (
                  <span>作成中...</span>
                ) : (
                  <>
                    {/* <PlusIcon className="h-5 w-5" /> */}
                    <span>カルテ作成</span>
                  </>
                )}
              </Button>
            </div>

            <div className="space-y-4">
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="multiSite"
                    checked={!!condition.multiCondition?.entireCompany}
                    onChange={handleEntireCompanyChange}
                    className="accent-black"
                  />
                  <span>企業全体</span>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="multiSite"
                    checked={!!condition.multiCondition?.groupOption}
                    onChange={handleGroupSelectionChange}
                    className="accent-black"
                  />
                  <span>グループ</span>
                </div>

                <div className={`${!condition.multiCondition?.groupOption ? "opacity-50 pointer-events-none" : ""}`}>
                  {/* 第一グループ */}
                  <div className="mb-6">
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="mb-2 text-xs font-medium">グループ</div>
                        <Select
                          value={g0.groupId}
                          onValueChange={(value) => onChangeGroupId(0, value)}
                          disabled={!condition.multiCondition?.groupOption}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="グループ選択" />
                          </SelectTrigger>
                          <SelectContent position="popper" className="z-[10000]">
                            {agreementFilteredGroups.map((group) => (
                              <SelectItem key={group.id} value={group.id}>
                                {group.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex-1">
                        <div className="mb-2 text-xs font-medium">拠点タイプ</div>
                        <Select
                          value={g0.locationType}
                          onValueChange={(value) => updateGroupItem(0, "locationType", value)}
                          disabled={!g0.groupId}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="拠点選択" />
                          </SelectTrigger>
                          <SelectContent position="popper" className="z-[10000]">
                            {(agreementFilteredGroups.find((g) => g.id === g0.groupId)?.options ?? []).map((opt) => (
                              <SelectItem key={opt.no} value={opt.no}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>

                  {/* AND */}
                  <div className="flex items-center justify-center w-full my-4">
                    <div className="border-t border-gray-300 flex-grow max-w-[160px]" />
                    <span className="mx-4 text-gray-500 whitespace-nowrap">AND</span>
                    <div className="border-t border-gray-300 flex-grow max-w-[160px]" />
                  </div>

                  {/* 第二グループ */}
                  <div className="mb-6">
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="mb-2 text-xs font-medium">グループ</div>
                        <Select
                          value={g1.groupId}
                          onValueChange={(value) => onChangeGroupId(1, value)}
                          disabled={!condition.multiCondition?.groupOption}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="グループ選択" />
                          </SelectTrigger>
                          <SelectContent position="popper" className="z-[10000]">
                            {agreementFilteredGroups.map((group) => (
                              <SelectItem key={group.id} value={group.id}>
                                {group.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex-1">
                        <div className="mb-2 text-xs font-medium">拠点タイプ</div>
                        <Select
                          value={g1.locationType}
                          onValueChange={(value) => updateGroupItem(1, "locationType", value)}
                          disabled={!g1.groupId}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="拠点選択" />
                          </SelectTrigger>
                          <SelectContent position="popper" className="z-[10000]">
                            {(agreementFilteredGroups.find((g) => g.id === g1.groupId)?.options ?? []).map((opt) => (
                              <SelectItem key={opt.no} value={opt.no}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <AlertModal
            className="z-[10000] w-[400px] h-[180px]"
            isOpen={isConfirmModalOpen}
            onClose={() => setIsConfirmModalOpen(false)}
            onConfirm={handleConfirmAction}
            loading={submitting && creationType === "multi"}
            title="カルテ作成の確認"
            description="選択した条件でレポートを作成します。よろしいですか？"
            cancelText="キャンセル"
            continueText="作成する"
          />

          {/* 単拠点作成 */}
          <section className={sectionStyle}>
            <div className="flex justify-between items-center mb-4">
              <h2 className={titleStyle}>2-2. 単拠点カルテ作成</h2>
              <Button
                variant="primary"
                size="third"
                className="gap-1"
                onClick={() => handleCreateAndSave("single")}
                disabled={submitting || selectedLocationIds.length === 0}
              >
                {submitting && creationType === "single" ? (
                  <span>作成中...</span>
                ) : (
                  <>
                    {/* <PlusIcon className="h-5 w-5" /> */}
                    <span>カルテ作成</span>
                  </>
                )}
              </Button>
            </div>

            <span style={{ marginBottom: "8px", display: "inline-block" }}>▼絞り込み条件</span>

            <div className="space-y-6">
              <div className="flex gap-4 items-center flex-wrap">
                <Select value={selectedGroupId} onValueChange={setSelectedGroupId} disabled={isFiltered}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="グループ選択" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[10000]">
                    {agreementFilteredGroups.map((group) => (
                      <SelectItem key={group.id} value={group.id}>
                        {group.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={selectedLocationType}
                  onValueChange={setSelectedLocationType}
                  disabled={!selectedGroupId || isFiltered}
                >
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="拠点選択" />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[10000]">
                    {(agreementFilteredGroups.find((g) => g.id === selectedGroupId)?.options ?? []).map((opt) => (
                      <SelectItem key={opt.no} value={opt.no}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Button
                  onClick={handleFilterToggle}
                  disabled={!selectedGroupId || !selectedLocationType}
                  variant="second"
                  size="primary"
                >
                  {isFiltered ? "解除" : "絞り込み"}
                </Button>
              </div>

              {isFiltered && (
                <div className="p-3 bg-blue-50 rounded-md">
                  現在の絞り込み条件:
                  <span className="font-semibold ml-2">
                    {agreementFilteredGroups.find((g) => g.id === selectedGroupId)?.name} -
                    {
                      agreementFilteredGroups
                        .find((g) => g.id === selectedGroupId)
                        ?.options.find((opt) => opt.no === selectedLocationType)?.label
                    }
                  </span>
                  <span className="ml-4">
                    表示中: {filteredLocations.length}/{agreementFilteredLocations.length} 件
                  </span>
                </div>
              )}

              <div className="max-h-[400px] overflow-y-auto border rounded-md">
                <Table>
                  <TableHeader className="sticky top-0 bg-gray-100 z-10">
                    <TableRow>
                      <TableHead className="sticky top-0 bg-gray-100 z-10">
                        <input
                          type="checkbox"
                          checked={filteredLocations.length > 0 && selectedLocationIds.length === filteredLocations.length}
                          onChange={handleSelectAll}
                          className="accent-green"
                        />
                      </TableHead>
                      <TableHead className="whitespace-nowrap">拠点ID</TableHead>
                      <TableHead className="whitespace-nowrap">拠点名</TableHead>
                      {agreementFilteredGroups.map((group) => (
                        <TableHead className="whitespace-nowrap" key={group.id}>
                          {group.name}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>

                  <TableBody>
                    {filteredLocations.map((location, idx) => (
                      <TableRow key={`${location.id}-${idx}`}>
                        <TableCell>
                          <input
                            type="checkbox"
                            name="locationSelection"
                            checked={selectedLocationIds.includes(location.id)}
                            onChange={() => handleLocationSelect(location.id)}
                            className="accent-green"
                          />
                        </TableCell>
                        <TableCell>{location.id}</TableCell>
                        <TableCell>{location.name}</TableCell>

                        {agreementFilteredGroups.map((group) => {
                          const match = group.id.match(/_group(\d+)$/);
                          const groupIndex = match ? match[1] : null;
                          if (!groupIndex) {
                            return <TableCell key={group.id}>ー</TableCell>;
                          }
                          const groupField = `group${groupIndex}` as keyof Location;

                          const shouldDisplay = location.agreementCategory === group.agreementCategory;
                          const value = shouldDisplay ? location[groupField] || "ー" : "ー";

                          return <TableCell key={group.id}>{value}</TableCell>;
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </section>

          <AlertModal
            className="z-[10000] w-[400px] h-[180px]"
            isOpen={isConfirmModalOpen}
            onClose={() => setIsConfirmModalOpen(false)}
            onConfirm={handleConfirmAction}
            loading={submitting && creationType === "single"}
            title="カルテ作成の確認"
            description="選択した条件でレポートを作成します。よろしいですか？"
            cancelText="キャンセル"
            continueText="作成する"
          />

          <div className="popup-buttons mt-6">
            <Button
              variant="second"
              size="third"
              type="button"
              onClick={() => setIsCloseConfirmOpen(true)}
              className="gap-1"
            >
              <span>キャンセル</span>
            </Button>
          </div>

          <AlertModal
            className="z-[10000] w-[400px] h-[180px]"
            isOpen={isCloseConfirmOpen}
            onClose={() => setIsCloseConfirmOpen(false)}
            onConfirm={() => {
              setIsCloseConfirmOpen(false);
              onClose();
            }}
            title="編集を終了しますか？"
            description="入力中の内容は保存されません。本当に閉じてもよろしいですか？"
            cancelText="続ける"
            continueText="閉じる"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default function CNReportTable() {
  const [reports, setReports] = useState<Report[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [acceptedCondition, setAcceptedCondition] = useState<ReportCreationCondition | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showDownloadConfirm, setShowDownloadConfirm] = useState(false);
  const [acceptedDialogType, setAcceptedDialogType] = useState<AcceptedDialogType>("accepted");
  const [downloadInfo, setDownloadInfo] = useState<{
    filePath: string;
    fileType: "cnKarte" | "missingData" | "kpi";
    format: "pdf" | "csv";
  } | null>(null);

  const [selectedTab, setSelectedTab] = useState<TabName>("CNカルテ");
  const [showReportPopup, setShowReportPopup] = useState(false);
  const [showAcceptedDialog, setShowAcceptedDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");

  const errorTopRef = useScrollToError(errorMessage);
  const location = useLocation();
  const navigate = useNavigate();

  const customerData = location.state?.customerData;
  const corporateNumber = customerData?.corporate_number;

  // route 側 orgId（画面遷移時に state で渡ってくる可能性がある）
  const orgIdFromRouteState = location.state?.orgId ?? "";
  const permission = location.state?.permission ?? 1;

  const [token, setToken] = useState<string | null>(null);
  const [corporateName, setCorporateName] = useState<string | null>(null);

  // ★ CommonLayout の現在選択（これで一覧＆modalを固定）
  const [selectedAgreementCategory, setSelectedAgreementCategory] = useState<string>("");
  const [selectedAgreementCategoryName, setSelectedAgreementCategoryName] = useState<string>("");
  const [selectedConsentOrgId, setSelectedConsentOrgId] = useState<string>("");

  // CommonLayout の cache から agreement_name を引く（label 表示用）
  const resolveAgreementNameFromCache = (corpNo: string | undefined, perm: number, agreementCategory: string) => {
    try {
      if (!corpNo || !agreementCategory) return "";
      const sessionRaw = sessionStorage.getItem("session");
      if (!sessionRaw) return "";
      const sessionObj = JSON.parse(sessionRaw);
      const userId = sessionObj?.authorityInfo?.user_id ?? "unknownUser";
      const orgIdForKey = sessionObj?.authorityInfo?.org_id ?? "unknownOrg";
      const sessionId = sessionObj?.session_id ?? "noSessionId";
      const keyPrefix = `${sessionId}:${userId}:${orgIdForKey}:${perm}`;
      const cacheKey = `consentOptions:${keyPrefix}:${corpNo}`;
      const cached = sessionStorage.getItem(cacheKey);
      if (!cached) return "";
      const rows = JSON.parse(cached) as { agreement_category: string; agreement_name: string }[];
      const hit = rows.find((r) => r.agreement_category === agreementCategory);
      return hit?.agreement_name ?? "";
    } catch {
      return "";
    }
  };

  // CommonLayout の pulldown 変更を受けて、selectedAgreementCategory と selectedConsentOrgId を更新する
  useEffect(() => {
    const handler = (e: Event) => {
      const ce = e as CustomEvent<{
        permission: number;
        corporateNumber?: string;
        agreementCategory: string;
        orgId: string;
      }>;

      const nextCat = ce.detail?.agreementCategory ?? "";
      const nextOrg = ce.detail?.orgId ?? "";

      setSelectedAgreementCategory(nextCat);
      setSelectedConsentOrgId(nextOrg);

      const name = resolveAgreementNameFromCache(corporateNumber, permission, nextCat);
      setSelectedAgreementCategoryName(name || nextCat);
    };

    window.addEventListener(CONSENT_CHANGED_EVENT, handler as EventListener);
    return () => window.removeEventListener(CONSENT_CHANGED_EVENT, handler as EventListener);
  }, [corporateNumber, permission]);

  useEffect(() => {
    const sessionData = sessionStorage.getItem("session");
    if (!sessionData) return;
    const corporateData = sessionStorage.getItem("corporateData");
    if (!corporateData) return;
    try {
      const session = JSON.parse(sessionData);
      setToken(session.token);

      const corporate = JSON.parse(corporateData);
      setCorporateName(corporate.company_name);
    } catch (e) {
      console.error("Error parsing session data:", e);
    }
  }, []);

  const resolveKyotenSelect = (buildingId: unknown): "全体" | "グループ" | "個別" => {
    if (buildingId === null || buildingId === undefined) return "個別";
    const v = String(buildingId);
    if (v === "0") return "全体";
    if (v === "1") return "グループ";
    return "個別";
  };

  const fmtYmRangePlus11 = (fromYm: string | undefined | null) => {
    const s = String(fromYm ?? "");
    if (!/^\d{6}$/.test(s)) return "-";
    const y = parseInt(s.slice(0, 4), 10);
    const m = parseInt(s.slice(4, 6), 10);
    if (isNaN(y) || isNaN(m)) return "-";

    const startY = String(y);
    const startM = String(m).padStart(2, "0");

    const endDate = new Date(y, m - 1 + 11, 1);
    const endY = String(endDate.getFullYear());
    const endM = String(endDate.getMonth() + 1).padStart(2, "0");

    return `${startY}/${startM}-${endY}/${endM}`;
  };

  const translateReportTypeIntoText = (reportType: 1 | 0 | string): string => {
    if (reportType == 0) return "CNカルテ(簡易版)";
    if (reportType == 1) return "CNカルテ(標準版)";
    return String(reportType);
  };

  //ステータス変換関数
  const resolveCnReportStatus = (status?: string, queueNo?: string | number | null): React.ReactNode => {
    const normalizedQueueNo =
      queueNo !== null && queueNo !== undefined && queueNo !== "" ? String(Math.floor(Number(queueNo))) : "-";

    switch (status) {
      case "0":
        return (
          <span className="text-red-600">
            作成中
            <br />
            (待ち{normalizedQueueNo})
          </span>
        );
      case "1":
        return "作成済";
      case "9":
        return <span className="text-red-600">エラー</span>;
      default:
        return "未作成";
    }
  };

  // レポート一覧取得
  const fetchReports = async () => {
    try {
      const orgId = selectedConsentOrgId || orgIdFromRouteState;
      const agreementCategory = fixedAgreementCategory;

      if (!token || !corporateNumber || !orgId || !agreementCategory) return;
      setLoading(true);

      let url = `/api/report/cn-karte/visual/list?corporate_number=${corporateNumber}&org_id=${orgId}`;
      if (agreementCategory) {
        url += `&agreement_category=${agreementCategory}`;
      }

      const raw = await getData(url);
      const data = Array.isArray(raw.cn_karte_list) ? raw.cn_karte_list : [];

      const sortedData: Report[] = data
        .sort((a: any, b: any) => new Date(b.report_created_at).getTime() - new Date(a.report_created_at).getTime())
        .map((item: any, index: number) => {
          const cnPdfStatus = resolveCnReportStatus(item.report_status, item.queue_no);
          return {
            conditionId: `report-${item.id || index}`,
            period: {
              display: fmtYmRangePlus11(item.report_selection_period_from),
            },
            reportType: item.format_type || "未設定",
            targetType: resolveKyotenSelect(item.building_id),
            createdDate: item.report_created_at ? item.report_created_at.split(/[ T]/)[0].replace(/-/g, "/") : "",
            agreementCategory: item.agreement_name || item.agreement_category,
            orgName: item.org_name || "不明",
            author: item.report_created_by || "不明",
            group1: item.group1 || null,
            group2: item.group2 || null,
            group3: item.group3 || null,
            group4: item.group4 || null,
            group5: item.group5 || null,
            pdf: item.cn_pdf || "",
            csv: item.cn_csv || "",
            loss_pdf: item.data_loss_pdf || "",
            kpi_csv: item.kpi_csv || "",
            cnKarte: {
              pdfStatus: cnPdfStatus,
              pdfPath: item.cn_pdf || "",
              csv: !!item.cn_csv,
            },
            missingData: {
              pdf: !!item.data_loss_pdf,
            },
            kpi: {
              csv: !!item.kpi_csv,
            },
            status: item.cn_pdf || item.cn_csv || item.data_loss_pdf || item.kpi_csv ? "作成済" : "未作成",
            report_save_path: item.cn_pdf || item.cn_csv || item.data_loss_pdf || item.kpi_csv || "",
            building_id: item.building_id || null,
            building_name: item.location_identifier_name || "",
            report_status: item.report_status,
            queue_no: item.queue_no ? String(parseInt(item.queue_no, 10)) : "",
            report_selection_period_from: item.report_selection_period_from,
            format_type: item.format_type,
            createdTime: item.report_created_at ? item.report_created_at.split(/[ T]/)[1].match(/^\d{2}:\d{2}/)?.[0] || "" : "",
          };
        });
      setReports(sortedData);
      setError("");
    } catch (err: any) {
      setErrorMessage(err.data?.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // token + org + agreementCategory が揃ったら都度更新
  useEffect(() => {
    const orgId = selectedConsentOrgId || orgIdFromRouteState;
    if (!token || !orgId) {
      setLoading(false);
      return;
    }
    fetchReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedConsentOrgId, orgIdFromRouteState, selectedAgreementCategory]);

  const handleSaveReport = async () => {
    await fetchReports();
    setShowReportPopup(false);
  };

  const StatusCell = ({
    status,
    filePath,
    fileType,
    format,
    onProcessingClick,
  }: {
    status: React.ReactNode;
    filePath: string;
    fileType: "cnKarte" | "missingData" | "kpi";
    format: "pdf" | "csv";
    onProcessingClick?: () => void;
  }) => {
    if (fileType === "missingData" && format !== "pdf") return null;
    if (fileType === "kpi" && format !== "csv") return null;

    const handleClick = (e: React.MouseEvent) => {
      e.preventDefault();
      setDownloadInfo({ filePath, fileType, format });
      setShowDownloadConfirm(true);
    };

    if (status === "作成済") {
      return (
        <button
          type="button"
          onClick={handleClick}
          className="text-blue-600 underline hover:text-blue-800 bg-transparent p-0 border-0"
        >
          {status}
        </button>
      );
    }

    // 作成中
    if (onProcessingClick) {
      return (
        <button
          type="button"
          onClick={onProcessingClick}
          className="text-red-600 bg-transparent p-0 border-0 text-left"
        >
          {status}
        </button>
      );
    }

    // それ以外
    return <span className="text-gray-500">{status}</span>;
  };

  const columns = useMemo(
    () => [
      {
        accessorKey: "period.display",
        header: () => <div className="text-xs">選択期間</div>,
        size: 100,
        cell: ({ row }: any) => <div className="text-xs  text-left whitespace-nowrap">{row.original.period.display}</div>,
      },
      {
        accessorKey: "reportType",
        header: () => <div className="text-xs">フォーマット</div>,
        size: 110,
        cell: ({ row }: any) => (
          <div className="text-xs whitespace-nowrap">{translateReportTypeIntoText(row.original.reportType)}</div>
        ),
      },
      {
        accessorKey: "targetType",
        header: () => <div className="text-xs">拠点選択</div>,
        size: 110,
        cell: ({ row }: { row: { original: Report } }) => {
          const label = row.original.targetType;
          if (label === "個別") {
            const buildingName = row.original.building_name || "";
            return <div className="text-xs whitespace-nowrap">{buildingName}</div>;
          }
          return <div className="text-xs whitespace-nowrap">{label}</div>;
        },
      },
      {
        id: "cnReport",
        header: () => (
          <div className="flex justify-between text-xs">
            <div>CNレポート</div>
            <div className="h-full cursor-col-resize bg-gray-300 hover:bg-gray-400 transition" />
          </div>
        ),
        columns: [
          {
            id: "cnKartePdf",
            header: () => <div className="text-xs">PDF</div>,
            size: 60,
            meta: {
              className: "text-left w-[60px] whitespace-nowrap text-xs",
            },
            cell: ({ row }) => {
              const original = row.original;

              // 「作成中」クリック時の処理
              const handleProcessingClick = () => {
                const ym = original.report_selection_period_from;

                const startYear = ym?.slice(0, 4) ?? "";
                const startMonth = ym?.slice(4, 6) ?? "";

                setAcceptedCondition({
                  period: {
                    start: `${startYear}/${startMonth}`,
                    end: original.period.display.split("-")[1] ?? "",
                    display: original.period.display,
                  },
                  reportType:
                    original.format_type === "CNカルテ(簡易版)" ? REPORT_TYPES.SIMPLE_CN : REPORT_TYPES.STANDARD_CN,
                });

                setAcceptedDialogType("creating");
                setShowAcceptedDialog(true);
              };

              return (
                <div className="text-xs w-[60px] !text-left [&_*]:!justify-start">
                  <StatusCell
                    status={original.cnKarte.pdfStatus}
                    filePath={original.cnKarte.pdfPath}
                    fileType="cnKarte"
                    format="pdf"
                    onProcessingClick={original.report_status === "0" ? handleProcessingClick : undefined}
                  />
                </div>
              );
            },
          },
          {
            id: "cnKarteCsv",
            header: () => <div className="text-xs">CSV</div>,
            size: 60,
            cell: ({ row }: any) => (
              <div className="text-xs w-[60px] !text-left [&_*]:!justify-start">
                <StatusCell
                  status={
                    row.original.report_status === "0" || row.original.report_status === "9"
                      ? "未作成"
                      : row.original.cnKarte.csv
                        ? "作成済"
                        : "未作成"
                  }
                  filePath={row.original.csv || ""}
                  fileType="cnKarte"
                  format="csv"
                />
              </div>
            ),
            meta: { className: "text-left w-[60px] whitespace-nowrap text-xs" },
          },
        ],
      },
      {
        id: "missingData",
        header: () => <div className="text-xs">データ欠損一覧</div>,
        columns: [
          {
            id: "missingDataPdf",
            header: () => <div className="text-xs">PDF</div>,
            size: 60,
            cell: ({ row }: any) => (
              <div className="text-xs w-[60px] !text-left [&_*]:!justify-start">
                <StatusCell
                  status={
                    row.original.report_status === "0" || row.original.report_status === "9"
                      ? "未作成"
                      : row.original.cnKarte.csv
                        ? "作成済"
                        : "未作成"
                  }
                  filePath={row.original.loss_pdf || ""}
                  fileType="missingData"
                  format="pdf"
                />
              </div>
            ),
          },
        ],
      },
      {
        id: "kpi",
        header: () => <div className="text-xs">KPI一覧</div>,
        columns: [
          {
            id: "kpiCsv",
            size: 60,
            header: () => <div className="text-xs">CSV</div>,
            cell: ({ row }: any) => (
              <div className="text-xs w-[60px] !text-left [&_*]:!justify-start">
                <StatusCell
                  status={
                    row.original.report_status === "0" || row.original.report_status === "9"
                      ? "未作成"
                      : row.original.cnKarte.csv
                        ? "作成済"
                        : "未作成"
                  }
                  filePath={row.original.kpi_csv || ""}
                  fileType="kpi"
                  format="csv"
                />
              </div>
            ),
          },
        ],
      },
      ...GROUP_KEYS.map((groupKey: GroupKey, index) => ({
        header: () => (
          <div className="text-center whitespace-nowrap text-xs">{groups[index]?.name || `グループ${index + 1}`}</div>
        ),
        id: `group-${groupKey}`,
        size: 110,
        cell: ({ row }: { row: { original: Report } }) => {
          if (row.original.targetType === "全体") {
            return <div className="whitespace-nowrap text-xs">全体</div>;
          }
          const groupValue = row.original[groupKey] ?? null;
          return <div className="whitespace-nowrap text-xs">{groupValue || "ー"}</div>;
        },
      })),
      {
        accessorKey: "agreementCategory",
        header: () => <div className="text-xs">同意書取得経路</div>,
        size: 130,
        cell: ({ row }: any) => <div className="text-xs text-left whitespace-nowrap">{row.original.agreementCategory}</div>,
      },
      {
        accessorKey: "orgName",
        header: () => <div className="w-full w-[20px] text-xs">作成組織名</div>,
        cell: ({ row }: any) => <div className="text-xs whitespace-nowrap">{row.original.orgName}</div>,
      },
      {
        accessorKey: "createdDate",
        header: () => <div className="text-xs">作成年月日</div>,
        size: 60,
        cell: ({ row }: any) => <div className="text-xs w-[60px] whitespace-nowrap">{row.original.createdDate}</div>,
      },
      {
        accessorKey: "createdTime",
        header: () => <div className="text-xs">作成時間</div>,
        size: 50,
        cell: ({ row }: any) => <div className="text-xs w-[50px] whitespace-nowrap">{row.original.createdTime}</div>,
      },
      {
        accessorKey: "author",
        header: () => <div className="text-xs">作成者</div>,
        size: 80,
        cell: ({ row }: any) => (
          <div className="text-xs text-left w-auto inline-block whitespace-nowrap">{row.original.author}</div>
        ),
      },
    ],
    [groups],
  );

  const breadcrumbItems = [
    { title: "レポート作成・管理", link: "/", className: "color-green-primar" },
    { title: "○○株式会社", link: "" },
  ];

  const rawDownload = async (path: string, fallbackName = "download") => {
    try {
      const response = await getData(path, { Authorization: `Bearer ${token}` });

      const blob = await response.blob();

      let fileName = fallbackName;
      const cd = response.headers.get("content-disposition");
      if (cd) {
        const m = /filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i.exec(cd);
        fileName = decodeURIComponent(m?.[1] || m?.[2] || fileName);
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      console.error("Download error:", error);
      setErrorMessage(error.data?.message);
    }
  };

  const fixedAgreementCategory = selectedAgreementCategory || "";
  const fixedAgreementCategoryName = selectedAgreementCategoryName || fixedAgreementCategory;

  return (
    <CommonLayout
      selectedTab={selectedTab}
      onTabChange={setSelectedTab}
      breadcrumbItems={breadcrumbItems}
      permission={permission}
    >
      <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />

      {errorMessage && (
        <div
          ref={errorTopRef as React.RefObject<HTMLDivElement>}
          className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden mt-5 ml-16 scroll-mt-[300px]"
        >
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
              <div className="text-[#d92d20] text-[14px] font-normal leading-[21px] text-left whitespace-nowrap">
                {errorMessage}
              </div>
            )}
          </div>
        </div>
      )}

      {selectedTab === "CNカルテ" && (
        <div className=" ml-16 mr-16 py-4 pt-8 max-w-full">
          {error && <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">{error}</div>}

          <div className="mb-6 flex justify-end items-center gap-3">
            <Button variant="primary" className="gap-2 flex items-center" onClick={fetchReports}>
              画面の更新
            </Button>

            <Button
              variant="primary"
              //size="primary"
              className="gap-3 flex items-center"
              onClick={() => setShowReportPopup(true)}
              disabled={saving}
            >
              {saving ? (
                <span>保存中...</span>
              ) : (
                <>
                  {/* <PlusIcon className="h-5 w-5" /> */}
                  <span>カルテ作成</span>
                </>
              )}
            </Button>
          </div>

          {showDownloadConfirm && downloadInfo && (
            <div className="popup-overlay">
              <div className="popup-content max-w-md">
                <div className="popup-title">ダウンロード確認</div>
                <div className="p-6">
                  <p className="mb-4">ファイルをダウンロードしますか？</p>
                  <div className="bg-gray-50 p-4 rounded-md mb-6">
                    <p className="font-medium">
                      {downloadInfo.fileType === "cnKarte" && "CNレポート"}
                      {downloadInfo.fileType === "missingData" && "データ欠損一覧"}
                      {downloadInfo.fileType === "kpi" && "KPI一覧"} -{downloadInfo.format.toUpperCase()}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      レポートID: {downloadInfo.filePath.replace(/\\/g, "/").split("/").pop()}
                    </p>
                  </div>
                  <div className="flex justify-end gap-3">
                    <Button
                      variant="second"
                      size="third"
                      type="button"
                      onClick={() => setShowDownloadConfirm(false)}
                      className="gap-1"
                    >
                      <span>キャンセル</span>
                    </Button>
                    <Button
                      variant="primary"
                      size="third"
                      className="gap-1"
                      onClick={async () => {
                        rawDownload(
                          `/api/file/file-download?file_path=${encodeURIComponent(downloadInfo.filePath)}`,
                          "report",
                        );
                        setShowDownloadConfirm(false);
                      }}
                    >
                      <span>ダウンロード</span>
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {loading ? (
            <div className="p-4 flex justify-center items-center text-gray-500 text-sm">
              <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin mr-2" />
              読み込み中...
            </div>
          ) : (
            <div className="allow-x-scroll w-full max-w-full overflow-x-auto">
              <div className="min-w-max border-collapse">
                <PageableTable<Report, unknown>
                  columns={columns as any}
                  data={reports}
                  pageCount={1}
                  totalCount={reports.length}
                  pageSizeOptions={[5, 10, 20, 50]}
                />
              </div>
            </div>
          )}

          {showReportPopup && (
            <ReportCreationPopup
              showPopup={showReportPopup}
              onClose={() => setShowReportPopup(false)}
              onAccepted={() => {
                setShowReportPopup(false);
                setShowAcceptedDialog(true);
              }}
              onSave={handleSaveReport}
              setAcceptedCondition={setAcceptedCondition}
              corporateNumber={corporateNumber}
              orgName={customerData?.org_name ?? ""}
              // 一覧は CommonLayout の “同意書取得組織” を使う想定なので、その orgId を優先
              orgId={selectedConsentOrgId || orgIdFromRouteState || ""}
              fixedAgreementCategory={fixedAgreementCategory}
              fixedAgreementCategoryName={fixedAgreementCategoryName}
            />
          )}

          <CustomDialog
            title=" "
            open={showAcceptedDialog}
            onOpenChange={setShowAcceptedDialog}
            size="default"
            className="w-[600px] h-[380px]"
            footer={
              <div className="flex justify-center w-full">
                <Button variant="primary" onClick={() => setShowAcceptedDialog(false)}>
                  OK
                </Button>
              </div>
            }
          >
            <div className="flex flex-col items-center text-center gap-3 py-6">
              <span className="text-base">
                {acceptedDialogType === "creating"
                  ? Messages.energy_building.ebrc01.cn_karte_creating
                  : Messages.energy_building.ebrc01.create_request_accepted}
              </span>
              <div></div>
              {acceptedCondition && (
                <div className="text-center space-y-2">
                  <div>
                    <span className="text-base">お客さま名：</span>
                    {corporateName}
                  </div>
                  <div>
                    <span className="text-base">選択期間：</span>
                    {acceptedCondition.period.display}
                  </div>
                  <div>
                    <span className="text-base">フォーマット：</span>
                    {acceptedCondition.reportType === REPORT_TYPES.SIMPLE_CN
                      ? "CNカルテ（簡易版）"
                      : "CNカルテ（標準版）"}
                  </div>
                </div>
              )}
              <div></div>
              <span className="text-base text-red-600 leading-relaxed">
                {Messages.energy_building.ebrc06.create_request_note}
              </span>
            </div>
          </CustomDialog>
        </div>
      )}
    </CommonLayout>
  );
}
