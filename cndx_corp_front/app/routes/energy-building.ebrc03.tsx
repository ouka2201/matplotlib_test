// ebrc03.tsx
// import { MetaFunction } from "@remix-run/node";
import React, { FC, Fragment, useCallback, useEffect, useMemo, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { FormProvider, useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import type { BreadCrumbType } from "~/components/common/breadcrumb";
import MasterFormField from "~/components/common/master-form-field";
// import MasterLayout from "~/components/layout/master-layout";
import ErrorHint from "~/components/common/error-hint";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Messages } from "~/constants/messages/message";
import { getData, postData } from "~/lib/fetch";
import "~/styles/CNTable.css";
// import popupStyles from "~/styles/popup.css";
import { useEbConsentSelection } from "~/hooks/useEbConsentSelection";
import { useRoleFlags } from "~/hooks/useRoleFlags";
import { useScrollToError } from "~/hooks/useScrollToError";
import { cn } from "~/lib/utils";
import { IndustryInput, industrySchema } from "~/lib/validations/ebrc";
import CommonLayout from "../components/CommonLayout";
import { TabName } from "../components/tab-navigator";
import { saveSuccessToast } from "../components/ui/use-toast";

// export const meta: MetaFunction = () => {
//   return [{ title: "レポート管理画面_企業詳細_お客さま基本情報画面" }, { name: "ebrc03", content: "ebrc03" }];
// };

interface CustomerCompanyList {
  company_address: string;
  company_name: string;
  company_name_kana: string;
  corporate_number: string;
}

interface LocationState {
  customerData: CustomerCompanyList;
  mode: string;
  dataSource?: string;
  agreementCategory?: string;
  orgId?: string;
  permission?: number;
}

interface CustomerProfile {
  agreement_category: string;
  agreement_name: string;
  company_name: string;
  corporate_number: string | null;
  company_address: string;
  business_office_count: string;
  industry_class_major_name: string;
  industry_class_middle_name: string;
  industry_class_minor_name: string;
  industry_class_detail_name: string;
  org_id: string;
}

interface CompanyAgreement {
  agreement_category: string;
  agreement_name: string;
  company_name: string;
  corporate_number: string;
  company_address: string;
  business_office_count: string;
  industry_class_major_name: string;
  industry_class_middle_name: string;
  industry_class_minor_name: string;
  industry_class_detail_name: string;
  org_id: string;
}

interface CompanyDataState {
  agreements: CompanyAgreement[];
  selectedAgreement: CompanyAgreement | null;
}

// スタイル定数
const sectionStyle = "p-6 bg-white rounded-xl shadow border border-gray-200 mb-6";
const titleStyle = "text-lg font-bold mb-4 text-blue-800 border-b pb-2";

type IndustryOptionType = {
  code: string;
  text: string;
  children?: IndustryOptionType[];
};

type InnerProps = {
  // ctx 追従で必要
  companyData: CompanyDataState;
  applySelection: (cat: string, orgId?: string) => void;

  // 表示・操作に必要（外側ロジックをそのまま使う）
  selectedTab: TabName;
  isVis: boolean;
  isEditing: boolean;
  saving: boolean;
  loading: boolean;

  errorMessage: string | string[];
  errorTopRef: React.RefObject<HTMLDivElement>;

  methods: UseFormReturn<CustomerProfile>;
  handleSubmit: UseFormReturn<CustomerProfile>["handleSubmit"];
  control: UseFormReturn<CustomerProfile>["control"];

  corporateData: {
    company_name: string;
    corporate_number: string;
    company_address: string;
  } | null;

  errors: {
    major?: string;
    middle?: string;
    minor?: string;
    detail?: string;
  };

  toggleEditMode: () => void;
  handleCancelEdit: () => void;
  handleSaveProfile: (data: CustomerProfile) => Promise<void>;

  // 産業分類 UI
  rootIndustries: IndustryOptionType[];
  optionsB: IndustryOptionType[];
  optionsC: IndustryOptionType[];
  optionsD: IndustryOptionType[];
  selectedA: IndustryOptionType | null;
  selectedB: IndustryOptionType | null;
  selectedC: IndustryOptionType | null;
  selectedD: IndustryOptionType | null;
  setIsManualSelection: React.Dispatch<React.SetStateAction<boolean>>;
  setSelectedA: React.Dispatch<React.SetStateAction<IndustryOptionType | null>>;
  setSelectedB: React.Dispatch<React.SetStateAction<IndustryOptionType | null>>;
  setSelectedC: React.Dispatch<React.SetStateAction<IndustryOptionType | null>>;
  setSelectedD: React.Dispatch<React.SetStateAction<IndustryOptionType | null>>;
  setErrors: React.Dispatch<
    React.SetStateAction<{
      major?: string;
      middle?: string;
      minor?: string;
      detail?: string;
    }>
  >;

  // 権限フラグ
  isEpAdmin: boolean;
  isEpGeneral: boolean;
  isBank: boolean;
  isBranchAdmin: boolean;
  isBranchGeneral: boolean;
  isRepAdmin: boolean;
  isRepGeneral: boolean;
  isTcsAdmin: boolean;
  isTcsGeneral: boolean;
};

const CustomerProfileInner: FC<InnerProps> = (p) => {
  // ★ここは CommonLayout の Provider の「子」なので ctx が取れる
  const { agreementCategory, orgId } = useEbConsentSelection();

  // CommonLayout のプルダウン値に追従する
  useEffect(() => {
    if (!agreementCategory) return;
    if (p.companyData.agreements.length === 0) return;
    p.applySelection(agreementCategory, orgId || "");
  }, [agreementCategory, orgId, p.companyData.agreements, p.applySelection]);

  // 権限判定（旧 handleConsentPathChange の代替）
  const canEditByConsentPath = () => {
    if (agreementCategory === "01") {
      return p.isEpAdmin || p.isEpGeneral || p.isBank || p.isBranchAdmin || p.isBranchGeneral || p.isTcsAdmin || p.isTcsGeneral;
    }
    if (agreementCategory === "02") {
      return p.isEpAdmin || p.isEpGeneral || p.isRepAdmin || p.isRepGeneral || p.isTcsAdmin || p.isTcsGeneral;
    }
    return true;
  };

  const handleBlur = (field: keyof IndustryInput) => {
    const result = industrySchema.safeParse({
      major: p.selectedA?.code || "",
      middle: p.selectedB?.code || "",
      minor: p.selectedC?.code || "",
      detail: p.selectedD?.code || "",
    });

    const fieldErrors = result.success ? {} : result.error.flatten().fieldErrors;

    p.setErrors((prev) => ({
      ...prev,
      [field]: fieldErrors[field]?.[0],
    }));
  };

  const handleSelect = (level: "A" | "B" | "C" | "D", value: string, options: IndustryOptionType[]) => {
    p.setIsManualSelection(true);
    const selected = options.find((o) => o.code === value) || null;

    switch (level) {
      case "A":
        p.setSelectedA(selected);
        p.setSelectedB(null);
        p.setSelectedC(null);
        p.setSelectedD(null);
        p.setErrors((prev) => ({ ...prev, major: selected ? "" : prev.major }));
        break;
      case "B":
        p.setSelectedB(selected);
        p.setSelectedC(null);
        p.setSelectedD(null);
        p.setErrors((prev) => ({ ...prev, middle: selected ? "" : prev.middle }));
        break;
      case "C":
        p.setSelectedC(selected);
        p.setSelectedD(null);
        p.setErrors((prev) => ({ ...prev, minor: selected ? "" : prev.minor }));
        break;
      case "D":
        p.setSelectedD(selected);
        p.setErrors((prev) => ({ ...prev, detail: selected ? "" : prev.detail }));
        break;
    }
  };

  const optionsA = p.rootIndustries;

  return (
    <>
      <div ref={p.errorTopRef as React.RefObject<HTMLDivElement>} />
      {p.errorMessage && (
        <div ref={p.errorTopRef as React.RefObject<HTMLDivElement>} className="mt-5 ml-16 w-4/5 scroll-mt-[300px]">
          <ErrorHint message={p.errorMessage} bodyClassName="py-4" />
        </div>
      )}

      {p.selectedTab === "お客さま基本情報" && (
        <div className="table-container">
          <div className="mr-16 ml-16 pt-8 whitespace-nowrap">
            {!p.isVis && (
              <div className="mb-6 flex justify-end">
                {p.isEditing ? (
                  <div className="flex space-x-2">
                    <Button
                      variant="secondary"
                      size="default"
                      className="gap-2 border-none"
                      onClick={p.handleCancelEdit}
                      disabled={p.saving}
                    >
                      {/* <X className="h-5 w-5" /> */}
                      <span>キャンセル</span>
                    </Button>
                    <Button
                      variant="primary"
                      size="default"
                      className="gap-2"
                      onClick={p.handleSubmit(p.handleSaveProfile)}
                      disabled={p.saving}
                    >
                      {/* <Save className="h-5 w-5" /> */}
                      <span>登録</span>
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="primary"
                    size="default"
                    className={`gap-2 border-none ${!canEditByConsentPath() ? "opacity-50 cursor-not-allowed" : ""}`}
                    onClick={p.toggleEditMode}
                    disabled={!canEditByConsentPath()}
                  >
                    {/* <Pencil className="h-5 w-5" /> */}
                    <span>編集</span>
                  </Button>
                )}
              </div>
            )}

            {p.loading ? (
              <div className="text-center py-10">
                <p>データを読み込み中です...</p>
              </div>
            ) : (
              <FormProvider {...p.methods}>
                <form onSubmit={p.handleSubmit(p.handleSaveProfile)}>
                  <Card className={sectionStyle}>
                    <CardHeader>
                      <CardTitle className={titleStyle}>
                        {p.companyData.selectedAgreement?.company_name || p.corporateData?.company_name || ""}
                      </CardTitle>
                    </CardHeader>

                    <CardContent className={`flex flex-col gap-0`}>
                      <MasterFormField
                        control={p.control}
                        name="company_name"
                        label="お客さま名"
                        required={true}
                        isEditing={false}
                      />

                      <MasterFormField
                        control={p.control}
                        name="corporate_number"
                        label="法人番号"
                        placeholder="法人番号"
                        isEditing={false}
                        renderCustom={(field) => <input {...field} readOnly />}
                      />

                      <MasterFormField
                        control={p.control}
                        name="company_address"
                        label="本社所在地"
                        placeholder="本社所在地"
                        required={true}
                        isEditing={false}
                      />

                      <MasterFormField
                        control={p.control}
                        name="business_office_count"
                        label="拠点数"
                        placeholder="拠点数を入力"
                        required={true}
                        isEditing={false}
                      />

                      {!p.isEditing && (
                        <Fragment>
                          <MasterFormField
                            control={p.control}
                            name="industry_class_major_name"
                            label="産業分類（大分類）"
                            required={true}
                            isEditing={false}
                          />
                          <MasterFormField
                            control={p.control}
                            name="industry_class_middle_name"
                            label="産業分類（中分類）"
                            required={true}
                            isEditing={false}
                          />
                          <MasterFormField
                            control={p.control}
                            name="industry_class_minor_name"
                            label="産業分類（小分類）"
                            required={true}
                            isEditing={false}
                          />
                          <MasterFormField
                            control={p.control}
                            name="industry_class_detail_name"
                            label="産業分類（細分類）"
                            required={true}
                            isEditing={false}
                          />
                        </Fragment>
                      )}

                      {p.isEditing && (
                        <Fragment>
                          <div className="mt-6 flex flex-col gap-6">
                            {/* Select A */}
                            <div className="flex flex-col gap-2">
                              <div>
                                <span className="text-[#8893ac]">産業分類（大分類）</span>
                                <span className="required-mark">必須</span>
                              </div>
                              <Select
                                value={p.selectedA?.code || ""}
                                onValueChange={(value) => handleSelect("A", value, optionsA)}
                                onOpenChange={(isOpen) => {
                                  if (!isOpen) handleBlur("major");
                                }}
                              >
                                <SelectTrigger className={cn(p.errors.major ? "input-text-error" : "border-gray-300")}>
                                  <SelectValue placeholder="選択してください" />
                                </SelectTrigger>
                                <SelectContent position="popper" className="z-[10000]">
                                  {optionsA.map((opt) => (
                                    <SelectItem key={opt.code} value={opt.code}>
                                      {opt.text}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {p.errors.major && <p className="text-red-500 text-sm font-medium mt-1">{p.errors.major}</p>}
                            </div>

                            {/* Select B */}
                            <div className="flex flex-col gap-2">
                              <div>
                                <span className="text-[#8893ac]">産業分類（中分類）</span>
                                <span className="required-mark">必須</span>
                              </div>
                              <Select
                                value={p.selectedB?.code || ""}
                                onValueChange={(value) => handleSelect("B", value, p.optionsB)}
                                onOpenChange={(isOpen) => {
                                  if (!isOpen) handleBlur("middle");
                                }}
                                disabled={p.optionsB.length === 0}
                              >
                                <SelectTrigger className={cn(p.errors.middle ? "input-text-error" : "border-gray-300")}>
                                  <SelectValue placeholder="選択してください" />
                                </SelectTrigger>
                                <SelectContent position="popper" className="z-[10000]">
                                  {p.optionsB.map((opt) => (
                                    <SelectItem key={opt.code} value={opt.code}>
                                      {opt.text}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {p.errors.middle && (
                                <p className="text-red-500 text-sm font-medium mt-1">{p.errors.middle}</p>
                              )}
                            </div>

                            {/* Select C */}
                            <div className="flex flex-col gap-2">
                              <div>
                                <span className="text-[#8893ac]">産業分類（小分類）</span>
                                <span className="required-mark">必須</span>
                              </div>
                              <Select
                                value={p.selectedC?.code || ""}
                                onValueChange={(value) => handleSelect("C", value, p.optionsC)}
                                onOpenChange={(isOpen) => {
                                  if (!isOpen) handleBlur("minor");
                                }}
                                disabled={p.optionsC.length === 0}
                              >
                                <SelectTrigger className={cn(p.errors.minor ? "input-text-error" : "border-gray-300")}>
                                  <SelectValue placeholder="選択してください" />
                                </SelectTrigger>
                                <SelectContent position="popper" className="z-[10000]">
                                  {p.optionsC.map((opt) => (
                                    <SelectItem key={opt.code} value={opt.code}>
                                      {opt.text}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {p.errors.minor && <p className="text-red-500 text-sm font-medium mt-1">{p.errors.minor}</p>}
                            </div>

                            {/* Select D */}
                            <div className="flex flex-col gap-2">
                              <div>
                                <span className="text-[#8893ac]">産業分類（細分類）</span>
                                <span className="required-mark">必須</span>
                              </div>
                              <Select
                                value={p.selectedD?.code || ""}
                                onValueChange={(value) => handleSelect("D", value, p.optionsD)}
                                onOpenChange={(isOpen) => {
                                  if (!isOpen) handleBlur("detail");
                                }}
                                disabled={p.optionsD.length === 0}
                              >
                                <SelectTrigger className={cn(p.errors.detail ? "input-text-error" : "border-gray-300")}>
                                  <SelectValue placeholder="選択してください" />
                                </SelectTrigger>
                                <SelectContent position="popper" className="z-[10000]">
                                  {p.optionsD.map((opt) => (
                                    <SelectItem key={opt.code} value={opt.code}>
                                      {opt.text}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {p.errors.detail && (
                                <p className="text-red-500 text-sm font-medium mt-1">{p.errors.detail}</p>
                              )}
                            </div>
                          </div>
                        </Fragment>
                      )}
                    </CardContent>
                  </Card>
                </form>
              </FormProvider>
            )}
          </div>
        </div>
      )}
    </>
  );
};

const CustomerProfilePage: FC = () => {
  const [selectedTab, setSelectedTab] = useState<TabName>("お客さま基本情報");
  const [companyData, setCompanyData] = useState<CompanyDataState>({
    agreements: [],
    selectedAgreement: null,
  });

  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<{
    major?: string;
    middle?: string;
    minor?: string;
    detail?: string;
  }>({});

  const [token, setToken] = useState<string | null>(null);

  const { isBankUser, isVis } = useRoleFlags();

  const location = useLocation();
  const navigate = useNavigate();
  const locationState = location.state as LocationState;
  const effectivePermission = locationState?.permission ?? 1;
  const dataSource = locationState?.dataSource;

  const displayMode = location.state?.mode;
  const [isEditing, setIsEditing] = useState(displayMode === "edit");
  const [isManualSelection, setIsManualSelection] = useState<boolean>(false);

  const [industryTree, setIndustryTree] = useState<{
    divisions: { id: string; name: string }[];
    majorGroups: { id: string; name: string }[];
    minorGroups: { id: string; name: string }[];
    industryCodes: { id: string; name: string }[];
    parentChildMap: Record<string, any[]>;
  }>({
    divisions: [],
    majorGroups: [],
    minorGroups: [],
    industryCodes: [],
    parentChildMap: {},
  });

  const [rootIndustries, setRootIndustries] = useState<IndustryOptionType[]>([]);
  const [selectedA, setSelectedA] = useState<IndustryOptionType | null>(null);
  const [selectedB, setSelectedB] = useState<IndustryOptionType | null>(null);
  const [selectedC, setSelectedC] = useState<IndustryOptionType | null>(null);
  const [selectedD, setSelectedD] = useState<IndustryOptionType | null>(null);

  const [optionsB, setOptionsB] = useState<IndustryOptionType[]>(selectedA?.children ?? []);
  const [optionsC, setOptionsC] = useState<IndustryOptionType[]>(selectedB?.children ?? []);
  const [optionsD, setOptionsD] = useState<IndustryOptionType[]>(selectedC?.children ?? []);

  // フォーム管理
  const methods = useForm<CustomerProfile>();
  const { control, handleSubmit, reset } = methods;

  // 産業分類フィールドの値を監視（既存ロジック維持）
  const divisionValue = methods.watch("industry_class_major_name");
  const majorGroupValue = methods.watch("industry_class_middle_name");
  const minorGroupValue = methods.watch("industry_class_minor_name");

  const [corporateData, setCorporateData] = useState<{
    company_name: string;
    corporate_number: string;
    company_address: string;
  } | null>(null);

  // corporateData を sessionStorage から読み込み
  useEffect(() => {
    const stored = sessionStorage.getItem("corporateData");
    if (stored) setCorporateData(JSON.parse(stored));
  }, []);

  // token
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sessionData = sessionStorage.getItem("session");
    if (sessionData) setToken(JSON.parse(sessionData).token);
  }, []);

  // 権限フラグ（既存）
  const [isEpAdmin, setIsEpAdmin] = useState(false);
  const [isEpGeneral, setIsEpGeneral] = useState(false);
  const [isBank, setIsBank] = useState(false);
  const [isBranchAdmin, setIsBranchAdmin] = useState(false);
  const [isBranchGeneral, setIsBranchGeneral] = useState(false);
  const [isRepGeneral, setIsRepGeneral] = useState(false);
  const [isRepAdmin, setIsRepAdmin] = useState(false);
  const [isTcsAdmin, setIsTcsAdmin] = useState(false);
  const [isTcsGeneral, setIsTcsGeneral] = useState(false);

  useEffect(() => {
    const userRoleFlags = JSON.parse(sessionStorage.getItem("userRoleFlags") || "{}");

    setIsEpAdmin(!!userRoleFlags.isEpAdmin);
    setIsEpGeneral(!!userRoleFlags.isEpGeneral);

    setIsBank(!!userRoleFlags.isBank);
    setIsBranchAdmin(!!userRoleFlags.isBranchAdmin);
    setIsBranchGeneral(!!userRoleFlags.isBranchGeneral);

    setIsRepAdmin(!!userRoleFlags.isRepAdmin);
    setIsRepGeneral(!!userRoleFlags.isRepGeneral);

    setIsTcsAdmin(!!userRoleFlags.isTcsAdmin);
    setIsTcsGeneral(!!userRoleFlags.isTcsGeneral);
  }, []);

  // options 派生
  useEffect(() => {
    setOptionsB(selectedA?.children || []);
  }, [selectedA]);
  useEffect(() => {
    setOptionsC(selectedB?.children || []);
  }, [selectedB]);
  useEffect(() => {
    setOptionsD(selectedC?.children || []);
  }, [selectedC]);

  const findOptionByText = (options: IndustryOptionType[], text: string): IndustryOptionType | null => {
    return options.find((opt) => opt.text === text) || null;
  };

  // 編集モードで、selectedAgreement の値から A/B/C/D を復元（既存）
  useEffect(() => {
    if (!isEditing) return;
    if (isManualSelection) return;
    if (!companyData.selectedAgreement) return;
    if (rootIndustries.length === 0) return;

    setSelectedA(findOptionByText(rootIndustries, companyData.selectedAgreement.industry_class_major_name));
    setSelectedB(findOptionByText(optionsB, companyData.selectedAgreement.industry_class_middle_name));
    setSelectedC(findOptionByText(optionsC, companyData.selectedAgreement.industry_class_minor_name));
    setSelectedD(findOptionByText(optionsD, companyData.selectedAgreement.industry_class_detail_name));
  }, [isEditing, isManualSelection, companyData.selectedAgreement, rootIndustries, optionsB, optionsC, optionsD]);

  // URL state update（既存）
  const updateLocationState = useCallback(
    (orgIdValue: string, agreementCategoryValue: string) => {
      const currentState = (location.state as LocationState | undefined) ?? {};
      if (currentState.orgId === orgIdValue && currentState.agreementCategory === agreementCategoryValue) return;

      navigate(location.pathname, {
        replace: true,
        state: {
          ...currentState,
          orgId: orgIdValue,
          agreementCategory: agreementCategoryValue,
        },
      });
    },
    [location.pathname, location.state, navigate],
  );

  // フォーム初期化（既存）
  useEffect(() => {
    if (!corporateData) return;

    const profileData: Partial<CustomerProfile> = {
      company_name: corporateData.company_name,
      corporate_number: corporateData.corporate_number,
      company_address: corporateData.company_address,

      business_office_count: "",
      industry_class_major_name: "",
      industry_class_middle_name: "",
      industry_class_minor_name: "",
      industry_class_detail_name: "",

      agreement_category: "",
      agreement_name: "",
      org_id: "",
    };

    reset(profileData as CustomerProfile);
  }, [corporateData, dataSource, reset]);

  const convertToProfile = useCallback(
    (data: CompanyAgreement): CustomerProfile => ({
      company_name: data.company_name,
      corporate_number: corporateData?.corporate_number || "",
      company_address: data.company_address,
      business_office_count: String(data.business_office_count ?? ""),
      industry_class_major_name: data.industry_class_major_name || "",
      industry_class_middle_name: data.industry_class_middle_name || "",
      industry_class_minor_name: data.industry_class_minor_name || "",
      industry_class_detail_name: data.industry_class_detail_name || "",
      agreement_category: data.agreement_category,
      agreement_name: data.agreement_name,
      org_id: data.org_id,
    }),
    [corporateData?.corporate_number],
  );

  const applySelection = useCallback(
    (nextCat: string, nextOrgId?: string) => {
      if (!nextCat) return;

      const byCatAndOrg =
        nextOrgId ? companyData.agreements.find((a) => a.agreement_category === nextCat && a.org_id === nextOrgId) : null;
      const byCatOnly = companyData.agreements.find((a) => a.agreement_category === nextCat) ?? null;

      const agreement = byCatAndOrg ?? byCatOnly;
      if (!agreement) return;

      setCompanyData((prev) => ({
        ...prev,
        selectedAgreement: agreement,
      }));

      reset(convertToProfile(agreement));
      setErrorMessage("");

      updateLocationState(agreement.org_id || "", agreement.agreement_category || "");
    },
    [companyData.agreements, convertToProfile, reset, updateLocationState],
  );

  const corporateNumber = corporateData?.corporate_number;

  // api: corp/basic-info
  const fetchCustomerData = useCallback(async () => {
    try {
      setLoading(true);

      const url = `/api/corp/basic-info?corporate_number=${corporateNumber}`;
      const response = await getData(url);

      const rawAgreements: CompanyAgreement[] = response.result_list ?? [];

      const agreements: CompanyAgreement[] =
        effectivePermission === 1
          ? rawAgreements.filter((a) => (a.agreement_category ?? "").startsWith("0"))
          : effectivePermission === 2
            ? rawAgreements.filter((a) => (a.agreement_category ?? "").startsWith("1"))
            : rawAgreements;

      setCompanyData({
        agreements,
        selectedAgreement: agreements[0] ?? null, // 仮（本命は applySelection が上書き）
      });

      setLoading(false);
    } catch (err: any) {
      setErrorMessage(err.data?.message);
      setLoading(false);
    }
  }, [corporateNumber, effectivePermission]);

  useEffect(() => {
    if (!corporateNumber) return;
    fetchCustomerData();
  }, [corporateNumber, effectivePermission, fetchCustomerData]);

  // 産業分類データ処理（既存）
  const processIndustryData = (industryData: any[]) => {
    const parentChildMap: Record<string, any[]> = {};
    const allNodes: any[] = [];

    const divisions: { id: string; name: string }[] = [];
    const majorGroups: { id: string; name: string }[] = [];
    const minorGroups: { id: string; name: string }[] = [];
    const industryCodes: { id: string; name: string }[] = [];

    const processNode = (node: any, parentCode: string | null = null, level = 1) => {
      const nodeData = { id: node.code, name: node.text, level, parentCode };

      switch (level) {
        case 1:
          divisions.push(nodeData);
          break;
        case 2:
          majorGroups.push(nodeData);
          break;
        case 3:
          minorGroups.push(nodeData);
          break;
        case 4:
          industryCodes.push(nodeData);
          break;
      }

      allNodes.push(nodeData);

      if (parentCode) {
        if (!parentChildMap[parentCode]) parentChildMap[parentCode] = [];
        parentChildMap[parentCode].push(nodeData);
      }

      if (node.children && node.children.length > 0) {
        node.children.forEach((child: any) => processNode(child, node.code, level + 1));
      }
    };

    industryData.forEach((node) => processNode(node));

    return { divisions, majorGroups, minorGroups, industryCodes, parentChildMap, allNodes };
  };

  // 産業分類 option 取得（既存）
  useEffect(() => {
    const fetchIndustryOptions = async () => {
      if (!isEditing) return;

      try {
        const response = await getData("/api/ui/option/industry", {
          Authorization: `Bearer ${token}`,
        });

        if (!response.ok) throw new Error(Messages.energy_building.ebrc03.industry_data_fetch_failed);

        const { result_list }: { result_list: IndustryOptionType[] } = response;

        const processedOptions = processIndustryData(result_list);
        setIndustryTree(processedOptions);
        setRootIndustries(result_list);
      } catch (err) {
        setErrorMessage((err as any).data?.message);
      }
    };

    fetchIndustryOptions();
  }, [token, isEditing]);

  const toggleEditMode = useCallback(() => {
    setIsEditing(!isEditing);
  }, [isEditing]);

  const handleCancelEdit = () => {
    setIsEditing(false);
    setErrorMessage("");
    setErrors({ major: undefined, middle: undefined, minor: undefined, detail: undefined });
    setIsManualSelection(false);
    if (companyData.selectedAgreement) {
      reset(convertToProfile(companyData.selectedAgreement));
    }
  };

  // 大/中/小の watch 連動（既存のまま）
  useEffect(() => {
    if (!isEditing) return;
    if (divisionValue && industryTree.parentChildMap) {
      const filteredMajorGroups = industryTree.parentChildMap[divisionValue] || [];
      setIndustryTree((prev) => ({
        ...prev,
        majorGroups: filteredMajorGroups.map((item) => ({ id: item.id, name: item.name })),
      }));

      methods.setValue("industry_class_middle_name", "");
      methods.setValue("industry_class_minor_name", "");
      methods.setValue("industry_class_detail_name", "");
    }
  }, [divisionValue, methods, industryTree.parentChildMap, isEditing]);

  useEffect(() => {
    if (!isEditing) return;
    if (majorGroupValue && industryTree.parentChildMap) {
      const filteredMinorGroups = industryTree.parentChildMap[majorGroupValue] || [];
      setIndustryTree((prev) => ({
        ...prev,
        minorGroups: filteredMinorGroups.map((item) => ({ id: item.id, name: item.name })),
      }));

      methods.setValue("industry_class_minor_name", "");
      methods.setValue("industry_class_detail_name", "");
    }
  }, [majorGroupValue, methods, industryTree.parentChildMap, isEditing]);

  useEffect(() => {
    if (!isEditing) return;
    if (minorGroupValue && industryTree.parentChildMap) {
      const filteredIndustryCodes = industryTree.parentChildMap[minorGroupValue] || [];
      setIndustryTree((prev) => ({
        ...prev,
        industryCodes: filteredIndustryCodes.map((item) => ({ id: item.id, name: item.name })),
      }));

      methods.setValue("industry_class_detail_name", "");
    }
  }, [minorGroupValue, methods, industryTree.parentChildMap, isEditing]);

  // 保存処理（既存）
  const handleSaveProfile = async (data: CustomerProfile) => {
    const parseResult = industrySchema.safeParse({
      major: selectedA?.code || "",
      middle: selectedB?.code || "",
      minor: selectedC?.code || "",
      detail: selectedD?.code || "",
    });

    if (!parseResult.success) {
      const fieldErrors = parseResult.error.flatten().fieldErrors;
      setErrors({
        major: fieldErrors.major?.[0],
        middle: fieldErrors.middle?.[0],
        minor: fieldErrors.minor?.[0],
        detail: fieldErrors.detail?.[0],
      });
      return;
    }

    try {
      if (!companyData.selectedAgreement) {
        throw new Error(Messages.VALIDATION.data.none);
      }

      const updatePayload = {
        org_id: companyData.selectedAgreement.org_id,
        corporate_number: corporateData?.corporate_number,
        agreement_category: data.agreement_category,
        business_office_count: data.business_office_count || 0,
        industry_class_major_code: selectedA?.code,
        industry_class_middle_code: selectedB?.code,
        industry_class_minor_code: selectedC?.code,
        industry_class_detail_code: selectedD?.code,
      };

      const response = await postData(`/api/corp/basic-info`, updatePayload, {});

      if (!response.ok) {
        throw new Error(Messages.SAVE_FAILED);
      }

      saveSuccessToast();

      const updatedProfile = convertToProfile({
        ...companyData.selectedAgreement,
        ...updatePayload,
      } as CompanyAgreement);

      setCompanyData((prev) => ({
        ...prev,
        selectedAgreement: {
          ...(prev.selectedAgreement as CompanyAgreement),
          ...updatePayload,
        } as CompanyAgreement,
      }));

      setErrors({ major: undefined, middle: undefined, minor: undefined, detail: undefined });
      setSaving(true);
      reset(updatedProfile);
      setIsEditing(false);
      fetchCustomerData();
    } catch (err) {
      setErrorMessage((err as any).data?.message || Messages.SAVE_FAILED);
    } finally {
      setSaving(false);
    }
  };

  const breadcrumbItems = useMemo((): BreadCrumbType[] => {
    const name = companyData.selectedAgreement?.company_name || corporateData?.company_name || "";
    return [
      { title: "レポート作成・管理", link: "/energy-building/ebmg01" },
      { title: name, link: "" },
    ];
  }, [companyData.selectedAgreement?.company_name, corporateData?.company_name]);

  return (
    <CommonLayout
      selectedTab={selectedTab}
      onTabChange={setSelectedTab}
      breadcrumbItems={breadcrumbItems}
      permission={effectivePermission}
      // 地銀は true（組織も出す）、可視化は false（経路だけ）
      showConsentOrgSelector={effectivePermission === 1}
      // 編集中は CommonLayout 側の selector を止めたいならここで渡す
      disableConsentSelector={isEditing}
    >
      <CustomerProfileInner
        companyData={companyData}
        applySelection={applySelection}
        selectedTab={selectedTab}
        isVis={isVis}
        isEditing={isEditing}
        saving={saving}
        loading={loading}
        errorMessage={errorMessage}
        errorTopRef={errorTopRef as React.RefObject<HTMLDivElement>}
        methods={methods}
        handleSubmit={handleSubmit}
        control={control}
        corporateData={corporateData}
        errors={errors}
        toggleEditMode={toggleEditMode}
        handleCancelEdit={handleCancelEdit}
        handleSaveProfile={handleSaveProfile}
        rootIndustries={rootIndustries}
        optionsB={optionsB}
        optionsC={optionsC}
        optionsD={optionsD}
        selectedA={selectedA}
        selectedB={selectedB}
        selectedC={selectedC}
        selectedD={selectedD}
        setIsManualSelection={setIsManualSelection}
        setSelectedA={setSelectedA}
        setSelectedB={setSelectedB}
        setSelectedC={setSelectedC}
        setSelectedD={setSelectedD}
        setErrors={setErrors}
        isEpAdmin={isEpAdmin}
        isEpGeneral={isEpGeneral}
        isBank={isBank}
        isBranchAdmin={isBranchAdmin}
        isBranchGeneral={isBranchGeneral}
        isRepAdmin={isRepAdmin}
        isRepGeneral={isRepGeneral}
        isTcsAdmin={isTcsAdmin}
        isTcsGeneral={isTcsGeneral}
      />
    </CommonLayout>
  );
};

export default CustomerProfilePage;
