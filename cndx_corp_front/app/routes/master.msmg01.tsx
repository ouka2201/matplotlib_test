import React, { useEffect, useState } from "react";
// import { useNavigate } from "react-router-dom";
import ErrorHint from "~/components/common/error-hint";
import SearchForm from "~/components/common/search-form";
import SectionTitle from "~/components/common/section-title";
import MasterLayout from "~/components/layout/master-layout";
import { customerColumns } from "~/components/screen/master/msmg01/customer-columns";
import { Command, CommandList } from "~/components/ui/command";
import { PageableTable } from "~/components/ui/pageable-table";
import { Messages } from "~/constants/messages/message";
import { postData } from "~/lib/fetch";

type Customer = {
  company_name: string;
  corporate_number: string;
  company_address: string;
  // company_name_kana: string;
  // company_address_prefecture: string;
  // company_address_city: string;
};

const breadcrumbItems = [
  { title: "営業担当登録・管理", link: "" },
];

const searchFields = [
  { id: "company_name", label: "お客さま名", placeholder: "xx株式会社", },
  { id: "corporate_number", label: "法人番号", placeholder: "半角数字13桁", },
  { id: "company_address", label: "本社所在地", placeholder: "東京都xx区…", },
];

export default function CustomerMaster() {
  // const navigate = useNavigate();
  // const { session } = useSession();
  // const { isAdmin, isBank } = useAuthority(session);
  // const token = session?.token;
  const [token, setToken] = useState<string | null>(null);

  // 検索条件の型を定義
  type Criteria = {
    company_name: string;
    corporate_number: string;
    company_address: string;
  };

  // 検索条件
  const [criteria, setCriteria] = useState<Criteria>({
    company_name: "",
    corporate_number: "",
    company_address: "",
  });
  // 結果リスト
  const [results, setResults] = useState<Customer[]>([]);
  // 読み込み中フラグ
  const [isLoading, setIsLoading] = useState(false);
  // エラーメッセージ
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");

  const [shouldSimulateError, setShouldSimulateError] = useState(true);

  const onValueChange = (upd: Partial<typeof criteria>) => {
    console.log("onValueChange >>>", upd);
    setCriteria(prev => ({ ...prev, ...upd }));
  };

  // 絞り込み実行
  const handleSearch = React.useCallback(
    async (next?: Partial<Criteria>, options?: { forceError?: boolean }) => {
      if (!token) return;
      setIsLoading(true);
      setErrorMessage("");
      try {
        if (options?.forceError || shouldSimulateError) {
          if (shouldSimulateError) {
            setShouldSimulateError(false);
          }
        }
        const requestParams = {
          ...Object.fromEntries(
            Object.entries({ ...criteria, ...(next ?? {}) }).filter(
              ([, v]) => typeof v === "string" || typeof v === "number"
            )
          ),
          page_info: "staff"
        };
        const url = `/api/mst_corporate/info/inquiry`;
        const response = await postData(url, requestParams, { Authorization: `Bearer ${token}` });


        const list: Customer[] = Array.isArray(response) ? response : response.result ?? [];
        list.sort((a, b) => a.company_name.localeCompare(b.company_name, "ja"));
        setResults(list);
      } catch (e) {
        setErrorMessage(e instanceof Error ? e.message || Messages.SYSTEM_ERROR : Messages.SYSTEM_ERROR);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    },
    [token, criteria, shouldSimulateError]
  );

  // 検索条件リセット実行
  const handleReset = () => {
    const cleared = { company_name: "", corporate_number: "", company_address: "" };

    // criteria の state をリセット
    setCriteria(cleared);
    handleSearch(cleared);
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
      }
    }
  }, []);

  // 初回検索を行ったかどうかのフラグ
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    if (token && !hasSearched) {
      handleSearch(); //tokenが取得できてから検索実行
      setHasSearched(true);// 入力変更で自動検索されないようにする
    }
  }, [token, handleSearch, hasSearched]);

  return (
    <MasterLayout breadcrumbItems={breadcrumbItems} isEditing={false}>
      {errorMessage && (
        <div className="w-4/5">
          <ErrorHint
            message={errorMessage}
            bodyClassName="py-4"
          />
        </div>
      )}
      {/* 検索条件 */}
      <div className="space-y-4 mb-10">
        <SearchForm
          fields={searchFields}
          values={criteria}
          onValueChange={onValueChange}
          onSearch={handleSearch}
          onReset={handleReset}
        />
      </div>

      {/* 検索結果 */}
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
            <PageableTable<Customer, unknown>
              columns={customerColumns}
              data={results}
              totalCount={results.length}
              pageCount={Math.ceil(results.length / 10)}
              initailSort={[]}
            />
          )}
        </CommandList>

      </Command>
    </MasterLayout>
  );
}
