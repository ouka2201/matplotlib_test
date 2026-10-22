// import { MetaFunction } from "@remix-run/node";
import { ColumnDef } from "@tanstack/react-table";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import SectionTitle from "~/components/common/section-title";
import { SessionAuthorityInfo, useSession } from "~/components/layout/session-provider";
import { Button } from "~/components/ui/button";
import { Command, CommandList } from "~/components/ui/command";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Messages } from "~/constants/messages/message";
import { useEbConsentSelection } from "~/hooks/useEbConsentSelection";
import { useRoleFlags } from "~/hooks/useRoleFlags";
import { useScrollToError } from "~/hooks/useScrollToError";
import CommonLayout from "../components/CommonLayout";
import { Icon, Text } from "../components/import";
import { TabName } from "../components/tab-navigator";
import { PageableTable } from "../components/ui/pageable-table";
import { getData } from "../lib/fetch";
import "../styles/popup.css";
import UploadData from "./data-upload";

type baseList = {
  orgName: string;
  baseId: string;
  baseName: string;
  Category: string;
  agreementCode: string;
  orgId: string;
  fourM: string;
  fiveM: string;
  sixM: string;
  sevenM: string;
  eightM: string;
  nineM: string;
  tenM: string;
  elevenM: string;
  twelveM: string;
  oneM: string;
  twoM: string;
  threeM: string;
  locIdentifierCd: string;
};

type BuildingData = {
  orgName?: string;
  building_id: string;
  building_name: string;
  co2_emissions: number[];
  primary_energy_data: number[];
  start_year_month: string;
  agreement_category: string;
  org_id: string;
  locIdentifierCd: string;
};

type YearData = {
  fiscal_year: string;
  data_buildings: BuildingData[];
};

type VendorData = {
  vis_vendor_name: string;
  data_years: YearData[];
};

// ---- Inner (Provider 配下で EbConsentSelection を読めるように) ----
type InnerProps = {
  selectedTab: TabName;
  setSelectedTab: (t: TabName) => void;
  permission: number;
};

const ReportENeRuGiInner: React.FC<InnerProps> = ({ selectedTab, setSelectedTab, permission }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const backState = (location.state as any) || {};
  const customerData = location.state?.customerData;

  const [showEnergyPopup, setShowEnergyPopup] = useState(false);
  const [showHearingPopup, setShowHearingPopup] = useState(false);

  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState<string | undefined>(
    backState.selectedYear ?? undefined
  );
  const [yearOptions, setYearOptions] = useState<string[]>([]);
  const [data, setData] = useState<baseList[]>([]);
  const [vendors, setVendors] = useState<VendorData[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");

  const errorTopRef = useScrollToError(errorMessage);

  const { session } = useSession();
  const [authorityInfo, setAuthorityInfo] = useState<SessionAuthorityInfo | null>(session?.authorityInfo ?? null);
  const { isVis, isEp, } = useRoleFlags();
  const [token, setToken] = useState<string | null>(session?.token ?? null);

  // ★ CommonLayout のプルダウン選択値
  const { agreementCategory, orgId } = useEbConsentSelection();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        const parsed = JSON.parse(sessionData);
        setToken(parsed.token);
        setAuthorityInfo(parsed.authorityInfo);
      }
    }
  }, [session]);

  // 複数の vendor の年度データをマージする関数
  function mergeVendorsYear(vendors: VendorData[], year: string): YearData | null {
    const buildings: any[] = [];

    vendors.forEach((vendor) => {
      const yearData = vendor.data_years?.find((y) => y.fiscal_year === year);
      if (!yearData) return;

      yearData.data_buildings.forEach((building) => {
        buildings.push({
          ...building,
          orgName: vendor.vis_vendor_name,
        });
      });
    });

    return {
      fiscal_year: year,
      data_buildings: buildings,
    };
  }

  const report1Columns: ColumnDef<baseList>[] = [
    {
      accessorKey: "locIdentifierCd",
      header: "拠点ID",
      size: 40,
      cell: (info) => {
        const value = String(info.getValue() ?? "");
        return (
          <span className="block max-w-[80px] truncate whitespace-nowrap" title={value}>
            {value}
          </span>
        );
      },
      meta: { className: "bg-white z-20 border-r border-gray-200" },
    },
    {
      accessorKey: "baseName",
      header: "拠点名",
      cell: ({ row }) => {
        const item = row.original;
        const name = row.original.baseName;
        if (isEp) {
          return (
            <button
              onClick={() => {
                const buildingData = {
                  corporate_number: customerData?.corporate_number ?? "",
                  agreement_code: item.agreementCode,
                  org_id: item.orgId,
                  building_id: item.baseId,
                };

                sessionStorage.setItem("selectedBuildingData", JSON.stringify(buildingData));
                // navigate("/master/msbd04", { state: { customerData } });
                navigate("/master/msbd04", {
                  state: {
                    customerData,
                    fromScreen: "ebrc05",
                    returnPath: "/energy-building/ebrc05",
                    forceActiveMenu: "ebmg01",
                    returnState: {
                      customerData,
                      permission,
                      selectedTab,
                      selectedYear,
                      agreementCategory,
                      orgId,
                    },
                    buildingName: item.baseName,
                  },
                });
              }}
              className="table-link underline text-left block w-[120px] truncate whitespace-nowrap"
              title={String(name ?? "")}
            >
              {name}
            </button>
          );
        }
        return (
          <span className="block max-w-[120px] truncate whitespace-nowrap" title={String(name ?? "")}>
            {name}
          </span>
        );
      },
      meta: { className: "min-w-[150px] sticky left-[300px] bg-white z-20 border-r border-gray-200" },
    },
    {
      accessorKey: "Category",
      header: "種別",
      cell: (info) => {
        const value = String(info.getValue() ?? "");
        return (
          <span className="block max-w-[150px] truncate whitespace-nowrap" title={value}>
            {value}
          </span>
        );
      },
      meta: { className: "min-w-[150px] sticky left-[450px] bg-white z-20 border-r border-gray-200" },
    },
    { accessorKey: "fourM", header: "4月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "fiveM", header: "5月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "sixM", header: "6月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "sevenM", header: "7月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "eightM", header: "8月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "nineM", header: "9月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "tenM", header: "10月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "elevenM", header: "11月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "twelveM", header: "12月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "oneM", header: "1月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "twoM", header: "2月", size: 60, meta: { className: "whitespace-nowrap" } },
    { accessorKey: "threeM", header: "3月", size: 60, meta: { className: "whitespace-nowrap" } },
    {
      accessorKey: "orgName",
      header: "登録組織名",
      cell: (info) => {
        const value = String(info.getValue() ?? "");
        return (
          <span className="block max-w-[150px] truncate whitespace-nowrap" title={value}>
            {value}
          </span>
        );
      },
      meta: { className: "min-w-[200px] sticky left-0 bg-white z-20 border-r border-gray-200" },
    },
  ];

  const corporateNumber = customerData?.corporate_number || "";

  // 月キーの定義とマッピング関数
  const monthKeys: (keyof baseList)[] = [
    "fourM",
    "fiveM",
    "sixM",
    "sevenM",
    "eightM",
    "nineM",
    "tenM",
    "elevenM",
    "twelveM",
    "oneM",
    "twoM",
    "threeM",
  ];

  const mapMonthValues = (values: number[] = []): Pick<baseList, (typeof monthKeys)[number]> => {
    return monthKeys.reduce((acc, key, idx) => {
      acc[key] = values[idx]?.toString() ?? "-";
      return acc;
    }, {} as Pick<baseList, (typeof monthKeys)[number]>);
  };

  const convertYearDataToTable = (year: YearData): baseList[] => {
    return year.data_buildings.flatMap((building) => {
      const common = {
        orgName: building.orgName ?? "",
        baseId: building.building_id,
        baseName: building.building_name,
        agreementCode: building.agreement_category,
        orgId: building.org_id,
        locIdentifierCd: building.locIdentifierCd,
      };

      return [
        {
          ...common,
          Category: "CO2排出量",
          ...mapMonthValues(building.co2_emissions),
        },
        {
          ...common,
          Category: "一次エネルギー消費量",
          ...mapMonthValues(building.primary_energy_data),
        },
      ];
    });
  };

  const setFilteredData = (yearData: YearData, agreementCode?: string) => {
    const filteredBuildings = yearData.data_buildings.filter((b) => !agreementCode || b.agreement_category === agreementCode);
    setData(convertYearDataToTable({ fiscal_year: yearData.fiscal_year, data_buildings: filteredBuildings }));
  };

  // API 取得（CommonLayout の agreementCategory/orgId に追従）
  const handleSearch = useCallback(async () => {
    if (!token) return;
    if (!corporateNumber) return;

    setLoading(true);
    setErrorMessage("");

    try {
      let url = `/api/building/energy-info-list?corporate_number=${corporateNumber}`;

      // 地銀側で orgId で絞る要件があるのでそのまま維持
      if (orgId) url += `&org_id=${orgId}`;

      // 経路は CommonLayout の選択を使う
      if (agreementCategory) url += `&agreement_category=${agreementCategory}`;

      console.log(Messages.VALIDATION.data.sent_url, url);

      const raw = await getData(url);
      const nextVendors: VendorData[] = raw.result_list?.data_vendors ?? [];
      setVendors(nextVendors);

      if (!nextVendors.length) {
        setData([]);
        setYearOptions([]);
        setSelectedYear(undefined);
        return;
      }

      const allYears = Array.from(new Set(nextVendors.flatMap((v) => (v.data_years ?? []).map((y) => y.fiscal_year))))
        .map(String)
        .sort();

      setYearOptions(allYears);

      // 年度選択の挙動：
      // - 1つなら自動選択して表示
      // - 複数なら「今選んでる年度」を維持できれば維持、できなければ未選択に
      if (allYears.length === 1) {
        const onlyYear = allYears[0];
        setSelectedYear(onlyYear);
        const merged = mergeVendorsYear(nextVendors, onlyYear);
        if (merged) setFilteredData(merged, agreementCategory);
        else setData([]);
      } else {
        // 複数年度：既存選択がまだ存在するなら維持、なければ未選択
        setSelectedYear((prev) => (prev && allYears.includes(prev) ? prev : undefined));
        setData([]); // 年度選択待ち
      }
    } catch (error) {
      console.error(Messages.VALIDATION.api.search_error, error);
      setErrorMessage((error as any).data?.message);
      setData([]);
      setYearOptions([]);
    } finally {
      setLoading(false);
    }
  }, [token, corporateNumber, orgId, agreementCategory]);

  // 経路/組織が変わったら再検索（年度聯动は handleSearch 側で維持）
  useEffect(() => {
    if (!token) return;
    if (!corporateNumber) return;
    if (!agreementCategory) return; // 経路が未選択の間は検索しない（無駄打ち防止）
    // if (permission === 1 && !orgId) return;
    handleSearch();
  }, [token, corporateNumber, agreementCategory, orgId, permission, handleSearch]);

  // 年度 or 経路が変わったら表示データ更新
  useEffect(() => {
    if (!selectedYear || !vendors.length) return;
    const merged = mergeVendorsYear(vendors, selectedYear);
    if (merged) setFilteredData(merged, agreementCategory);
  }, [selectedYear, agreementCategory, vendors]);

  const uploadData = [
    {
      company_name: customerData?.company_name,
      company_name_kana: customerData?.company_name_kana,
      corporate_number: customerData?.corporate_number,
    },
  ];

  return (
    <>
      <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />
      {errorMessage && (
        <div
          ref={errorTopRef as React.RefObject<HTMLDivElement>}
          className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden scroll-mt-[300px]"
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

      {selectedTab === "拠点・エネルギー情報" && (
        <div className="ml-4 mr-16 pt-4 max-w-full">
          <div className="relative table-container">
            {/* 検索条件 + ボタン */}
            <div className="flex justify-between items-start mr-8 ml-8">
              {/* 年度（経路は CommonLayout 側に一本化済み） */}
              <div className="space-y-4">
                {/* 対象年度の選択 */}
                <div className="space-y-2">
                  <SectionTitle className="!text-[14px]">対象年度の選択</SectionTitle>
                  <Select value={selectedYear ?? ""} onValueChange={(year) => setSelectedYear(year)} disabled={yearOptions.length === 0 || loading}>
                    <SelectTrigger className="w-64">
                      <SelectValue placeholder={loading ? "読み込み中..." : "選択してください"} />
                    </SelectTrigger>
                    <SelectContent>
                      {yearOptions.map((year) => (
                        <SelectItem key={year} value={year}>
                          {year}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex flex-col items-end gap-4">
                <Button onClick={() => setShowEnergyPopup(true)} variant="primary" className="w-[180px]">
                  エネルギーデータ登録
                </Button>
                <UploadData
                  data={uploadData}
                  modalOpen={showEnergyPopup}
                  onOpenChange={(open) => setShowEnergyPopup(open)}
                  uploadFileType="energy"
                  onUploadComplete={() => {
                    handleSearch();
                  }}
                />

                {!isVis && (
                  <>
                    <Button onClick={() => setShowHearingPopup(true)} variant="primary" className="w-[180px]">
                      ヒアリングデータ登録
                    </Button>
                    <UploadData
                      data={uploadData}
                      modalOpen={showHearingPopup}
                      onOpenChange={(open) => setShowHearingPopup(open)}
                      uploadFileType="hearing"
                      onUploadComplete={() => {
                        handleSearch();
                      }}
                    />
                  </>
                )}
              </div>
            </div>

            <div className="ml-8 mr-8 py-6 w-full max-w-full overflow-x-auto">
              <Command className="w-full">
                <CommandList className="w-full">
                  <div className="min-w-max border-collapse">
                    <PageableTable<baseList, unknown>
                      columns={report1Columns}
                      data={data}
                      pageCount={1}
                      totalCount={data.length}
                      pageSizeOptions={[5, 10, 20, 50]}
                    />
                  </div>
                </CommandList>
              </Command>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

// ---- Outer (CommonLayout をラップして Provider 配下に Inner を置く) ----
const ReportENeRuGi: React.FC = () => {
  const location = useLocation();
  const permission = (location.state as any)?.permission ?? 1;

  const [selectedTab, setSelectedTab] = useState<TabName>("拠点・エネルギー情報");

  const breadcrumbItems = useMemo(
    () => [
      { title: "レポート作成・管理", link: "/", className: "color-green-primar" },
      { title: "○○株式会社", link: "/" },
    ],
    [],
  );

  return (
    <CommonLayout selectedTab={selectedTab} onTabChange={setSelectedTab} breadcrumbItems={breadcrumbItems} permission={permission} showConsentOrgSelector={permission === 1}>
      <ReportENeRuGiInner selectedTab={selectedTab} setSelectedTab={setSelectedTab} permission={permission} />
    </CommonLayout>
  );
};

export default ReportENeRuGi;
