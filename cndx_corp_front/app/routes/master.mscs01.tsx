import { useCallback, useEffect, useReducer, useState } from 'react';
import { useNavigate } from "react-router-dom";
import SearchForm from '~/components/common/search-form';
import MasterLayout from '~/components/layout/master-layout';
import { customerColumns } from '~/components/screen/master/mscs01/customer-columns';
import { Button } from "~/components/ui/button";
import { Command, CommandList } from '~/components/ui/command';
import { PageableTable } from '~/components/ui/pageable-table';
import { API_ENDPOINTS } from '~/constants/api-endpoints';
import { getData } from '~/lib/fetch';
import "~/loader.css";
import { CustomerCompany } from '~/types/screen/master/mscs/mscsType';
import { Icon, Text } from "../components/import";


//------------------------１．状態管理------------------------
// お客さまマスタ画面管理State
interface CustomerMasterState {
  isLoading: boolean;
  hasPermission: boolean;
  searchCondition: {
    company_name: string;
    corporate_number: string;
    company_address: string;
  };
  searchResults: CustomerCompany[];
  showResults: boolean;
}

// stateを更新するAction
type CustomerMasterAction =
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_PERMISSION"; payload: boolean }
  | { type: "SET_SEARCH_CONDITION"; payload: Partial<CustomerMasterState["searchCondition"]> }
  | { type: "SET_SEARCH_RESULTS"; payload: CustomerCompany[] }
  | { type: "SET_SHOW_RESULTS"; payload: boolean };

// state更新用Reducer
const customerMasterReducer = (state: CustomerMasterState, action: CustomerMasterAction): CustomerMasterState => {
  switch (action.type) {
    case "SET_LOADING":
      return { ...state, isLoading: action.payload };
    case "SET_PERMISSION":
      return { ...state, hasPermission: action.payload };
    case "SET_SEARCH_CONDITION":
      return { ...state, searchCondition: { ...state.searchCondition, ...action.payload } };
    case "SET_SEARCH_RESULTS":
      return { ...state, searchResults: action.payload };
    case "SET_SHOW_RESULTS":
      return { ...state, showResults: action.payload };
    default:
      return state;
  }
};

// パンくず
const breadcrumbItems = [
  { title: "お客さまマスタ登録・管理", link: "" }
];

// 検索Form必要情報
const searchFields = [
  { id: "company_name", label: "お客さま名", placeholder: "xx株式会社", },
  { id: "corporate_number", label: "法人番号", placeholder: "半角数字13桁", },
  { id: "company_address", label: "所在地", placeholder: "東京都xx区…", }
];

export default function CustomerMaster() {
  // const { session } = useSession();
  const navigate = useNavigate();
  // EP管理者フラグ
  const [isEpAdmin, setIsEpAdmin] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const [token, setToken] = useState<string | null>(null);
  // 読み込み中フラグ
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const userRoleFlags = JSON.parse(sessionStorage.getItem("userRoleFlags") || "{}");
    setIsEpAdmin(userRoleFlags.isEpAdmin ?? false);
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
      }
    }
  }, []);

  // useEffect(() => {
  //   const handler = () => {
  //     sessionStorage.removeItem("session");
  //     window.location.href = "/session-expired";
  //   };
  //   window.addEventListener("sessionExpired", handler);
  //   return () => window.removeEventListener("sessionExpired", handler);
  // }, []);
  const [state, dispatch] = useReducer(customerMasterReducer, {
    isLoading: false,
    hasPermission: false,
    searchCondition: {
      company_name: '',
      corporate_number: '',
      company_address: ''
    },
    searchResults: [],
    showResults: false
  });

  // 検索条件更新
  const updateSearchCondition = (updates: Partial<typeof state.searchCondition>) => {
    dispatch({
      type: "SET_SEARCH_CONDITION",
      payload: { ...updates }
    });
  };

  const buildQuery = (params: Record<string, string>) => {
    const cleaned: Record<string, string> = {};
    Object.entries(params).forEach(([k, v]) => {
      if (typeof v === "string" && v.trim() !== "") cleaned[k] = v.trim();
    });
    return new URLSearchParams(cleaned).toString();
  };


  // 検索処理イベント
  const handleSearch = useCallback(
    async (overrides?: Partial<CustomerMasterState["searchCondition"]>) => {
      if (!token) return;
      setIsLoading(true);
      setErrorMessage("");
      dispatch({ type: "SET_LOADING", payload: true });

      try {

        const effective = { ...state.searchCondition, ...(overrides ?? {}) };
        const query = buildQuery(effective);
        const base = API_ENDPOINTS.CUSTOMER_MASTER.MASTER_LIST;
        const url = query ? `${base}?${query}` : base;

        const data = await getData(url, { Authorization: `Bearer ${token}` })
        // if (data.error) {
        //   setErrorMessage(data.message || Messages.VALIDATION.api.fetch_error);
        //   return;
        // }
        const sortedResults = data.result.sort(
          (a: CustomerCompany, b: CustomerCompany) =>
            a.company_name.localeCompare(b.company_name, "ja")
        );

        dispatch({ type: "SET_SEARCH_RESULTS", payload: sortedResults });
        dispatch({ type: "SET_SHOW_RESULTS", payload: true });
      } catch (error: any) {
        setErrorMessage(error.data?.message);
      } finally {
        // ここで1秒待つ
        // await new Promise((resolve) => setTimeout(resolve, 5000)); // TODO: 開発用。後で消す
        setIsLoading(false);
        dispatch({ type: "SET_LOADING", payload: false });
      }
    },
    [token, state.searchCondition]
  );

  // 初期表示時検索実行
  useEffect(() => {
    if (token) {
      handleSearch();
    }
  }, [token]);



  // 検索条件リセット実行
  const handleReset = () => {
    const cleared = { company_name: "", corporate_number: "", company_address: "" };

    dispatch({ type: "SET_SEARCH_CONDITION", payload: cleared });

    handleSearch(cleared);
  }

  return (
    <MasterLayout
      breadcrumbItems={breadcrumbItems}
      isEditing={false}>

      <div className="space-y-6 mb-10">
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
        {/* 新規登録リンク */}
        {/* {isBank && (  */}
        <div className="space-y-4">
          <div className="flex justify-end">
            {isEpAdmin && (
                <Button
                  variant="primary"
                  size="default"
                  className="gap-1"
                  onClick={() => navigate("/master/mscs02")}
                >
                  {/* <PlusIcon className="h-5 w-5" /> */}
                  <span>新規登録</span>
                </Button>
            )}
          </div>
          {/* )}  */}

          {/* ▼検索条件 */}
          <SearchForm
            fields={searchFields}
            values={state.searchCondition}
            onValueChange={updateSearchCondition}
            onSearch={handleSearch}
            onReset={handleReset}
          />
        </div>
      </div>
      {/* ▼確認・編集対象企業の選択 */}
      <Command>
        {/* <SectionTitle>対象企業の選択</SectionTitle> */}
        <CommandList>
          {isLoading ? (
            <div className="p-4 flex justify-center items-center text-gray-500 text-sm">
              <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin mr-2"></div>
              読み込み中...
            </div>
          ) : (
            // データあり
            <PageableTable<CustomerCompany, unknown>
              columns={customerColumns}
              data={state.searchResults}
              totalCount={state.searchResults.length}
              pageCount={Math.ceil(state.searchResults.length / 10)}
              initailSort={[]}
            />
          )}
        </CommandList>
      </Command>
    </MasterLayout>
  );
}

