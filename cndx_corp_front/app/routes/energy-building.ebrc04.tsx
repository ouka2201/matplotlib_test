import { ColumnDef } from "@tanstack/react-table";
import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import CustomDialog from "~/components/modal/common-dialog";
import { Button } from "~/components/ui/button";
import { Command, CommandList } from "~/components/ui/command";
import { Messages } from "~/constants/messages/message";
import { usePeriod12Months } from "~/hooks/usePeriod12Months";
import { useRoleFlags } from "~/hooks/useRoleFlags";
import { baseSchema } from "~/lib/validations/ebrc";
import CommonLayout from "../components/CommonLayout";
import { TabName } from "../components/tab-navigator";
import { PageableTable } from "../components/ui/pageable-table";
import { getData } from "../lib/fetch";
import "../styles/popup.css";


type listInfo = {
  fiscalYear: string;
  displayPeriod: string;
  responsible: string;
  staffOrg: string;
  points: string;
  createdDate: string;
  entryDraftFlag: string;
  entry_draft_flag: string;
  seq: number;
};

const CONSENT_ROUTE_ERROR_MESSAGE =
  "同意書取得経路が地銀アライアンス以外のため、新規登録できません。管理者へご確認ください。";

const ReportENeRuGi: React.FC = () => {
  const [showPopup, setshowPopup] = useState(false);
  // const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<TabName>("拠点・エネルギー情報");
  const [data, setData] = useState<listInfo[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [canCreateNew, setCanCreateNew] = useState(false);
  const location = useLocation();
  const permission = location.state?.permission ?? 1;
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

  const [selectedAgreementCategory, setSelectedAgreementCategory] = useState<string | null>(null);
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const navigate = useNavigate();
  const [corporateData, setCorporateData] = useState<any>(null);
  const { isBankUser } = useRoleFlags();
  const [corporateNumber, setCorporateNumber] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("corporateData");
      if (stored) {
        return JSON.parse(stored).corporate_number;
      }
    }
    return null;
  });
  const [errorMessage, setErrorMessage] = useState<string>("");
  // const [selectedConsentRouteCode, setSelectedConsentRouteCode] = useState("");
  const [token] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      return sessionData ? JSON.parse(sessionData).token : null;
    }
    return null;
  });
  const [orgId, setOrgId] = useState<string | null>(null);

  // CommonLayout の選択（sessionStorage）変更を購読して、即時反映する
  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncFromSessionStorage = () => {
      const keys = buildConsentKeys();
      if (!keys) return;
      setSelectedAgreementCategory(sessionStorage.getItem(keys.catKey));
      setSelectedOrgId(sessionStorage.getItem(keys.orgKey));
    };

    // 初回同期
    syncFromSessionStorage();

    // 別コンポーネント側で setItem されたときに拾う（同一タブ内は CustomEvent 推奨だが、まずは storage で対応）
    const onStorage = () => {
      syncFromSessionStorage();
    };
    window.addEventListener("storage", onStorage);
    const onConsentChanged = () => syncFromSessionStorage();
    window.addEventListener("consentSelectionChanged", onConsentChanged);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("consentSelectionChanged", onConsentChanged);
    };
  }, [buildConsentKeys]);

  useEffect(() => {
    const fetchTokenAndUserIdFromSessionStorage = () => {
      if (typeof window !== "undefined") {
        const sessionData = sessionStorage.getItem("session");
        if (sessionData) {
          const sessionObj = JSON.parse(sessionData);
          if (sessionObj?.authorityInfo.org_id) {
            setOrgId(sessionObj.authorityInfo.org_id);
          } else {
            console.log(Messages.energy_building_info.ebmg03.org_id_none);
            setOrgId(null);
          }
        } else {
          console.log(Messages.VALIDATION.data.session_none);
          setOrgId(null);
        }
      }
    };
    fetchTokenAndUserIdFromSessionStorage();
  }, [location.state]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("corporateData");
      if (stored) {
        const parsed = JSON.parse(stored);
        setCorporateData(parsed);
        setCorporateNumber(parsed.corporate_number);
      }
    }
  }, []);
  const breadcrumbItems = [
    { title: "レポート作成・管理", link: "/", className: "color-green-primar" },
    { title: "○○株式会社", link: "/" },
  ];

  const report2Columns: ColumnDef<listInfo>[] = [
    {
      accessorKey: "fiscalYear",
      header: () => (
        <div className="flex justify-between items-center w-full">
          <span>情報登録年</span>
        </div>
      ),

      cell: ({ row }) => row.original.fiscalYear,
    },
    { accessorKey: "displayPeriod", header: "情報登録期間" },
    { accessorKey: "staffOrg", header: "担当組織" },
    { accessorKey: "responsible", header: "担当者" },
    { accessorKey: "points", header: "拠点数" },
    {
      accessorKey: "createdDate",
      header: "情報登録日",
      cell: ({ row }) => {
        const date = new Date(row.original.createdDate);
        const y = date.getUTCFullYear();
        const m = String(date.getUTCMonth() + 1).padStart(2, "0");
        const d = String(date.getUTCDate()).padStart(2, "0");
        return `${y}/${m}/${d}`;
      },
    },
  ];

  // EP社レビュー表（総合・受入テスト）拠点・エネルギー情報登録-No132にてチェックを外す
  // 期間重複チェック関数（開始・終了年月の範囲が重なるかどうか判定）
  // const isPeriodDuplicate = useCallback(
  //   (startYM: string, endYM: string) => {
  //     const formatPeriod = (period: string) => {
  //       const [year, month] = period.split("/");
  //       return year + month.padStart(2, "0");
  //     };

  //     return data.some((item) => {
  //       const [itemStartRaw, itemEndRaw] = item.displayPeriod.split("〜");
  //       const itemStart = formatPeriod(itemStartRaw);
  //       const itemEnd = formatPeriod(itemEndRaw);

  //       // まったく同じ開始年月・終了年月かどうかの判定
  //       return startYM === itemStart && endYM === itemEnd;
  //     });
  //   },
  //   [data]
  // );

  // モーダルの入力・エラー状態をリセット
  const resetPopupState = useCallback(() => {
    setErrorMessage("");
    period.reset();
  }, []);

  const handleOpenPopup = async () => {
    resetPopupState();
    if (!token) {
      console.error(Messages.energy_building.ebrc04.token_error);
      setshowPopup(true);
      return;
    }
    // 未登録の場合はモーダルを開かない
    if (!canCreateNew) {
      return;
    }

    const keys = buildConsentKeys();
    const currentAgreement = keys ? sessionStorage.getItem(keys.catKey) : null;
    const currentOrg = keys ? sessionStorage.getItem(keys.orgKey) : null;
    if (!currentAgreement || !currentOrg) {
      setErrorMessage("同意書取得経路・組織を選択してください。");
      return;
    }

    setshowPopup(true);
  };

  const handleSearch = useCallback(async () => {
    // setLoading(true);
    setErrorMessage("");
    try {
      // 法人番号でURLを構築
      let url = `/api/building/energy-info-list?corporate_number=${corporateNumber}`;

      // CommonLayout の選択値を検索条件にする
      if (selectedAgreementCategory) {
        url += `&agreement_category=${selectedAgreementCategory}`;
      }
      if (selectedOrgId) {
        url += `&org_id=${selectedOrgId}`;
      }

      const raw = await getData(url);
      if (raw?.result_list && Array.isArray(raw.result_list)) {
        const converted: listInfo[] = raw.result_list.map((item: any) => {
          // "202404" → "2024年4月"
          const startYear = item.report_period_start_year_month.slice(0, 4);
          const startMonth = item.report_period_start_year_month.slice(4, 6);
          const endYear = item.report_period_end_year_month.slice(0, 4);
          const endMonth = item.report_period_end_year_month.slice(4, 6);
          const linkPath = `/energy-building-info/ebmg03`;

          return {
            fiscalYear: (
              <span>
                <a
                  href={linkPath}
                  className="text-[#00897b] underline font-semibold"
                  onClick={(e) => {
                    e.preventDefault();
                    const keys = buildConsentKeys();
                    const currentAgreement =
                      (keys ? sessionStorage.getItem(keys.catKey) : null) ?? selectedAgreementCategory ?? "";
                    const currentOrg =
                      (keys ? sessionStorage.getItem(keys.orgKey) : null) ?? selectedOrgId ?? "";
                    const reportInfo = {
                      start_year_month: item.report_period_start_year_month,
                      end_year_month: item.report_period_end_year_month,
                      registration_seq: item.registration_seq,
                      entry_draft_flag: item.entry_draft_flag,
                      fiscal_year: item.fiscal_year,
                      agreement_category: item.agreement_category,
                      create_org_id: item.org_id,
                    };
                    sessionStorage.setItem("reportStatusInfo", JSON.stringify(reportInfo));

                    sessionStorage.setItem("selectedAgreementCategory", item.agreement_category ?? "");
                    sessionStorage.setItem("selectedOrgId", item.org_id ?? "");
                    navigate(linkPath, {
                      state: {
                        ...corporateData,
                        agreementCategory: currentAgreement,
                        orgId: currentOrg,
                      },
                    });
                  }}
                >
                  {`${item.fiscal_year}-${item.registration_seq}`}
                </a>
                {item.entry_draft_flag === "1" && <span className="text-gray-500 text-sm ">（下書き）</span>}
              </span>
            ),

            entryDraftFlag: item.entry_draft_flag,
            displayPeriod: `${startYear}/${Number(startMonth)}〜${endYear}/${Number(endMonth)}`,
            staffOrg: item.staff_org,
            responsible: item.staff_user_name,
            points: item.business_office_count, // 仮に1拠点として設定（必要に応じて変更）
            createdDate: item.created_at,
          };
        });

        setData(converted);
        setTotalCount(converted.length);
        const maxRegistrationInfoList =
          raw.result_list.length > 0
            ? raw.result_list.map(item => ({
              fiscal_year: item.fiscal_year,
              max_registration_seq: item.max_registration_seq,
            }))
            : [];

        sessionStorage.setItem(
          "maxRegistrationInfoList",
          JSON.stringify(maxRegistrationInfoList)
        );
      }
    } catch (error) {
      console.error(error);
      const consentRouteErrorMessage =
        (error as any)?.status === 403 ? CONSENT_ROUTE_ERROR_MESSAGE : null;
      const message =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.data?.message ||
        (error instanceof Error ? error.message : null) ||
        consentRouteErrorMessage ||
        Messages.SYSTEM_ERROR;
      setErrorMessage(message);
    } finally {
      // setLoading(false);
    }
  }, [corporateNumber, selectedAgreementCategory, selectedOrgId, token, navigate, corporateData]);

  // 選択が変わったら即時再検索
  useEffect(() => {
    if (!corporateNumber) return;
    // 選択が未決定のときは検索しない（APIエラー回避）
    if (!selectedAgreementCategory || !selectedOrgId) return;

    // 新規登録の可否は選択値に依存するため、先に判定してから検索する
    setCanCreateNew(selectedAgreementCategory.startsWith("0") && selectedAgreementCategory !== "00");
    handleSearch();
  }, [corporateNumber, selectedAgreementCategory, selectedOrgId, handleSearch]);

  const period = usePeriod12Months({
    schema: baseSchema,
    // duplicateCheck: isPeriodDuplicate,
    // duplicateErrorMessage: Messages.energy_building.ebrc04.period_duplicate_error,
  });

  return (
    <CommonLayout
      selectedTab={selectedTab}
      onTabChange={setSelectedTab}
      breadcrumbItems={breadcrumbItems}
      permission={permission}
      showConsentOrgSelector={permission === 1}
    >
      {selectedTab === "拠点・エネルギー情報" && (
        <>
          <div className="px-16 pt-8">
            <div className="max-w-[1480px] w-full flex justify-end">
              <Button
                onClick={handleOpenPopup}
                disabled={!canCreateNew}
                variant="primary"
                size="default"
                // style={{
                //   border: "1px solid #15B79E",
                // }}
                className="disabled:cursor-not-allowed disabled:bg-[#EAECF0] disabled:text-gray-400"
              >
                新規登録
              </Button>
            </div>
            <div className="max-w-[1480px] pt-8">
              <Command>
                <CommandList>
                  {/* {data.length > 0 ? ( */}
                  <PageableTable<listInfo, unknown>
                    columns={report2Columns}
                    data={data}
                    pageCount={1}
                    totalCount={totalCount}
                    pageSizeOptions={[5, 10, 20, 50]}
                  />
                </CommandList>
              </Command>
              {/* )} */}
            </div>
          </div>
        </>
      )}
      <CustomDialog
        title="拠点・エネルギー情報の新規登録"
        description={Messages.energy_building.ebrc04.period_input_none}
        open={showPopup}
        size="lg"
        // onOpenChange={setshowPopup}
        onOpenChange={(open) => {
          setshowPopup(open);
          if (!open) resetPopupState();
        }}
        onClose={() => console.log("モーダル閉じた")}
        className="w-fit h-auto"
        errorMessage={errorMessage}
        errorBodyClassName="py-4"
        footer={
          <div className="popup-buttons flex justify-end gap-4 mt-4">
            <Button
              variant="third"
              size="third"
              className="border border-solid"
              onClick={() => {
                resetPopupState();
                setshowPopup(false);
              }}
            >
              キャンセル
            </Button>
            <Button
              disabled={!period.isValidRange}
              className={`${!period.isValidRange
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-[#15B79E] text-white cursor-pointer hover:bg-[#15B79E]"
                }`}
              variant="third"
              size="third"
              onClick={() => {
                if (!period.isValidRange) return;
                const keys = buildConsentKeys();

                // CommonLayout 選択値（namespaced）を確実に取得
                const currentAgreement = selectedAgreementCategory ?? (keys ? sessionStorage.getItem(keys.catKey) : null);
                const currentOrg = selectedOrgId ?? (keys ? sessionStorage.getItem(keys.orgKey) : null);

                // 互換：旧 key も更新して、他画面が旧 key を読んでも一致するようにする
                if (currentAgreement) sessionStorage.setItem("selectedAgreementCategory", currentAgreement);
                if (currentOrg) sessionStorage.setItem("selectedOrgId", currentOrg);
                const reportInfo = {
                  start_year_month: `${period.formData.startYear}${period.formData.startMonth.padStart(2, "0")}`,
                  end_year_month: `${period.formData.endYear}${period.formData.endMonth.padStart(2, "0")}`,
                  registration_seq: 0,
                  entry_draft_flag: "",
                  agreement_category: currentAgreement,
                  create_org_id: currentOrg,
                };
                sessionStorage.setItem("reportStatusInfo", JSON.stringify(reportInfo));
                navigate("/energy-building-info/ebmg03", {
                  state: {
                    ...corporateData,
                    agreementCategory: currentAgreement,
                    orgId: currentOrg,
                  },
                });
              }}
            >
              登録画面へ
            </Button>
          </div>
        }
      >
        <div>
          <span className="block text-sm font-medium text-gray-700 mb-1">情報登録期間（12か月）</span>
          <div className="flex items-center gap-8">
            {" "}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={period.formData.startYear}
                onChange={(e) => period.handleStartChange("year", e.target.value)}
                onBlur={() => period.handleBlur("startYear")}
                className={`border rounded px-2 py-1 w-[50px] text-center ${period.touched.startYear && (period.formErrors.startYear || period.formErrors.period) ? "border-red-500 bg-red-50" : "text-gray-500 bg-gray-50"
                  }`}
              />
              <span>年</span>
              <input
                type="text"
                value={period.formData.startMonth}
                onChange={(e) => period.handleStartChange("month", e.target.value)}
                onBlur={() => period.handleBlur("startMonth")}
                className={`border rounded px-2 py-1 w-[40px] text-center ${period.touched.startMonth && (period.formErrors.startMonth || period.formErrors.period) ? "border-red-500 bg-red-50" : "text-gray-500 bg-gray-50"
                  }`}
              />
              <span>月 ～</span>
              <input
                type="text"
                value={period.formData.endYear}
                onChange={(e) => period.handleEndChange("year", e.target.value)}
                onBlur={() => period.handleBlur("endYear")}
                className={`border rounded px-2 py-1 w-[50px] text-center ${period.touched.endYear && (period.formErrors.endYear || period.formErrors.period) ? "border-red-500 bg-red-50" : "text-gray-500 bg-gray-50"
                  }`}
              />
              <span>年</span>
              <input
                type="text"
                value={period.formData.endMonth}
                onChange={(e) => period.handleEndChange("month", e.target.value)}
                onBlur={() => period.handleBlur("endMonth")}
                className={`border rounded px-2 py-1 w-[40px] text-center ${period.touched.endMonth && (period.formErrors.endMonth || period.formErrors.period) ? "border-red-500 bg-red-50" : "text-gray-500 bg-gray-50"
                  }`}
              />
              <span>月</span>
            </div>
          </div>
        </div>
        {/* エラー表示 */}
        {/* {formErrors.period && (
          <p className="text-red-500 text-sm mt-1">{formErrors.period}</p> */}
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
      </CustomDialog>
    </CommonLayout>
  );
};

export default ReportENeRuGi;
