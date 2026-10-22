import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import BreadCrumb from "~/components/common/breadcrumb";
import SectionTitle from "~/components/common/section-title";
import MasterLayout from "~/components/layout/master-layout";
import { EbConsentSelectionProvider } from "~/hooks/useEbConsentSelection";
import { useRoleFlags } from "~/hooks/useRoleFlags";
import { getData } from "~/lib/fetch";
import { PERMISSION_TAB_URLS, TabName, TabNavigator } from "../components/tab-navigator";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

const CONSENT_CHANGED_EVENT = "eb_consent_changed";

type Props = {
  children: React.ReactNode;
  selectedTab: TabName;
  onTabChange: (tab: TabName) => void;
  breadcrumbItems: { title: string; link: string; className?: string }[];
  permission: number;
  showConsentOrgSelector?: boolean; // 地銀側だけ true
  disableConsentSelector?: boolean; // 編集中など
};
type AgreementRow = {
  agreement_category: string;
  agreement_name: string;
  org_id: string;
  org_name?: string;
};
type Option = { value: string; label: string };

const CommonLayout = ({
  children,
  selectedTab,
  onTabChange,
  showConsentOrgSelector,
  disableConsentSelector,
}: Props) => {
  const [showPopup, setShowPopup] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const permission = location.state?.permission ?? 1;
  const customerData = location.state?.customerData;
  const { isBankUser, isVis } = useRoleFlags();
  const [corporateData, setCorporateData] = useState<{
    company_name: string;
    corporate_number: string;
    company_address: string;
    agreement_category: string[];
  } | null>(null);
  const [consentRouteOptions, setConsentRouteOptions] = useState<Option[]>([]);
  const [consentOrgOptions, setConsentOrgOptions] = useState<Option[]>([]);
  const [agreementRows, setAgreementRows] = useState<AgreementRow[]>([]);
  const [selectedAgreementCategory, setSelectedAgreementCategory] = useState<string>("");
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");

  const [consentLoading, setConsentLoading] = useState(false);
  const [consentKeyPrefix, setConsentKeyPrefix] = useState<string>("");

  const corporateNumber = corporateData?.corporate_number;
  // corporateDataをsessionStorageから読み込み
  useEffect(() => {
    const stored = sessionStorage.getItem("corporateData");
    if (stored) {
      setCorporateData(JSON.parse(stored));
    }
  }, []);
  const categories: string[] = corporateData?.agreement_category ?? [];
  const isMiddleEnabled = categories.some((code) => code.startsWith("0"));
  const isMajorEnabled = categories.some((code) => code.startsWith("1"));

  const buildOptions = (rows: AgreementRow[], selectedCat?: string) => {
    // 経路 options（agreement_categoryでユニーク）
    const routeMap = new Map<string, Option>();
    for (const r of rows) {
      if (!routeMap.has(r.agreement_category)) {
        routeMap.set(r.agreement_category, {
          value: r.agreement_category,
          label: r.agreement_name ?? r.agreement_category,
        });
      }
    }
    setConsentRouteOptions(Array.from(routeMap.values()));

    // 組織 options：選択中の経路で絞ってから org_id でユニーク
    const cat = selectedCat ?? "";
    const orgSource = cat ? rows.filter((r) => r.agreement_category === cat) : rows;
    const orgMap = new Map<string, Option>();
    for (const r of orgSource) {
      if (!orgMap.has(r.org_id)) {
        orgMap.set(r.org_id, { value: r.org_id, label: r.org_name || r.org_id });
      }
    }
    setConsentOrgOptions(Array.from(orgMap.values()).sort((a, b) => a.label.localeCompare(b.label, "ja")));
  };

  const emitConsentChanged = (agreementCategory: string, orgId: string) => {
    window.dispatchEvent(
      new CustomEvent(CONSENT_CHANGED_EVENT, {
        detail: {
          permission,
          corporateNumber,
          agreementCategory,
          orgId,
        },
      }),
    );
    window.dispatchEvent(new Event("consentSelectionChanged"));
  };

  useEffect(() => {
    const fetchBasicInfoForConsent = async () => {
      // if (!showConsentOrgSelector) return;
      if (!corporateNumber) return;

      const sessionRaw = typeof window !== "undefined" ? sessionStorage.getItem("session") : null;
      const sessionObj = sessionRaw ? JSON.parse(sessionRaw) : null;
      const userId = sessionObj?.authorityInfo?.user_id ?? "unknownUser";
      const orgIdForKey = sessionObj?.authorityInfo?.org_id ?? "unknownOrg";
      const sessionId = sessionObj?.session_id ?? "noSessionId";

      // const keyPrefix = `${sessionId}:${userId}:${orgIdForKey}`;
      const keyPrefix = `${sessionId}:${userId}:${orgIdForKey}:${permission}`;
      setConsentKeyPrefix(keyPrefix);
      const cacheKey = `consentOptions:${keyPrefix}:${corporateNumber}`;
      const catKey = `selectedAgreementCategory:${keyPrefix}:${corporateNumber}`;
      const orgKey = `selectedOrgId:${keyPrefix}:${corporateNumber}`;

      const apply = (rows: AgreementRow[]) => {
        const filteredRows =
          permission === 1
            ? rows.filter((r) => (r.agreement_category ?? "").startsWith("0"))
            : permission === 2
              ? rows.filter((r) => (r.agreement_category ?? "").startsWith("1"))
              : rows;

        setAgreementRows(filteredRows);

        const storedCat = sessionStorage.getItem(catKey) ?? "";
        const storedOrg = sessionStorage.getItem(orgKey) ?? "";

        const catExists = filteredRows.some((r) => r.agreement_category === storedCat);
        const orgExists = filteredRows.some((r) => r.org_id === storedOrg);

        const defaultCat = catExists ? storedCat : filteredRows?.[0]?.agreement_category || "";
        const defaultOrg = orgExists ? storedOrg : filteredRows?.[0]?.org_id || "";

        setSelectedAgreementCategory(defaultCat);
        setSelectedOrgId(defaultOrg);

        if (defaultCat) sessionStorage.setItem(catKey, defaultCat);
        if (defaultOrg) sessionStorage.setItem(orgKey, defaultOrg);
        buildOptions(filteredRows, defaultCat);
        // 初期値確定時に hook にも反映（タブ側が確実に追従できる）
        if (defaultCat && defaultOrg) {
          // 互換イベントも必要なら維持
          emitConsentChanged(defaultCat, defaultOrg);
        }
      };

      const cached = sessionStorage.getItem(cacheKey);
      if (cached) {
        apply(JSON.parse(cached));
        return;
      }

      try {
        setConsentLoading(true);
        const url = `/api/corp/basic-info?corporate_number=${corporateNumber}`;
        const response = await getData(url);

        const rows: AgreementRow[] = response?.result_list ?? [];
        sessionStorage.setItem(cacheKey, JSON.stringify(rows));

        apply(rows);
      } finally {
        setConsentLoading(false);
      }
    };

    fetchBasicInfoForConsent();
  }, [corporateNumber, permission]);

  const breadcrumbItems = [
    { title: "レポート作成・管理", link: "/energy-building/ebmg01" },
    { title: customerData?.company_name || corporateData?.company_name || "未選択", link: "" },
  ];

  const handleVisualization = () => {
    const targetPath = PERMISSION_TAB_URLS[2]["お客さま基本情報"];
    if (permission === 2) {
      setShowPopup(false);
    } else if (targetPath) {
      navigate(targetPath, {
        state: {
          permission: 2,
          customerData: location.state?.customerData,
        },
      });
      setShowPopup(false);
    }
  };

  const handlelocalBank = () => {
    const targetPath = PERMISSION_TAB_URLS[1]["お客さま基本情報"];
    if (permission === 1) {
      setShowPopup(false);
    } else if (targetPath) {
      navigate(targetPath, {
        state: {
          permission: 1,
          customerData: location.state?.customerData,
        },
      });
      setShowPopup(false);
    }
  };

  const handleAgreementCategoryChange = (value: string) => {
    if (!consentKeyPrefix) return;

    const catKey = `selectedAgreementCategory:${consentKeyPrefix}:${corporateNumber}`;
    const orgKey = `selectedOrgId:${consentKeyPrefix}:${corporateNumber}`;

    setSelectedAgreementCategory(value);
    sessionStorage.setItem(catKey, value);

    //  route に紐づく org 一覧を作り直す
    const orgRows = (agreementRows ?? []).filter((r) => r.agreement_category === value);
    const orgMap = new Map<string, Option>();
    for (const r of orgRows) {
      if (!orgMap.has(r.org_id)) {
        orgMap.set(r.org_id, { value: r.org_id, label: r.org_name || r.org_id });
      }
    }
    const nextOrgOptions = Array.from(orgMap.values()).sort((a, b) => a.label.localeCompare(b.label, "ja"));
    setConsentOrgOptions(nextOrgOptions);

    // org は「今の selectedOrgId を維持できるなら維持」、無理なら先頭に
    const stillExists = nextOrgOptions.some((o) => o.value === selectedOrgId);
    const nextOrgId = stillExists ? selectedOrgId : nextOrgOptions?.[0]?.value ?? "";
    setSelectedOrgId(nextOrgId);
    if (nextOrgId) sessionStorage.setItem(orgKey, nextOrgId);

    // window.dispatchEvent(new Event(CONSENT_CHANGED_EVENT));
    // window.dispatchEvent(new Event("consentSelectionChanged"));
    // 互換イベント
    emitConsentChanged(value, nextOrgId);
  };

  const handleOrgChange = (value: string) => {
    if (!consentKeyPrefix) return;

    const orgKey = `selectedOrgId:${consentKeyPrefix}:${corporateNumber}`;
    setSelectedOrgId(value);
    sessionStorage.setItem(orgKey, value);
    // 互換イベント
    emitConsentChanged(selectedAgreementCategory || "", value);
  };

  return (
    <MasterLayout isEditing={false}>
      {/* ① ヘッダー行：パンくず + モード切替 */}
      <div className="flex justify-between items-center mb-4">
        <BreadCrumb items={breadcrumbItems} />
        {!(isVis || isBankUser) && (
          <Button
            variant="second"
            // iconRight={<ArrowRight className="ml-2 w-4 h-4 " />}
            onClick={() => setShowPopup(true)}
            className="border border-solid"
          >
            モード切替
          </Button>
        )}
      </div>

      {/* ② 同意書プルダウン：Tabの上（地銀側だけ） */}
      {/* <div className="min-h-screen bg-gray-50"> */}
      <EbConsentSelectionProvider
        value={{
          agreementCategory: selectedAgreementCategory || "",
          orgId: selectedOrgId || "",
        }}
      >
        <div className="min-h-screen bg-gray-50">
          {/* {showConsentOrgSelector && ( */}
          <div className="px-16 py-3">
            <div className="flex gap-8 items-end">
              {/* 同意書取得経路 */}
              <div className="w-[360px]">
                <span className="block text-sm font-medium text-gray-700 mb-1">同意書取得経路</span>
                <Select
                  value={selectedAgreementCategory || ""}
                  onValueChange={handleAgreementCategoryChange}
                  disabled={disableConsentSelector || consentLoading}
                >
                  <SelectTrigger className="border-none">
                    <SelectValue placeholder={consentLoading ? "読み込み中..." : "選択してください"} />
                  </SelectTrigger>
                  <SelectContent position="popper" className="z-[10000]">
                    {consentRouteOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* 同意書取得組織 */}
              {showConsentOrgSelector && (
                <div className="w-[360px]">
                  <span className="block text-sm font-medium text-gray-700 mb-1">同意書取得組織</span>
                  <Select
                    value={selectedOrgId || ""}
                    onValueChange={handleOrgChange}
                    disabled={disableConsentSelector || consentLoading}
                  >
                    <SelectTrigger className="border-none">
                      <SelectValue placeholder={consentLoading ? "読み込み中..." : "選択してください"} />
                    </SelectTrigger>
                    <SelectContent position="popper" className="z-[10000]">
                      {consentOrgOptions.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          </div>

          {/* ③ Tab Navigator */}
          <div className="px-16">
            <TabNavigator selectedTab={selectedTab} onTabChange={onTabChange} permission={permission} />
          </div>

          <div>{children}</div>
        </div>
      </EbConsentSelectionProvider>
      <Dialog open={showPopup} onOpenChange={setShowPopup}>
        <DialogTrigger hidden />
        <DialogContent>
          <DialogTitle hidden />
          <DialogDescription hidden />

          <div>
            <SectionTitle className="justify-center">作成・管理するレポートの種類を選択してください</SectionTitle>

            <div className="flex pt-10 py-2 justify-center">
              <Button
                variant="default"
                size="lg"
                className="text-sm px-4 py-2 rounded w-[300px] overflow-hidden text-ellipsis"
                onClick={handlelocalBank}
                disabled={!isMiddleEnabled}
              >
                ミドル向けレポート
              </Button>
            </div>

            <div className="flex py-2 justify-center">
              <Button
                variant="default"
                size="lg"
                className="text-sm px-4 py-2 rounded w-[300px] overflow-hidden text-ellipsis"
                onClick={handleVisualization}
                disabled={!isMajorEnabled}
              >
                メジャー向けレポート
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </MasterLayout>
  );
};

export default CommonLayout;
