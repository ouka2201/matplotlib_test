// import { MetaFunction } from "@remix-run/node";
import { ColumnDef } from "@tanstack/react-table";
import { format, parse } from "date-fns";
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Command, CommandList } from "~/components/ui/command";
import { Messages } from "~/constants/messages/message";
import CommonLayout from "../components/CommonLayout";
import ErrorHint from "../components/common/error-hint";
import { TabName } from "../components/tab-navigator";
import { PageableTable } from "../components/ui/pageable-table";
import { useEbConsentSelection } from "~/hooks/useEbConsentSelection";
import { getData } from "../lib/fetch";
import "../styles/popup.css";



// export const meta: MetaFunction = () => {
//   return [
//     { title: "CNレポート作成_電力情報" },
//     { name: "ebrc07", content: "PowerInformation" },
//   ];
// };

type listInfo = {
  buildingName: string;
  dataEntryPeriod: string;
  fileUpdateDate: string;
};

type UploadHistoryItem = {
  building_name: string;
  period_from: string;
  period_to: string;
  file_update_date: string;
};

type ApiResponse = {
  result: {
    upload_history: UploadHistoryItem[];
  };
};

const PowerInformation: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState<TabName>("電力情報");
  const location = useLocation();
  const permission = location.state?.permission ?? 1;

  const breadcrumbItems = [
    { title: "レポート作成・管理", link: "/", className: "color-green-primar" },
    { title: "○○株式会社", link: "/" },
  ];

  return (
    <CommonLayout
      selectedTab={selectedTab}
      onTabChange={setSelectedTab}
      breadcrumbItems={breadcrumbItems}
      permission={permission}
      showConsentOrgSelector={permission === 1}
    >
      {selectedTab === "電力情報" && <PowerInformationContent />}
    </CommonLayout>
  );
};

const PowerInformationContent: React.FC = () => {
  const { agreementCategory, orgId } = useEbConsentSelection();
  const [localLoading, setLocalLoading] = useState(true);
  const [localData, setLocalData] = useState<listInfo[]>([]);
  const [localTotal, setLocalTotal] = useState(0);
  const [localError, setLocalError] = useState<string>("");

  const Columns: ColumnDef<listInfo>[] = [
    { accessorKey: "buildingName", header: "拠点名" },
    { accessorKey: "dataEntryPeriod", header: "情報登録期間" },
    { accessorKey: "fileUpdateDate", header: "情報更新日" },
  ];

  const formatDate = (yyyymmdd: string): string => {
    const parsed = parse(yyyymmdd, "yyyyMMdd", new Date());
    return format(parsed, "yyyy/MM/dd");
  };

  const formatFileUpdateDate = (dateTime: string): string => {
    if (!dateTime) {
      return "";
    }
    const normalized = dateTime.replace("T", " ").slice(0, 19);
    const parsed = parse(normalized, "yyyy-MM-dd HH:mm:ss", new Date());
    return format(parsed, "yyyy/MM/dd");
  };

  const [corporateNumber] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("corporateData");
      if (stored) {
        return JSON.parse(stored).corporate_number;
      }
    }
    return null;
  });

  useEffect(() => {
    const handleSearch = async () => {
      setLocalLoading(true);
      setLocalError("");
      try {
        let url = `/api/building/per_30min_data?corp_number=${corporateNumber}`;

        // 組織IDが利用可能な場合は追加
        if (orgId && orgId != "dummy") {
          url += `&org_id=${orgId}`;
        }

        // 同意書カテゴリが利用可能な場合は追加
        if (agreementCategory) {
          url += `&agreement_category=${agreementCategory}`;
        }

        console.log("calling:", url);
        const res = await getData(url) as ApiResponse;
        console.log(res);

        const convertedList: listInfo[] = res.result.upload_history.map(
          (item: UploadHistoryItem) => ({
            buildingName: item.building_name,
            dataEntryPeriod: `${formatDate(item.period_from)} ~ ${formatDate(
              item.period_to
            )}`,
            fileUpdateDate: formatFileUpdateDate(item.file_update_date),
          })
        );

        setLocalData(convertedList);
        setLocalTotal(convertedList.length);
      } catch (error: unknown) {
        console.error(error);
        const message =
          (error as { data?: { message: string } })?.data?.message ||
          (error as { message?: string })?.message ||
          (typeof error === "string" ? error : Messages.SYSTEM_ERROR);
        setLocalError(message);
        setLocalData([]);
        setLocalTotal(0);
      } finally {
        setLocalLoading(false);
      }
    };

    if (orgId && agreementCategory) {
      handleSearch();
    }
  }, [orgId, agreementCategory, corporateNumber]);

  return (
    <>
      <div className="px-16  pt-8">
        <div className="max-w-[1480px] pt-8">
          <ErrorHint message={localError} className="mb-4" bodyClassName="py-4" />
          {localLoading ? (
            <div className="text-center py-10">
              <p>データを読み込み中です...</p>
            </div>
          ) : (
            <Command>
              <CommandList>
                <PageableTable<listInfo, unknown>
                  columns={Columns}
                  data={localData}
                  pageCount={1}
                  totalCount={localTotal}
                  pageSizeOptions={[5, 10, 20, 50]}
                />
              </CommandList>
            </Command>)}
        </div>
      </div>
    </>
  );
};

export default PowerInformation;
