// MetaFunction を利用する際は下記インポートを有効化する
import { ColumnDef } from "@tanstack/react-table";
// import { addMonths, format, parse, subMonths } from "date-fns";
import { FC, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Icon from "~/components/icon";
import { Icons } from "~/components/icons";
import CustomDialog from "~/components/modal/common-dialog";
import Text from "~/components/text";
import { Button } from "~/components/ui/button";
import { Messages } from "~/constants/messages/message";
import { useEbConsentSelection } from "~/hooks/useEbConsentSelection";
import { usePeriod12Months } from "~/hooks/usePeriod12Months";
import { baseSchema } from "~/lib/validations/ebrc";
import CommonLayout from "../components/CommonLayout";
import ErrorHint from "../components/common/error-hint";
import { TabName } from "../components/tab-navigator";
import { PageableTable } from "../components/ui/pageable-table";
import { TableCell, TableRow } from "../components/ui/table";
import { getData, postData } from "../lib/fetch";
import "../styles/popup.css";

// export const meta: MetaFunction = () => {
//   return [{ title: "電力見える化レポート" }, { name: "ebrc06", content: "" }];
// };

type OptionResponse = {
  building_list: {
    building_id: string;
    building_name: string;
    contracted_power: string | null;
  }[];
  target_months: string[];
  // そのほかのフィールドは省略
};

type ReportStatus = "0" | "1" | "9";

type CnKarteList = {
  building_name: string; // 建物名
  corporate_number: string; // 法人番号（13桁）
  org_id: string; // 組織ID
  report_classify: string; // レポート分類
  report_created_at: string | null; // レポート作成日時
  target_month: string; // レポート対象期間の開始年月
  target_period?: string; // レポート対象期間（表示用）
  report_period_end_year_month: string; // レポート対象期間の終了年月
  report_save_path: string | null; // レポート（PDF）の保存パス
  thumbnail_base64: string;
  org_name: string;
  report_name: string; //拠点名
  report_status: ReportStatus; //レポートステータス
  queue_no?: number | null; //レポート作成待ち番号
  report_created_by_id: string; // レポート作成者のユーザーID
  report_created_by_name: string; // レポート作成者の名前
};

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
}

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

type InnerProps = {
  onConsentChange?: (agreementCategory: string, orgId: string) => void;
};

const ReportPopupTest: FC<InnerProps> = ({ onConsentChange }) => {
  const { agreementCategory, orgId } = useEbConsentSelection();

  // hookの値が変化したとき、親コンポーネント ReportPopup に通知する
  useEffect(() => {
    if (onConsentChange) {
      onConsentChange(agreementCategory, orgId);
    }
  }, [agreementCategory, orgId]);

  return <div></div>;
};

const ReportPopup: React.FC = () => {
  const [agreementCategory, setAgreementCategory] = useState("");
  const [orgId, setOrgId] = useState("");

  const [message, setMessage] = useState("");
  const [pageError, setPageError] = useState<string>("");

  const [selectedBuildingId, setSelectedBuildingId] = useState<string>("");
  const [optionResponse, setOptionResponse] = useState<OptionResponse>({
    building_list: [],
    target_months: [],
  });
  const [pdfList, setPdfList] = useState<CnKarteList[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showPopup, setshowPopup] = useState(false);
  const [showAcceptedDialog, setShowAcceptedDialog] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);
  const fetchedRef = useRef(false);
  const [selectedTab, setSelectedTab] = useState<TabName>("電力見える化レポート");
  const [fiscalYear, setFiscalYear] = useState(""); // 会計年度を保存
  const [targetMonths, setTargetMonths] = useState<{ label: string; value: string }[]>([]);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [listError, setListError] = useState("");
  const [acceptedDialogType, setAcceptedDialogType] = useState<"default" | "creating">("default");
  const [showMonthSelector, setShowMonthSelector] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const permission = location.state?.permission ?? 1;
  const locationState = location.state as LocationState | undefined;
  const customerData = locationState?.customerData;
  const period = usePeriod12Months({
    schema: baseSchema,
  });
  const [corpNo, setCorpNo] = useState<string>(() => {
    if (customerData?.corporate_number) {
      return customerData.corporate_number;
    }
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("corporateData");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed?.corporate_number) {
            return parsed.corporate_number;
          }
        } catch (error) {
          console.warn("Failed to parse corporateData from sessionStorage", error);
        }
      }
    }
    return "";
  });

  useEffect(() => {
    if (!customerData?.corporate_number) {
      return;
    }
    setCorpNo(customerData.corporate_number);
    try {
      sessionStorage.setItem("corporateData", JSON.stringify(customerData));
    } catch (error) {
      console.warn("Failed to persist corporateData to sessionStorage", error);
    }
  }, [customerData]);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");

  const [contractPower, setContractPower] = useState("");

  const prevViewType = useRef<string>("");
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 3;

  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [viewType, setViewType] = useState<"grid" | "table">("grid");
  const [showFull, setShowFull] = useState(false);

  const totalPages = Math.ceil(pdfList.length / ITEMS_PER_PAGE);

  const [token, setToken] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
        setUserId(JSON.parse(sessionData).email);
      }
    }
  }, []);
  const handleBuildingChange = (buildingId: string) => {
    setSelectedBuildingId(buildingId);
    setContractPower("");
  };

  const breadcrumbItems = [
    { title: "レポート作成・管理", link: "/", className: "color-green-primar" },
    { title: "○○株式会社", link: "/" },
  ];

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
        <>
          <span>作成中</span>
          <Icons.spinner className="h-4 w-4 animate-spin" aria-hidden="true" />
          <span>（待ち{item.queue_no ?? "-"}）</span>
        </>
      );
    }

    if (item.report_status === "1") {
      return <>ダウンロード</>;
    }

    if (item.report_status === "9") {
      return <>エラー</>;
    }

    return <>未作成</>;
  };

  const formatDate = (dateStr: string | Date): string => {
    const d = new Date(dateStr);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${yyyy}/${mm}/${dd}`;
  };

  const formatTargetPeriod = (targetPeriod?: string, targetMonth?: string): string => {
    const tryFormatRange = (value?: string): string | null => {
      if (!value) return null;
      const trimmed = value.trim();
      if (!trimmed) return null;

      // 既にフォーマット済み（例: "2025/12～2026/11"）
      if (trimmed.includes("～") || trimmed.includes("〜")) {
        return trimmed;
      }

      const digits = trimmed.replace(/\D/g, "");
      if (digits.length !== 6) {
        return trimmed;
      }

      const startYear = parseInt(digits.slice(0, 4), 10);
      const startMonth = parseInt(digits.slice(4, 6), 10);
      if (!startYear || startMonth < 1 || startMonth > 12) {
        return trimmed;
      }

      const startLabel = `${startYear}/${String(startMonth).padStart(2, "0")}`;
      const endDate = new Date(startYear, startMonth - 1);
      endDate.setMonth(endDate.getMonth() + 11);
      const endYear = endDate.getFullYear();
      const endMonth = endDate.getMonth() + 1;

      return `${startLabel}～${endYear}/${String(endMonth).padStart(2, "0")}`;
    };

    return tryFormatRange(targetPeriod) ?? tryFormatRange(targetMonth) ?? "未設定";
  };

  const paginatedPdfList = pdfList.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  useEffect(() => {
    if (
      selectedTab === "電力見える化レポート" &&
      //!fetchedRef.current &&
      corpNo &&
      orgId &&
      agreementCategory
    ) {
      //fetchedRef.current = true;

      fetchCo2List();
    }
  }, [selectedTab, hasFetched, corpNo, orgId, agreementCategory]);
  // 例: const orgId = "10001";

  const fetchCo2List = async () => {
    type AuthResponse = {
      power_report_list: CnKarteList[];
    };

    if (!corpNo || !orgId || !agreementCategory) return;

    try {
      const params = new URLSearchParams({
        corporate_number: corpNo,
        org_id: orgId,
        agreement_category: agreementCategory,
      });
      const url = `/api/report/power-report/list?${params.toString()}`;
      console.log(Messages.VALIDATION.data.sent_url, url);
      const raw = await getData(url);

      const data = raw as AuthResponse;
      setPdfList(data.power_report_list);
      setListError("");
    } catch (error) {
      console.error(Messages.VALIDATION.api.error, error);
      setListError(Messages.SYSTEM_ERROR);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setSubmitError("");
    if (!isFormValid || !agreementCategory || !orgId) {
      navigate("/report", { state: {} });
      return;
    }

    setSubmitting(true);

    setshowPopup(false);
    setAcceptedDialogType("default");
    setShowAcceptedDialog(true);

    // 会計年度として保存された値を使用（ユーザーが最初に入力した開始年）
    const fiscalYearValue = fiscalYear.trim();

    const pdfMade = {
      user_id: userId,
      corporate_number: corpNo,
      org_id: orgId,
      // 利用しない場合は fiscal_year をコメントアウト
      fiscal_year: fiscalYearValue,
      target_month: selectedMonth,
      building_id: selectedBuildingId,
      month_from: period.formData.startMonth.padStart(2, "0"),
      report_classify: "6",
      agreement_category: agreementCategory,
      contracted_power: contractPower,
    };
    try {
      console.log(Messages.energy_building.ebrc06.sent_parameter, pdfMade);

      await postData("/api/report/electric_vis/create", pdfMade);

      type AuthResponse = {
        power_report_list: CnKarteList[];
      };

      try {
        const params = new URLSearchParams({
          corporate_number: corpNo,
          org_id: orgId,
          agreement_category: agreementCategory,
        });
        const url = `/api/report/power-report/list?${params.toString()}`;
        console.log(Messages.VALIDATION.data.sent_url, url);
        const raw = await getData(url);
        console.log(Messages.VALIDATION.data.raw, raw);
        const data = raw as AuthResponse;

        setPdfList(data.power_report_list);
        // 必要に応じて setHasFetched(true); を再度実行
      } catch (error) {
        console.error(Messages.VALIDATION.api.error, error);
        setListError(Messages.SYSTEM_ERROR);
      } finally {
        setIsLoading(false);
        setSubmitting(false);
      }
    } catch (error: any) {
      console.error(Messages.energy_building.ebrc06.create_pdf_error, error);

      let message: string = Messages.energy_building.ebrc06.create_pdf_error;

      if (error instanceof Response) {
        try {
          const data = await error.json();
          console.error(Messages.VALIDATION.api.error, data);
          message = data.description || data.message || JSON.stringify(data);
        } catch (e) {
          message = error.statusText || Messages.SYSTEM_ERROR;
        }
      } else if (error.message) {
        message = error.message;
      }

      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const PdfViewer = ({ pdfList }: { pdfList: CnKarteList[]; corporateNumber: string }) => {
    const handleFullView = async (reportSavePath: string) => {
      if (!reportSavePath) {
        setErrorMessage(Messages.energy_building.ebrc06.file_none);
        return;
      }
      try {
        setPreviewingId(reportSavePath);
        const url = `/api/file/file-download?file_path=${encodeURIComponent(reportSavePath)}`;
        const response = await getData(url);

        const blob = await response.blob();

        // --- DataURLへ変換 ---
        const reader = new FileReader();
        reader.onload = () => {
          setPdfUrl(reader.result as string); // ← DataURL を state に入れる
          setShowFull(true);
        };
        reader.readAsDataURL(blob);
      } catch (error) {
        setErrorMessage(Messages.VALIDATION.api.error);
      } finally {
        setPreviewingId(null);
      }
    };

    // PDFファイルをダウンロードする
    const handleDownload = async (reportSavePath: string) => {
      if (!reportSavePath) {
        setErrorMessage(Messages.energy_building.ebrc06.download_file_none);
        return;
      }
      try {
        setDownloadingId(reportSavePath);
        // APIを呼ぶ
        const url = `/api/file/file-download?file_path=${encodeURIComponent(reportSavePath)}`;
        const response = await getData(url);

        const blob = await response.blob();

        // --- ファイル名の取得 ---
        let fileName = `report.pdf`; // フォールバック
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
        console.error(error);
        setErrorMessage(Messages.energy_building.ebrc06.pdf_download_failed);
      } finally {
        setDownloadingId(null);
      }
    };

    const columnsA: ColumnDef<CnKarteList>[] = [
      {
        header: "拠点名",
      },
      {
        header: "レポート名",
      },
      {
        header: "対象期間",
        accessorKey: "target_period",
      },
      {
        header: "作成組織",
        accessorKey: "org_name",
      },
      {
        header: "作成者",
      },
      {
        header: "作成日",
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
                    <div className="my-4">
                      <div className="title" style={{ fontSize: "10px" }}>
                        {item.building_name}
                      </div>
                      <div className="title-bold">
                        {item.report_name}
                      </div>
                    </div>
                    <hr />
                    <div>
                      <div className="title" style={{ fontSize: "10px" }}>
                        対象期間：
                        {formatTargetPeriod(item.target_period, item.target_month)}
                      </div>
                      <div className="title" style={{ fontSize: "10px" }}>
                        作成組織：
                        {item.org_name}
                      </div>
                      <div className="title" style={{ fontSize: "10px" }}>
                        作成者：
                        {item.report_created_by_name}
                      </div>
                      <div className="title" style={{ fontSize: "10px" }}>
                        作成日：
                        {item.report_created_at ? formatDate(item.report_created_at) : "未作成"}
                      </div>
                      <div className="title" style={{ fontSize: "10px" }}>
                        保存期間：
                        {item.report_created_at
                          ? (() => {
                            const start = new Date(item.report_created_at);
                            const end = new Date(item.report_created_at);
                            end.setFullYear(end.getFullYear() + 5);
                            return `${formatDate(start)}～${formatDate(end)}`;
                          })()
                          : "未設定"}
                      </div>
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
                          height: "330px",
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

                      <span className="inline-flex items-center gap-1">
                        {renderStatus(item)}
                      </span>
                    </button>

                    {item.report_status === "1" && item.report_save_path && (
                      <button
                        className="max-w-[120px] flex items-center space-x-1 text-[12px] text-teal-700"
                        onClick={() => handleFullView(item.report_save_path ?? "")}
                      >
                        {previewingId === item.report_save_path && (
                          <Icons.spinner className="mr-1 size-4 animate-spin" aria-hidden="true" />
                        )}
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
            columns={columnsA}
            data={pdfList}
            totalCount={pdfList.length}
            pageCount={Math.ceil(pdfList.length / 10)}
            renderRow={(item, index) => (
              <TableRow key={index}>
                <TableCell>{item.building_name}</TableCell>
                <TableCell>{item.report_name}</TableCell>
                <TableCell>{formatTargetPeriod(item.target_period, item.target_month)}</TableCell>
                <TableCell>{item.org_name}</TableCell>
                <TableCell>{item.report_created_by_name}</TableCell>
                <TableCell>
                  {item.report_created_at ? formatDate(item.report_created_at) : "未作成"}
                </TableCell>
                <TableCell>
                  {item.report_created_at
                    ? (() => {
                      const start = new Date(item.report_created_at);
                      const end = new Date(item.report_created_at);
                      end.setFullYear(end.getFullYear() + 5);
                      return `${formatDate(start)}～${formatDate(end)}`;
                    })()
                    : "未設定"}
                </TableCell>
                <TableCell>
                  <button
                    className={`w-[140px] flex items-center justify-start space-x-1 text-[12px]
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

                    <span className="inline-flex items-center gap-1">
                      {renderStatus(item)}
                    </span>
                  </button>
                </TableCell>
                <TableCell>
                  {item.report_status === "1" && item.report_save_path && (
                    <button
                      className="w-[90px] flex items-center justify-start space-x-1 text-[12px] text-teal-700"
                      onClick={() => handleFullView(item.report_save_path ?? "")}
                    >
                      {previewingId === item.report_save_path && (
                        <Icons.spinner className="mr-1 size-4 animate-spin" aria-hidden="true" />
                      )}
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
                <button onClick={() => setShowFull(false)} className="fixed top-4 right-4 z-50 text-white ">
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
    if (!showPopup) {
      // ポップアップが開いた瞬間に状態を初期化
      setSelectedBuildingId("");
      setFiscalYear("");
      setMessage("");
      setContractPower("");
      setShowMonthSelector(false);
      setTargetMonths([]);
      setSelectedMonth("");
      setSubmitError("");
      period.reset();
    }
  }, [showPopup]);

  const handleOpenPopup = async () => {
    // setshowPopup(true);
    if (!corpNo || !orgId || !agreementCategory) {
      console.warn("Missing corpNo/orgId/agreementCategory");
      return;
    }
    try {
      const params = new URLSearchParams({
        corporate_number: corpNo,
        org_id: orgId,
        agreement_category: agreementCategory,
      });
      const url = `/api/report/power-report/options?${params.toString()}`;
      console.log(Messages.VALIDATION.data.sent_url, url);
      const raw = await getData(url);
      const data = raw as OptionResponse;

      setOptionResponse(data);
      setshowPopup(true);
    } catch (error) {
      setErrorMessage(Messages.VALIDATION.api.error);
      return;
    }
  };

  useEffect(() => {
    const allValid = selectedBuildingId.trim() !== "" && period.isValidRange;
    if (!allValid || !corpNo || !orgId || !agreementCategory) {
      setMessage("");
      setTargetMonths([]);
      return;
    }

    const fetchData = async () => {
      try {
        const params = new URLSearchParams({
          building_id: selectedBuildingId,
          start_year: period.formData.startYear,
          start_month: period.formData.startMonth.padStart(2, "0"),
          end_year: period.formData.endYear,
          end_month: period.formData.endMonth.padStart(2, "0"),
        });

        const url = `/api/report/power-report/target-months?corporate_number=${corpNo}&org_id=${orgId}&agreement_category=${encodeURIComponent(
          agreementCategory,
        )}&${params.toString()}`;

        console.log(Messages.VALIDATION.data.sent_url, url);

        const raw = await getData(url);
        const data = raw as {
          message: string;
          target_months: { label: string; value: string }[];
        };

        console.log(Messages.energy_building.ebrc06.result, data);
        setMessage(data.message);
        setTargetMonths(data.target_months ?? []);
      } catch (e) {
        console.error(Messages.VALIDATION.api.error, e);
      }
    };

    fetchData();
  }, [
    selectedBuildingId,
    corpNo,
    orgId,
    agreementCategory,
    period.isValidRange,
    period.formData.startYear,
    period.formData.startMonth,
    period.formData.endYear,
    period.formData.endMonth,
  ]);

  // const isFormValid = selectedBuildingId !== "" && selectedMonth !== "";
  const isFormValid =
    selectedBuildingId !== "" &&
    selectedMonth !== "" &&
    contractPower.trim() !== "";

  const handleContractPowerChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (/^\d*$/.test(value)) {
      setContractPower(value);
    }
  };

  return (
    <CommonLayout
      selectedTab={selectedTab}
      onTabChange={setSelectedTab}
      breadcrumbItems={breadcrumbItems}
      permission={permission}
      showConsentOrgSelector={permission === 1}
    >
      <ReportPopupTest
        onConsentChange={(cat, org) => {
          setAgreementCategory(cat);
          setOrgId(org);
        }}
      />
      {pageError && (
        <div className="px-16 pt-6">
          <ErrorHint message={pageError} className="mb-4" bodyClassName="py-4" />
        </div>
      )}
      <div className="px-16 py-10">
        {listError && <ErrorHint message={listError} className="mb-4 w-4/5" bodyClassName="py-4" />}
        {selectedTab === "電力見える化レポート" && (
          <div style={{ flexGrow: 1 }}>
            {/* エラーメッセージ */}
            {errorMessage && (
              <div className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden mt-5 ml-4">
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
                    <div className="text-[#d92d20] text-[14px]">{errorMessage}</div>
                  )}
                </div>
              </div>
            )}
            {isLoading ? (
              <p>読み込み中...</p>
            ) : pdfList.length === 0 ? (
              <>
                <div className="max-w-[1480px] h-[420px] bg-white rounded-lg shadow flex flex-col items-center justify-center">
                  <div className="flex flex-col items-center justify-center h-full">
                    <div className="text-base font-semibold mb-6">電力見える化レポートは未作成です</div>
                    <Button onClick={handleOpenPopup} className=" px-4 py-2 text-[14px]">
                      レポートの作成
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
                  <Button onClick={handleOpenPopup} style={{ fontSize: "14px" }}>
                    レポートの作成
                  </Button>
                  {/* <Button
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
                <PdfViewer pdfList={pdfList} corporateNumber={corpNo} />
              </div>
            )}
          </div>
        )}

        <CustomDialog
          title="電力見える化レポートの作成"
          description={Messages.energy_building.ebrc06.input_none}
          open={showPopup}
          size="lg"
          // onOpenChange={setshowPopup}
          onOpenChange={(open) => {
            if (!open && submitting) return;

            setshowPopup(open);
            if (!open) setSubmitting(false);
          }}
          onClose={() => console.log(Messages.energy_building.ebrc06.modal_closed)}
          // className="w-[750px] overflow-hidden max-h-[90vh]"
          className="w-[750px] overflow-hidden max-h-[90vh] h-auto"
          footer={
            <>
              <Button variant="third" size="third" className="border border-solid" onClick={() => setshowPopup(false)} disabled={submitting}>
                キャンセル
              </Button>
              <Button variant="primary" size="second" onClick={handleGenerateReport} disabled={!isFormValid || submitting}>
                作成
              </Button>
            </>
          }
        >
          <div>
            {submitting && (
              <div className="fixed inset-0 z-[9999] bg-black/20 flex items-center justify-center cursor-not-allowed">
                <div className="bg-white shadow-lg rounded-lg p-6 max-w-md w-full border border-gray-200 text-center">
                  <p className="text-gray-800 text-lg font-semibold mb-2">
                    電力見える化レポート作成中
                    <LoadingDots />
                  </p>
                  <p className="text-gray-600 text-sm">2～3分ほどかかります、しばらくお待ちください</p>
                </div>
              </div>
            )}
            {submitError && (
              <div className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden mt-2 mb-4">
                <div className="flex flex-row items-center bg-red-500 px-4 py-2 gap-1">
                  <Icon name="error-pink" />
                  <Text content="エラーがあります" color="white" weight="bold" />
                </div>
                <div className="flex flex-col items-start bg-[#fee4e2] border border-[#d92d20] px-4 py-4 rounded-b text-[#d92d20] cursor-pointer gap-[10px]">
                  {Array.isArray(submitError) ? (
                    <ul className="list-disc list-inside">
                      {submitError.map((message, index) => (
                        <li key={index}>{message}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-sm font-normal leading-[21px] text-left whitespace-pre-wrap">
                      {submitError}
                    </div>
                  )}
                </div>
              </div>
            )}
            <div className="text-gray-600  mb-[5px] text-[12px]">拠点名</div>

            <select
              value={selectedBuildingId}
              onChange={(e) => handleBuildingChange(e.target.value)}
              className="border rounded px-2 py-1 w-full"
            >
              {/* <option value="">選択してください</option> */}
              <option value="" disabled hidden>選択してください</option>
              {(optionResponse?.building_list ?? []).map((b) => (
                <option key={b.building_id} value={b.building_id}>
                  {b.building_name}
                </option>
              ))}
            </select>

            <div>
              <div className="text-gray-600  mb-[5px] text-[12px]">対象期間（12か月）</div>

              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  placeholder=""
                  value={period.formData.startYear}
                  onChange={(e) => {
                    const v = e.target.value;
                    period.handleStartChange("year", v);
                    // 会計年度として開始年を保存（ユーザーが入力した値）
                    if (/^\d{4}$/.test(v)) setFiscalYear(v);
                  }}
                  onBlur={() => period.handleBlur("startYear")}
                  className={`border rounded px-2 py-1 w-[50px] text-center ${period.touched.startYear && period.formErrors.startYear
                    ? "border-red-500 bg-red-50"
                    : period.formData.startYear
                      ? "text-gray-500 bg-gray-50"
                      : "bg-white"
                    }`}
                />
                <span>年</span>

                <input
                  type="text"
                  placeholder=""
                  value={period.formData.startMonth}
                  onChange={(e) => period.handleStartChange("month", e.target.value)}
                  onBlur={() => period.handleBlur("startMonth")}
                  className={`border rounded px-2 py-1 w-[40px] text-center ${period.touched.startMonth && period.formErrors.startMonth
                    ? "border-red-500 bg-red-50"
                    : period.formData.startYear
                      ? "text-gray-500 bg-gray-50"
                      : "bg-white"
                    }`}
                />
                <span>月</span>
                <span>～</span>

                <input
                  type="text"
                  value={period.formData.endYear}
                  onChange={(e) => period.handleEndChange("year", e.target.value)}
                  onBlur={() => period.handleBlur("endYear")}
                  onFocus={() => {
                    if (period.formData.endYear && !period.isValidRange) setShowMonthSelector(true);
                  }}
                  placeholder=""
                  className={`border rounded px-2 py-1 w-[50px] text-center ${period.touched.endYear && period.formErrors.endYear
                    ? "border-red-500 bg-red-50"
                    : period.formData.endYear
                      ? "text-gray-500 bg-gray-50"
                      : "bg-white"
                    }`}
                />
                <span>年</span>
                <input
                  type="text"
                  value={period.formData.endMonth}
                  onChange={(e) => period.handleEndChange("month", e.target.value)}
                  onBlur={() => period.handleBlur("endMonth")}
                  onFocus={() => {
                    if (period.formData.endMonth && !period.isValidRange) setShowMonthSelector(true);
                  }}
                  placeholder=""
                  className={`border rounded px-2 py-1 w-[40px] text-center ${period.touched.endMonth && period.formErrors.endMonth
                    ? "border-red-500 bg-red-50"
                    : period.formData.endYear
                      ? "text-gray-500 bg-gray-50"
                      : "bg-white"
                    }`}
                />
                <span>月</span>
              </div>
              {period.formErrors.period && (
                <p className="text-red-500 text-sm mt-1">{period.formErrors.period}</p>
              )}
              {period.touched.startYear && period.formErrors.startYear && (
                <p className="text-red-500 text-sm mt-1">{period.formErrors.startYear}</p>
              )}
              {period.touched.startMonth && period.formErrors.startMonth && (
                <p className="text-red-500 text-sm mt-1">{period.formErrors.startMonth}</p>
              )}
              {period.touched.endYear && period.formErrors.endYear && (
                <p className="text-red-500 text-sm mt-1">{period.formErrors.endYear}</p>
              )}
              {period.touched.endMonth && period.formErrors.endMonth && (
                <p className="text-red-500 text-sm mt-1">{period.formErrors.endMonth}</p>
              )}
              {message && <p className="text-red-500 mt-1 text-sm">{message}</p>}

              <div className={` py-2`}>
                <hr className="my-4 border-gray-300" />
              </div>
            </div>

            {targetMonths.length > 0 && (
              <div className="mb-4">
                <div className="text-gray-600 mb-1 text-sm">対象月</div>
                <select
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="border rounded px-2 py-1 w-full"
                >
                  {/* <option value="">選択してください</option> */}
                  <option value="" disabled hidden>選択してください</option>
                  {targetMonths.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {targetMonths.length > 0 && (
              <div>
                <div className="text-gray-600  mb-[5px] text-[12px]">
                  対象月の契約電力
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={contractPower}
                    onChange={handleContractPowerChange}
                    placeholder=""
                    className={`border rounded px-2 py-1 w-[80px] text-center`}
                  />
                  <span>㎾</span>
                </div>
              </div>
            )}
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
              {Messages.energy_building.ebrc06.electricity_visible_creating}
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
