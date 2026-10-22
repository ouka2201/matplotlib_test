import React, { useCallback, useEffect, useReducer, useState } from "react";

import { DialogDescription, DialogTitle } from "@radix-ui/react-dialog";
// import { MetaFunction } from "@remix-run/node";
import { useLocation, useNavigate } from "react-router-dom";
import SearchForm from "~/components/common/search-form";
import SectionTitle from "~/components/common/section-title";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import MasterLayout from "~/components/layout/master-layout";
import { useSession } from "~/components/layout/session-provider";
import { customerColumns } from "~/components/screen/master/ebmg01/customer-columns";
import ReceiptDataTarget from "~/components/screen/master/ebmg01/ebmg10";
import { Command, CommandList } from "~/components/ui/command";
import { Dialog, DialogContent, DialogTrigger } from "~/components/ui/dialog";
import { PageableTable } from "~/components/ui/pageable-table";
import { Messages } from "~/constants/messages/message";
import { useLoadingSpinner } from "~/hooks/use-loadingspinner";
import { postData } from "~/lib/fetch";
import "~/loader.css";
import { Option } from "~/types/screen/energy-building/ebmg/ebmgType";
import { AgreementCategoryMaster } from "~/types/screen/master/msbg/msbgType";
import { Icon, Text } from "../components/import";

// export const meta: MetaFunction = () => {
//   return [{ title: "CNレポート" }, { name: "description", content: "input data" }];
// };
//------------------------１．状態管理------------------------
interface CustomerMasterState {
  isLoading: boolean;
  hasPermission: boolean;
  searchCondition: {
    company_name: string;
    corporate_number: string;
    company_address: string;
  };
  searchResults: CustomerCompanyList[];
  showResults: boolean;
}
interface CustomerCompanyList {
  company_address: string;
  company_name: string;
  company_name_kana: string;
  corporate_number: string;
  agreement_category: string[];
}

interface ApiCompany {
  company_address: string;
  company_name: string;
  company_name_kana: string;
  corporate_number: string;
  agreement_category: string;
}

const CNreportMaster: React.FC = () => {
  // stateを更新するAction
  type CustomerMasterAction =
    | { type: "SET_LOADING"; payload: boolean }
    | { type: "SET_PERMISSION"; payload: boolean }
    | {
        type: "SET_SEARCH_CONDITION";
        payload: Partial<CustomerMasterState["searchCondition"]>;
      }
    | { type: "SET_SEARCH_RESULTS"; payload: CustomerCompanyList[] }
    | { type: "SET_SHOW_RESULTS"; payload: boolean };

  // state更新用Reducer
  const customerMasterReducer = (state: CustomerMasterState, action: CustomerMasterAction): CustomerMasterState => {
    switch (action.type) {
      case "SET_LOADING":
        return { ...state, isLoading: action.payload };
      case "SET_PERMISSION":
        return { ...state, hasPermission: action.payload };
      case "SET_SEARCH_CONDITION":
        return {
          ...state,
          searchCondition: { ...state.searchCondition, ...action.payload },
        };
      case "SET_SEARCH_RESULTS":
        return {
          ...state,
          searchResults: Array.isArray(action.payload) ? action.payload : [],
        };
      case "SET_SHOW_RESULTS":
        return { ...state, showResults: action.payload };
      default:
        return state;
    }
  };

  // 検索Form必要情報
  const searchFields = [
    { id: "company_name", label: "お客さま名", placeholder: "xx株式会社" },
    {
      id: "corporate_number",
      label: "法人番号",
      // type: "number",
      placeholder: "半角数字13桁",
    },
    {
      id: "company_address",
      label: "本社所在地",
      placeholder: "東京都xx区…",
    },
  ];

  const { withLoading } = useLoadingSpinner();
  const [state, dispatch] = useReducer(customerMasterReducer, {
    isLoading: false,
    hasPermission: false,
    searchCondition: {
      company_name: "",
      corporate_number: "",
      company_address: "",
    },
    searchResults: [],
    showResults: false,
  });

  const { session, clearSession } = useSession();
  const [token, setToken] = useState<string | null>(session?.token ?? null);
  const [userId, setUserId] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>();
  const [role, setRole] = useState<string | null>();
  const [prefectureOptions, setPrefectureOptions] = useState<Option[]>([]);
  const location = useLocation();
  // const [userData, setuserData] = useState<dummysession | null>(null);
  useState<AgreementCategoryMaster[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [payload, setPayload] = useState<CustomerCompanyList | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  // 読み込み中フラグ
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchTokenAndUserInfoFromSessionStorage = () => {
      if (typeof window !== "undefined") {
        const sessionData = sessionStorage.getItem("session");

        if (sessionData) {
          const sessionObj = JSON.parse(sessionData);

          // トークン処理
          if (sessionObj?.token) {
            setToken(sessionObj.token);
          } else {
            console.log(Messages.VALIDATION.data.token_none);
            setToken(null);
          }

          if (sessionObj?.email) {
            setUserId(sessionObj.email);
          } else {
            console.log(Messages.VALIDATION.data.session_none);
            setUserId(null);
          }

          if (sessionObj?.authorityInfo.org_id) {
            setOrgId(sessionObj.authorityInfo.org_id);
          } else {
            console.log(Messages.VALIDATION.data.session_none);
            setOrgId(null);
          }

          if (sessionObj?.authorityInfo.role) {
            setRole(sessionObj.authorityInfo.role);
          } else {
            console.log(Messages.VALIDATION.data.session_none);
            setRole(null);
          }
        } else {
          console.log(Messages.VALIDATION.data.session_none);
          setToken(null);
          setUserId(null);
          setOrgId(null);
          setRole(null);
        }
      }
    };
    fetchTokenAndUserInfoFromSessionStorage();
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

  // 検索条件更新
  const updateSearchCondition = (updates: Partial<typeof state.searchCondition>) => {
    dispatch({
      type: "SET_SEARCH_CONDITION",
      payload: { ...updates },
    });
  };

  // 検索処理イベント
  const handleSearch = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setErrorMessage("");
    dispatch({ type: "SET_LOADING", payload: true });

    function isErrorWithStatus(error: unknown): error is { status: number; error_message_list?: string } {
      return (
        typeof error === "object" &&
        error !== null &&
        "status" in error &&
        typeof (error as { status: number }).status === "number"
      );
    }

    try {
      // const queryString = new URLSearchParams(state.searchCondition).toString();
      const url = `/api/mst_corporate/info/inquiry?page_info=report`;
      // const url = `/api/report-management/info/inquiry?${queryString}`;
      const data = (await withLoading(() => postData(url, state.searchCondition))) as ApiCompany[];
      const rawData: ApiCompany[] = data ?? [];
      const groupedMap = rawData.reduce<Record<string, CustomerCompanyList>>((acc, item) => {
        const key = item.corporate_number;

        if (!acc[key]) {
          acc[key] = {
            company_address: item.company_address,
            company_name: item.company_name,
            company_name_kana: item.company_name_kana,
            corporate_number: item.corporate_number,
            agreement_category: [item.agreement_category], // 配列化
          };
        } else {
          if (!acc[key].agreement_category.includes(item.agreement_category)) {
            acc[key].agreement_category.push(item.agreement_category);
          }
        }

        return acc;
      }, {});

      const groupedData: CustomerCompanyList[] = Object.values(groupedMap);

      dispatch({ type: "SET_SEARCH_RESULTS", payload: groupedData });
      console.log("groupedData:", groupedData);
    } catch (error: unknown) {
      console.error(Messages.VALIDATION.api.error);

      if (isErrorWithStatus(error)) {
        if (error.status === 401) {
          // error_codeを確認して、SINGLE_LOGIN_VIOLATIONの場合は遷移しない
          // （イベントハンドラーが既に処理しているため）
          const errorCode = (error as any).data?.error_code;
          if (errorCode === "SINGLE_LOGIN_VIOLATION") {
            console.log("[ebmg01] SINGLE_LOGIN_VIOLATION検出、遷移をスキップ");
            return;
          }
          clearSession();
          sessionStorage.removeItem("session");
          return window.location.href = "/session-expired";
        }
        switch (error.status) {
          case 400:
            // setErrorMessage(error.error_message_list || Messages.VALIDATION_ERROR);
            setErrorMessage(
              (error as any).data?.error_message_list?.[0] || (error as any).data?.message || Messages.VALIDATION_ERROR,
            );
            break;
          case 500:
            setErrorMessage(Messages.SYSTEM_ERROR);
            break;
          default:
            // setErrorMessage(Messages.UNKNOWN_ERROR);
            setErrorMessage((error as any).data?.message || Messages.UNKNOWN_ERROR);
            break;
        }
      } else {
        setErrorMessage(Messages.VALIDATION.api.error);
      }
    } finally {
      // ここで1秒待つ
      // await new Promise((resolve) => setTimeout(resolve, 5000)); // TODO: 開発用。後で消す
      setIsLoading(false);
      dispatch({ type: "SET_LOADING", payload: false });
    }
  }, [state.searchCondition, withLoading]);

  // 初期表示時検索実行
  useEffect(() => {
    if (role && userId && orgId) {
      handleSearch();
    }
  }, [role, userId, orgId]);

  // 検索条件リセット実行
  const handleReset = () => {
    setIsResetting(true);
    updateSearchCondition({
      company_name: "",
      corporate_number: "",
      company_address: "",
    });
  };

  useEffect(() => {
    if (isResetting) {
      handleSearch();
      setIsResetting(false);
    }
  }, [state.searchCondition, isResetting]);

  const handleCustomerNameClick = (company: CustomerCompanyList) => {
    const { isJfs = false, isAse = false, isZrb = false } = JSON.parse(sessionStorage.getItem("userRoleFlags") || "{}");

    // 可視化事業者ユーザーの権限フラグ
    const isVis = isJfs || isAse || isZrb;
    const {
      isBank = false,
      isBranchAdmin = false,
      isBranchGeneral = false,
    } = JSON.parse(sessionStorage.getItem("userRoleFlags") || "{}");

    // 銀行ユーザーの権限フラグ
    const isBankUser = isBank || isBranchAdmin || isBranchGeneral;
    let path = ""; // 初期化

    sessionStorage.setItem(
      "corporateData",
      JSON.stringify({
        corporate_number: company.corporate_number,
        company_name: company.company_name,
        company_address: company.company_address,
        agreement_category: company.agreement_category,
      }),
    );

    if (isVis) {
      path = "/energy-building/ebrc03";
      navigate(path, {
        state: { customerData: company, mode: "refer", permission: 2 },
      });
    } else if (isBankUser) {
      path = "/energy-building/ebrc03";
      navigate(path, {
        state: { customerData: company, mode: "refer", permission: 1 },
      });
    } else {
      path = ""; // 他のユーザーは詳細ページに遷移しない
      setPayload(company);
      setOpen(true);
      navigate(path, {
        state: { customerData: company, mode: "refer" },
      });
    }
  };
  // パンくず
  const breadcrumbItems = [{ title: "レポート作成・管理", link: "" }];

  return (
    <MasterLayout breadcrumbItems={breadcrumbItems} isEditing={false}>
      {/* <h2 className="font-bold text-2xl my-8">レポート作成・管理</h2> */}
      {/* <div className='p-3'> */}
      {errorMessage && (
        <div className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden">
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
      {/* ▼検索条件 */}
      <div className="space-y-4 mb-10">
        <SearchForm
          fields={searchFields}
          values={state.searchCondition}
          onValueChange={updateSearchCondition}
          onSearch={handleSearch}
          onReset={handleReset}
        />
      </div>

      {/* ▼確認・編集対象企業の選択 */}
      <Command>
        {isLoading ? (
          // ローディング中
          <div className="p-4 flex justify-center items-center text-gray-500 text-sm">
            <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin mr-2"></div>
            読み込み中...
          </div>
        ) : (
          // 結果あり
          <>
            {/* <SectionTitle>対象企業の選択</SectionTitle> */}
            <CommandList>
              <PageableTable<CustomerCompanyList, unknown>
                columns={customerColumns(prefectureOptions, handleCustomerNameClick)}
                totalCount={state.searchResults.length}
                data={state.searchResults}
                pageCount={Math.ceil(state.searchResults.length / 5)}
              />
            </CommandList>
          </>
        )}
      </Command>

      <div className="z-201">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger hidden />
          <DialogContent>
            <DialogTitle hidden />
            <DialogDescription hidden />
            {payload && <ReceiptDataTarget orgId={orgId} data={payload} />}
          </DialogContent>
        </Dialog>
      </div>
    </MasterLayout>
  );
};

export default CNreportMaster;
