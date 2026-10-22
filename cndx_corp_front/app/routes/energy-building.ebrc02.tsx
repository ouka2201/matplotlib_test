// import { MetaFunction } from "@remix-run/node";
import { ColumnDef } from "@tanstack/react-table";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ErrorHint from "~/components/common/error-hint";
import { Icons } from "~/components/icons";
import CustomDialog from "~/components/modal/common-dialog";
import { Button } from "~/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Messages } from "~/constants/messages/message";
import CommonLayout from "../components/CommonLayout";
import { TabName } from "../components/tab-navigator";
import { PageableTable } from "../components/ui/pageable-table";
import { TableCell, TableRow } from "../components/ui/table";
import { getData, postData } from "../lib/fetch";
import "../styles/popup.css";

// export const meta: MetaFunction = () => {
//   return [{ title: "CNレポート作成_CNレポート作成条件指定" }, { name: "ebrc02", content: "popoup data" }];
// };

type CnKarteList = {
  karte_name: string; //カルテ名
  download_link: string | null; // ダウンロード
  report_created_at: string; // レポート作成日
  storage_period: string; // 保存期間
  report_save_path?: string | null; //レポート格納先
  org_name: string; //組織名
  thumbnail_base64: string;
  display_period: string;
  fiscal_year: string;
  created_date: string;
  fileUrl: string;
  fileName: string;
  report_period_start_year_month: string;
  report_period_end_year_month: string;
  registration_seq: number;
  report_status: ReportStatus; //レポートステータス
  queue_no?: number | null; //レポート作成待ち番号
  register_org_id: string;
  entry_draft_flag?: string;
  report_created_by_name: string; // レポート作成者の名前
};

type ReportStatus = "0" | "1" | "9" | null;

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

const ReportPopup: React.FC = () => {
  const [pdfList, setPdfList] = useState<CnKarteList[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showPopup, setshowPopup] = useState(false);
  const [showAcceptedDialog, setShowAcceptedDialog] = useState(false);
  const [years, setYears] = useState<string[]>([]);
  const [startYm, setStartYm] = useState<string>("");
  const [endYm, setEndYm] = useState<string>("");
  const [karteList, setKarteList] = useState<CnKarteList[]>([]);
  const [selectedTab, setSelectedTab] = useState<TabName>("CNカルテ");
  const [selectedYear, setSelectedYear] = useState("");
  const [selectedRegisterOrg, setSelectedRegisterOrg] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const permission = location.state?.permission ?? 1;
  const locationAgreementCategory = location.state?.agreementCategory as string | undefined;
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 3;
  const prevViewType = useRef<string>("");
  const [isCreating, setIsCreating] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const [listError, setListError] = useState("");
  const [acceptedDialogType, setAcceptedDialogType] = useState<"default" | "creating">("default");
  const [fiscalYear, setFiscalYear] = useState(""); // "2024"
  const [registrationSeq, setRegistrationSeq] = useState(0);
  const [agreementCategory, setAgreementCategory] = useState<string>("");
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const buildConsentKeys = useCallback(() => {
    if (typeof window === "undefined") return null;
    const sessionRaw = sessionStorage.getItem("session");
    if (!sessionRaw) return null;
    const sessionObj = JSON.parse(sessionRaw);
    const userId = sessionObj?.authorityInfo?.user_id ?? "unknownUser";
    const orgIdForKey = sessionObj?.authorityInfo?.org_id ?? "unknownOrg";
    const sessionId = sessionObj?.session_id ?? "noSessionId";
    const keyPrefix = `${sessionId}:${userId}:${orgIdForKey}:${permission}`;
    const stored = sessionStorage.getItem("corporateData");
    const corpNo = stored ? JSON.parse(stored).corporate_number : "";
    if (!corpNo) return null;
    return {
      corporateNumber: corpNo as string,
      catKey: `selectedAgreementCategory:${keyPrefix}:${corpNo}`,
      orgKey: `selectedOrgId:${keyPrefix}:${corpNo}`,
    };
  }, [permission]);

  // CommonLayout の選択（sessionStorage 新 key）変更を購読して、即時反映する
  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncFromSessionStorage = () => {
      const keys = buildConsentKeys();
      if (!keys) return;
      const cat = sessionStorage.getItem(keys.catKey) ?? "";
      const org = sessionStorage.getItem(keys.orgKey) ?? "";
      // location.state がある場合はそれを優先（画面遷移元から明示指定）
      setAgreementCategory(cat);
      setSelectedOrgId(org);
    };

    syncFromSessionStorage();

    const onConsentChanged = () => syncFromSessionStorage();
    window.addEventListener("consentSelectionChanged", onConsentChanged);
    // storage は別タブ対策（新 key は動的なので来たら再同期する）
    const onStorage = () => syncFromSessionStorage();
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("consentSelectionChanged", onConsentChanged);
      window.removeEventListener("storage", onStorage);
    };
  }, [buildConsentKeys]);

  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [showFull, setShowFull] = useState(false);

  const [viewType, setViewType] = useState<"grid" | "table">("grid");
  const isCreateDisabled = karteList.length > 0 && karteList.every((item) => item.entry_draft_flag === "1");

  const revokeBlobUrl = (url?: string | null) => {
    if (typeof window === "undefined" || !url) {
      return;
    }
    if (url.startsWith("blob:")) {
      URL.revokeObjectURL(url);
    }
  };

  useEffect(() => {
    return () => {
      revokeBlobUrl(pdfUrl);
    };
  }, [pdfUrl]);

  const handleCloseFullView = () => {
    revokeBlobUrl(pdfUrl);
    setPdfUrl(null);
    setShowFull(false);
  };

  const breadcrumbItems = [
    { title: "レポート作成・管理", link: "/", className: "color-green-primar" },
    { title: "○○株式会社", link: "/" },
  ];
  const totalPages = Math.ceil(pdfList.length / ITEMS_PER_PAGE);

  const paginatedPdfList = pdfList.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  const [token, setToken] = useState<string | null>(null);
  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
      }
    }
  }, []);

  // const getStatusLabel = (item: CnKarteList) => {
  //   switch (item.report_status) {
  //     case "0":
  //       return `作成中（待ち${item.queue_no}）`;
  //     case "1":
  //       return "ダウンロード";
  //     case "9":
  //       return "エラー";
  //     default:
  //       return "未作成";
  //   }
  // };
  const renderStatus = (item: CnKarteList) => {
    if (item.report_status === "0") {
      return (
        <div className="flex items-center space-x-1 whitespace-nowrap">
          <span>作成中</span>
          <Icons.spinner className="h-4 w-4 animate-spin" />
          <span>（待ち{item.queue_no ?? "-"}）</span>
        </div>
      );
    }

    if (item.report_status === "1") {
      return <span>ダウンロード</span>;
    }

    if (item.report_status === "9") {
      return <span>エラー</span>;
    }

    return <span>未作成</span>;
  };

  const customerData = location.state?.customerData;
  const [corporateNumber, setCorporateNumber] = useState<string>(() => {
    if (customerData?.corporate_number) {
      return customerData.corporate_number;
    }
    if (typeof window !== "undefined") {
      try {
        const stored = sessionStorage.getItem("corporateData");
        if (stored) {
          const parsed = JSON.parse(stored);
          return parsed?.corporate_number || "";
        }
      } catch (error) {
        console.error("Failed to initialize corporate data", error);
      }
    }
    return "";
  });

  useEffect(() => {
    if (customerData?.corporate_number) {
      setCorporateNumber(customerData.corporate_number);

      if (typeof window !== "undefined") {
        try {
          sessionStorage.setItem("corporateData", JSON.stringify(customerData));
        } catch (error) {
          console.error("Failed to persist corporate data", error);
        }
      }
      return;
    }

    if (typeof window !== "undefined") {
      try {
        const stored = sessionStorage.getItem("corporateData");
        if (stored) {
          const parsed = JSON.parse(stored);
          if (parsed?.corporate_number) {
            setCorporateNumber(parsed.corporate_number);
          }
        }
      } catch (error) {
        console.error("Failed to restore corporate data", error);
      }
    }
  }, [customerData]);

  // const corpNo = "2025052601002";
  const corpNo = corporateNumber;
  // const orgId = location.state?.orgId;
  const orgId = selectedOrgId;

  const formatYM = (ym?: string) => (ym && ym.length === 6 ? `${ym.slice(0, 4)}/${ym.slice(4, 6)}` : "―");

  const formatPeriodRange = (startYm?: string, endYm?: string) => {
    if (!startYm || !endYm) return "";
    return `${formatYM(startYm)}~${formatYM(endYm)}`;
  };

  // const fetchCo2List = async () => {
  const fetchCo2List = useCallback(async () => {
    // if (!corpNo || !agreementCategory) {
    if (!corpNo || !agreementCategory || !orgId) {
      return;
    }
    type AuthResponse = {
      cn_karte_list: CnKarteList[];
    };

    try {
      setIsLoading(true);
      const params = new URLSearchParams({
        corporate_number: corpNo,
        org_id: orgId,
        agreement_category: agreementCategory,
      });
      const url = `/api/report/cn-karte/list?${params.toString()}`;
      console.log(Messages.VALIDATION.data.sent_url, url);
      const raw = await getData(url);

      console.log(Messages.VALIDATION.data.raw, raw);
      const data = raw as AuthResponse;

      const sortedList = [...data.cn_karte_list]
        .sort((a, b) => {
          return new Date(b.report_created_at).getTime() - new Date(a.report_created_at).getTime();
        })
        .map((item) => ({
          ...item,
          report_created_at: item.report_created_at.split(" ")[0],
        }));
      setKarteList(sortedList);

      const allYears = sortedList
        .filter((item) => item.entry_draft_flag !== "1")
        .map((item) =>
          item.fiscal_year && item.registration_seq ? `${item.fiscal_year}-${item.registration_seq}` : null,
        )
        .filter((val): val is string => val !== null);

      // null 念のためundefinedも除外
      const filteredList = sortedList.filter((item) => item.report_status != null);
      setPdfList(filteredList);

      setYears(allYears);

      // setHasFetched(true);
      setListError("");
    } catch (error) {
      console.error(Messages.VALIDATION.api.error, error);
      setListError(Messages.SYSTEM_ERROR);
    } finally {
      setIsLoading(false);
    }
    // };
  }, [corpNo, agreementCategory, orgId]);

  const handleYearChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const year = e.target.value;
    setSelectedYear(year);

    const [yearStr, seqStr] = year.split("-");
    setFiscalYear(yearStr);
    setRegistrationSeq(Number(seqStr));

    const matched = karteList.find((item) => item.fiscal_year === yearStr && item.registration_seq === Number(seqStr));

    if (matched) {
      setStartYm(matched.report_period_start_year_month);
      setEndYm(matched.report_period_end_year_month);
      setSelectedRegisterOrg(matched.register_org_id);
    } else {
      setStartYm("");
      setEndYm("");
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedYear) {
      navigate("/report", { state: { year: selectedYear } });
      return;
    }

    const pdfMade = {
      corporate_number: corpNo,
      fiscal_year: fiscalYear,
      org_id: selectedRegisterOrg,
      registration_seq: registrationSeq,
      agreement_category: agreementCategory,
    };

    setshowPopup(false);
    setAcceptedDialogType("default");
    setShowAcceptedDialog(true);

    setIsCreating(true);
    setErrorMessage("");

    try {
      await postData("/api/report/cn-karte/create", pdfMade);
      await fetchCo2List();
      setshowPopup(false);
      resetForm();
    } catch (error: any) {
      console.error(Messages.VALIDATION.api.error, error);
      let message: string | string[] = Messages.VALIDATION.api.error;
      if (error instanceof Response) {
        try {
          const data = await error.json();
          message = data?.message || data?.description || data?.error || message;
        } catch {
          message = error.statusText || message;
        }
      } else if (error?.data) {
        const data = error.data;
        message = data?.message || data?.description || data?.error || message;
      } else if (error?.message) {
        message = error.message;
      }
      setErrorMessage(message);

      setshowPopup(false);
    } finally {
      setIsCreating(false);
      setIsLoading(false);
    }
  };
  const handleClosePopup = () => {
    setshowPopup(false);
    setErrorMessage("");
    setIsCreating(false);
  };

  const resetForm = () => {
    setSelectedYear("");
    setStartYm("");
    setEndYm("");
    setErrorMessage("");
    setIsCreating(false);
  };

  const buildCnKarteDownloadUrl = (report_save_path: string) => {
    const params = new URLSearchParams({
      file_path: report_save_path,
    });
    return `/api/file/file-download?${params.toString()}`;
  };

  const PdfViewer = ({
    pdfList,
    corporateNumber,
    // agreementCategory,
    orgId,
  }: {
    pdfList: CnKarteList[];
    corporateNumber: string;
    // agreementCategory: string;
    orgId: string;
  }) => {
    // const [fullViewUrl, setFullViewUrl] = useState<string>("");

    const handleDownload = async (report_save_path: string) => {
      try {
        setDownloadingId(report_save_path);
        const url = buildCnKarteDownloadUrl(report_save_path);
        const response = await getData(url, {
          Authorization: `Bearer ${token}`,
        });
        if (!response.ok) {
          throw new Error("ファイルの取得に失敗しました");
        }

        const blob = await response.blob();

        // --- ファイル名の取得 ---
        let fileName = `CNカルテ_${fiscalYear}.pdf`; // フォールバック
        const cd = response.headers.get("content-disposition");
        if (cd) {
          const m = /filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i.exec(cd);
          fileName = decodeURIComponent(m?.[1] || m?.[2] || fileName);
        }

        // --- ダウンロード処理 ---
        const urlObject = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = urlObject;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(urlObject);
        console.log(Messages.PDF_DOWNLOAD_SUCCESS);
      } catch (error) {
        console.error(Messages.VALIDATION.api.error);
      } finally {
        setDownloadingId(null);
      }
    };

    const handleFullView = async (report_save_path: string) => {
      try {
        setPreviewingId(report_save_path);
        const url = buildCnKarteDownloadUrl(report_save_path);
        const response = await getData(url, {
          Authorization: `Bearer ${token}`,
        });

        if (!response.ok) {
          throw new Error("ファイルの取得に失敗しました");
        }

        const blob = await response.blob();

        const urlObject = URL.createObjectURL(blob);
        revokeBlobUrl(pdfUrl);
        setPdfUrl(urlObject);
        setShowFull(true);
      } catch (error) {
        alert(Messages.VALIDATION.api.error);
      } finally {
        setPreviewingId(null);
      }
    };
    const formatLocalDate = (dateStr: string) => {
      const date = new Date(dateStr);
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, "0");
      const dd = String(date.getDate()).padStart(2, "0");
      return `${yyyy}/${mm}/${dd}`;
    };

    const columns: ColumnDef<CnKarteList>[] = [
      {
        header: "カルテ名",
        accessorFn: (row) =>
          row.report_period_start_year_month && row.report_period_end_year_month
            ? `${formatPeriodRange(row.report_period_start_year_month, row.report_period_end_year_month)}のCNカルテ`
            : "",
      },
      {
        header: "情報登録年",
        accessorKey: "fiscal_year",
      },
      {
        header: "作成組織",
        accessorKey: "org_name",
      },
      {
        header: "作成者",
        accessorKey: "report_created_by_name",
      },
      {
        header: "作成日",
        accessorKey: "report_created_at",
      },
      {
        header: "保存期間",
      },
      {
        header: "",
        id: "status",
      },
      {
        header: "",
        id: "actions",
        cell: () => null,
      },
    ];
    useEffect(() => {
      if (prevViewType.current && prevViewType.current !== viewType && viewType === "grid") {
        setCurrentPage(1);
      }
      prevViewType.current = viewType;
    }, [viewType]);

    return (
      <>
        <div className="view-toggle" style={{ marginBottom: "16px", display: "flex", gap: 0 }}>
          <button
            onClick={() => setViewType("grid")}
            style={{
              backgroundColor: viewType === "grid" ? "#e0e0e0" : "transparent",
              border: "none",
              cursor: "pointer",
              borderRadius: "4px",
            }}
          >
            <img src="/assets/icons/grid.svg" alt="Grid View" />
          </button>
          <button
            onClick={() => setViewType("table")}
            style={{
              backgroundColor: viewType === "table" ? "#e0e0e0" : "transparent",
              border: "none",
              cursor: "pointer",
              borderRadius: "4px",
            }}
          >
            <img src="/assets/icons/list.svg" alt="Grid View" />
          </button>
        </div>

        {viewType === "grid" ? (
          <>
            <div className="flex flex-wrap gap-8">
              {paginatedPdfList.map((item, index) => (
                <div
                  key={index}
                  className="relative w-[350px] h-[560px] p-1 border border-gray-300 rounded-lg overflow-hidden bg-white box-border transform-gpu"
                >
                  <div className="karte-info" style={{ lineHeight: "1.8", paddingLeft: "20px" }}>
                    <div className="title-bold">
                      {item.report_period_start_year_month && item.report_period_end_year_month
                        ? `${formatPeriodRange(
                          item.report_period_start_year_month,
                          item.report_period_end_year_month,
                        )}のCNカルテ`
                        : ""}
                    </div>
                    <hr />
                    <div className="title" style={{ fontSize: "10px" }}>
                      情報登録年：{item.fiscal_year}-
                      {item.registration_seq}
                    </div>
                    <div className="title" style={{ fontSize: "10px" }}>
                      作成組織：{item.org_name}
                    </div>
                    <div className="title" style={{ fontSize: "10px" }}>
                      作成者：{item.report_created_by_name}
                    </div>
                    <div className="title" style={{ fontSize: "10px" }}>
                      作成日：
                      {item.report_created_at ? formatLocalDate(item.report_created_at) : ""}
                    </div>
                    <div className="title" style={{ fontSize: "10px" }}>
                      保存期間：
                      {item.report_created_at
                        ? (() => {
                          const start = new Date(item.report_created_at);
                          const end = new Date(item.report_created_at);
                          end.setFullYear(end.getFullYear() + 5);
                          end.setDate(end.getDate() - 1);
                          return `${formatLocalDate(start.toISOString())} ~ ${formatLocalDate(end.toISOString())}`;
                        })()
                        : ""}
                    </div>
                  </div>

                  <div style={{ lineHeight: "1.8", paddingLeft: "20px" }}>
                    {item.thumbnail_base64 && (
                      <img
                        src={`data:image/png;base64,${item.thumbnail_base64}`}
                        alt="pdf preview"
                        width="100%"
                        style={{
                          display: "block",
                          width: "90%",
                          height: "380px",
                          objectFit: "contain",
                          border: "1px solid #ccc",
                          boxSizing: "border-box",
                        }}
                      />
                    )}
                  </div>

                  <div className="pdf-footer">
                    <button
                      className={`w-[140px] flex items-center justify-end space-x-1 text-[12px]
                               ${item.report_status === "0" || item.report_status === "9"
                          ? "text-red-600 cursor-pointer"
                          : item.report_status === "1"
                            ? "text-teal-700 cursor-pointer"
                            : "text-gray-400 cursor-pointer"
                        }
                               `}
                      onClick={() => {
                        if (item.report_status === "0") {
                          setAcceptedDialogType("creating");
                          setShowAcceptedDialog(true);
                          return;
                        }
                        if (item.report_status === "1") {
                          handleDownload(item.report_save_path ?? "");
                        }
                      }}
                    >
                      {/* 作成済 */}
                      {item.report_status === "1" && (
                        <svg className="w-4 h-4">
                          <use href="/assets/icons/download.svg#icon-download" />
                        </svg>
                      )}

                      <span>{renderStatus(item)}</span>
                    </button>
                    {item.report_status === "1" && item.report_save_path && (
                      <button
                        className="max-w-[120px] flex items-center space-x-1 text-[12px] text-teal-700"
                        onClick={() => handleFullView(item.report_save_path ?? "")}
                      >
                        {/* {previewingId === item.report_save_path && (
                        <Icons.spinner className="mr-1 size-4 animate-spin" aria-hidden="true" />
                      )} */}
                        <svg className="w-4 h-4">
                          <use href="/assets/icons/fullscreen.svg#icon-fullscreen" />
                        </svg>
                        <span>全画面表示</span>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-center gap-2 mt-4">
              <button
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className="px-2 py-1 border rounded disabled:opacity-50"
              >
                &lt;
              </button>
              {Array.from({ length: totalPages }).map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentPage(i + 1)}
                  className={`w-8 h-8 text-center rounded ${currentPage === i + 1 ? "bg-gray-300 font-bold" : "bg-white border"
                    }`}
                >
                  {i + 1}
                </button>
              ))}
              <button
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="px-2 py-1 border rounded disabled:opacity-50"
              >
                &gt;
              </button>
            </div>
          </>
        ) : (
          <PageableTable
            columns={columns}
            data={pdfList}
            totalCount={pdfList.length}
            pageCount={Math.ceil(pdfList.length / 10)}
            renderRow={(item, index) => (
              <TableRow key={index}>
                <TableCell>
                  {item.report_period_start_year_month && item.report_period_end_year_month
                    ? `${formatPeriodRange(
                      item.report_period_start_year_month,
                      item.report_period_end_year_month,
                    )}のCNカルテ`
                    : ""}
                </TableCell>

                <TableCell className="w-[10%]">
                  {item.fiscal_year}-{item.registration_seq}
                </TableCell>
                <TableCell>{item.org_name}</TableCell>
                <TableCell>{item.report_created_by_name}</TableCell>
                <TableCell>{item.report_created_at ? formatLocalDate(item.report_created_at) : ""}</TableCell>
                <TableCell>
                  {item.report_created_at
                    ? (() => {
                      const start = new Date(item.report_created_at);
                      const end = new Date(item.report_created_at);
                      end.setFullYear(end.getFullYear() + 5);
                      end.setDate(end.getDate() - 1);
                      return `${formatLocalDate(start.toISOString())} ~ ${formatLocalDate(end.toISOString())}`;
                    })()
                    : ""}
                </TableCell>
                <TableCell>
                  <button
                    className={`flex items-center justify-start space-x-1 text-[12px]
                              ${item.report_status === "0" || item.report_status === "9"
                        ? "text-red-600 cursor-pointer"
                        : item.report_status === "1"
                          ? "text-teal-700 cursor-pointer"
                          : "text-gray-400 cursor-pointer"
                      }
                             `}
                    onClick={() => {
                      if (item.report_status === "0") {
                        setAcceptedDialogType("creating");
                        setShowAcceptedDialog(true);
                        return;
                      }
                      if (item.report_status === "1") {
                        handleDownload(item.report_save_path ?? "");
                      }
                    }}
                  >
                    {item.report_status === "1" && (
                      <svg className="w-4 h-4">
                        <use href="/assets/icons/download.svg#icon-download" />
                      </svg>
                    )}

                    <span>{renderStatus(item)}</span>
                  </button>
                </TableCell>
                <TableCell>
                  {item.report_status === "1" && item.report_save_path && (
                    <button
                      className="max-w-[120px] flex items-center space-x-1 text-[12px] text-teal-700"
                      onClick={() => handleFullView(item.report_save_path ?? "")}
                    >
                      {/* {previewingId === item.report_save_path && (
                      <Icons.spinner className="mr-1 size-4 animate-spin" aria-hidden="true" />
                    )} */}
                      <svg className="w-4 h-4">
                        <use href="/assets/icons/fullscreen.svg#icon-fullscreen" />
                      </svg>
                      <span>全画面表示</span>
                    </button>
                  )}
                </TableCell>
              </TableRow>
            )}
          />
        )}

        {showFull && (
          <div className="pdf-modal">
            <div className="modal-content">
              <div style={{ position: "relative" }}>
                <button onClick={handleCloseFullView} className="fixed top-4 right-4 z-50 text-white ">
                  × 閉じる
                </button>
              </div>

              <iframe src={pdfUrl ?? ""} title="PDF View" className="full-pdf-frame"></iframe>
            </div>
          </div>
        )}
      </>
    );
  };

  useEffect(() => {
    if (selectedTab !== "CNカルテ") return;
    if (!corpNo) return;
    // 選択が未決定のときは検索しない（APIエラー回避）
    if (!agreementCategory || !orgId) return;
    fetchCo2List();
  }, [selectedTab, corpNo, agreementCategory, orgId, fetchCo2List]);

  // const handleDownloadAll = async () => {
  //   if (!pdfList.length) return;

  //   try {
  //     for (const item of pdfList) {
  //       if (!item.report_save_path) continue;

  //       const url = buildCnKarteDownloadUrl(item.report_save_path);
  //       const response = await getData(url, {
  //         Authorization: `Bearer ${token}`,
  //       });

  //       if (!response.ok) {
  //         console.error("ダウンロード失敗:", item.report_save_path);
  //         continue;
  //       }

  //       const blob = await response.blob();

  //       // ファイル名の取得（単体ダウンロードと同一ロジック）
  //       let fileName = `CNカルテ_${item.fiscal_year}.pdf`;
  //       const cd = response.headers.get("content-disposition");
  //       if (cd) {
  //         const m = /filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i.exec(cd);
  //         fileName = decodeURIComponent(m?.[1] || m?.[2] || fileName);
  //       }

  //       // ダウンロードを実行
  //       const urlObject = URL.createObjectURL(blob);
  //       const a = document.createElement("a");
  //       a.href = urlObject;
  //       a.download = fileName;
  //       document.body.appendChild(a);
  //       a.click();
  //       a.remove();
  //       URL.revokeObjectURL(urlObject);

  //       // ブラウザのダウンロード制限を回避するため、少し待機
  //       await new Promise((resolve) => setTimeout(resolve, 300));
  //     }

  //     console.log("すべてのレポートのダウンロードが完了しました");
  //   } catch (error) {
  //     console.error("すべてのレポートのダウンロードエラー", error);
  //     alert(Messages.VALIDATION.api.error);
  //   }
  // };

  return (
    <CommonLayout
      selectedTab={selectedTab}
      onTabChange={setSelectedTab}
      breadcrumbItems={breadcrumbItems}
      permission={permission}
      showConsentOrgSelector={permission === 1}
    >
      {errorMessage && <ErrorHint message={errorMessage} className="w-4/5" />}
      <div className="px-16 py-10">
        {selectedTab === "CNカルテ" && (
          <div>
            <div style={{ flexGrow: 1 }}>
              {isLoading ? (
                <p>読み込み中...</p>
              ) : pdfList.length === 0 ? (
                <>
                  <div className="max-w-[1480px] h-[420px] bg-white rounded-lg shadow flex flex-col items-center justify-center">
                    <div className="flex flex-col items-center justify-center h-full">
                      <div className="text-base font-semibold mb-6">CNカルテは未作成です</div>
                      <Button
                        className=" px-4 py-2 text-[14px]"
                        onClick={() => setshowPopup(true)}
                      // className="create-button"
                      >
                        カルテの作成
                      </Button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="max-w-[1480px] max-w-screen w-full h-screen flex flex-col justify-start bg-transparent border-0">
                  <div className="button-wrapper">
                    <Button onClick={fetchCo2List} style={{ fontSize: "14px" }}>
                      画面の更新
                    </Button>
                    <Button
                      onClick={() => setshowPopup(true)}
                      style={{ fontSize: "14px" }}
                      disabled={isCreateDisabled}
                      className="disabled:cursor-not-allowed disabled:bg-[#EAECF0] disabled:text-gray-400"
                    >
                      カルテの作成
                    </Button>
                    {/* <Button
                      onClick={handleDownloadAll}
                      style={{
                        width: "230px",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "8px",
                        padding: "6px 16px",
                        fontSize: "14px",
                        color: "#00897b",
                        border: "1px solid #00897b",
                        background: "transparent",
                        borderRadius: "4px",
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                      }}
                    >
                      <svg className="w-4 h-4">
                        <use href="/assets/icons/download.svg#icon-download" />
                      </svg>
                      すべてのレポートダウンロード
                    </Button> */}
                  </div>

                  <PdfViewer
                    pdfList={pdfList}
                    corporateNumber={corpNo}
                    // agreementCategory={agreementCategory ?? ""}
                    orgId={orgId ?? ""}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        <CustomDialog
          title="CNカルテの作成"
          description="情報登録年を選択してください。"
          open={showPopup}
          size="lg"
          onOpenChange={(open) => {
            if (!open && isCreating) return;
            if (!open) {
              handleClosePopup();
              resetForm();
            } else {
              setErrorMessage("");
              setListError("");
              setshowPopup(true);
            }
          }}
          onClose={() => console.log("モーダル閉じた")}
          // className="w-fit h-[400px]"
          className="w-fit h-auto"
          footer={
            <>
              <Button
                variant="third"
                size="third"
                className="border border-solid"
                onClick={() => {
                  handleClosePopup();
                  resetForm();
                }}
                disabled={isCreating}
              >
                キャンセル
              </Button>
              <Button variant="primary" size="second" onClick={handleGenerateReport} disabled={!selectedYear || isCreating}>
                作成
              </Button>
            </>
          }
        >
          <div className="relative">
            {isCreating && (
              <div className="fixed inset-0 z-[9999] bg-black/20 flex items-center justify-center cursor-not-allowed">
                <div className="bg-white shadow-lg rounded-lg p-6 max-w-md w-full border border-gray-200 text-center">
                  <p className="text-gray-800 text-lg font-semibold mb-2">
                    CNカルテ作成中
                    <LoadingDots />
                  </p>
                  <p className="text-gray-600 text-sm">2～3分ほどかかります、しばらくお待ちください</p>
                </div>
              </div>
            )}

            <div>

              <div className="popup-label">情報登録年</div>
              <Select
                value={selectedYear}
                onValueChange={(v) => {
                  setErrorMessage("");
                  setSelectedYear(v);
                  handleYearChange({ target: { value: v } } as any);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="選択してください" />
                </SelectTrigger>

                <SelectContent position="popper" side="bottom" sideOffset={8} className="z-[1000] text-slate-700">
                  {Array.from(new Set(years)).map((y) => (
                    <SelectItem key={y} value={String(y)} className="text-slate-700">
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {startYm && endYm && (
                <div className="text-gray-600 font-semibold text-sm mt-1">
                  情報登録期間：{formatYM(startYm)}〜{formatYM(endYm)}
                </div>
              )}
            </div>
          </div>
        </CustomDialog>
        <CustomDialog
          title=" "
          open={showAcceptedDialog}
          onOpenChange={setShowAcceptedDialog}
          size="sm"
          className="w-[500px] h-[300px]"
          footer={
            <div className="flex justify-center w-full">
              <Button variant="primary" onClick={() => setShowAcceptedDialog(false)}>
                OK
              </Button>
            </div>
          }
        >
          <div className="flex flex-col items-center text-center gap-3 py-6">
            <span className="text-base whitespace-pre-line">
              {acceptedDialogType === "creating"
                ? Messages.energy_building.ebrc01.cn_karte_creating
                : Messages.energy_building.ebrc01.create_request_accepted}
            </span>
            <span className="text-base text-red-600 leading-relaxed">
              {Messages.energy_building.ebrc06.create_request_note}
            </span>
          </div>
        </CustomDialog>
        <CustomDialog
          title=" "
          open={showAcceptedDialog}
          onOpenChange={setShowAcceptedDialog}
          size="sm"
          className="w-[500px] h-[300px]"
          footer={
            <div className="flex justify-center w-full">
              <Button variant="primary" onClick={() => setShowAcceptedDialog(false)}>
                OK
              </Button>
            </div>
          }
        >
          <div className="flex flex-col items-center text-center gap-3 py-6">
            <span className="text-base whitespace-pre-line">
              {/* {acceptedDialogType === "creating"
                ? Messages.energy_building.ebrc01.cn_karte_creating
                : Messages.energy_building.ebrc01.create_request_accepted} */}
              {Messages.energy_building.ebrc01.cn_karte_creating}
            </span>
            {/* <span className="text-base text-red-600 leading-relaxed">
              {Messages.energy_building.ebrc06.create_request_note}
            </span> */}
          </div>
        </CustomDialog>
      </div>
    </CommonLayout>
  );
};

export default ReportPopup;
