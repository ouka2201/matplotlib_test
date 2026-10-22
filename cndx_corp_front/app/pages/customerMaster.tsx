// CustomerMaster.tsx
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import BreadCrumb from '~/components/common/breadcrumb';
import { columns } from '~/components/screen/master/mscs01/customer-columns';
import { Button } from '~/components/ui/button';
import { Command, CommandEmpty, CommandInput, CommandList } from '~/components/ui/command';
import { PageableTable, parseSortQueryParam } from '~/components/ui/pageable-table';
import { getData } from '~/lib/fetch';
import debounce from "lodash.debounce";
import {CustomerCompany} from '~/types/screen/master/mscs/mscsType'
import { LoadingSpinner } from '~/components/common/loadingSpinner';


const CustomerMaster: React.FC = () => {
  
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const [hasPermission, setHasPermission] = useState(false);

  const [searchCondition, setSearchCondition] = useState({
    company_name: '',
    corporate_number: '',
    company_address: ''
  });

  const [searchResults, setSearchResults] = useState<CustomerCompany[]>([]);
  const [showResults, setShowResults] = useState(false);

  // 権限検証
  useEffect(() => {
    const checkPermission = async () => {
      const currentUser = { role: 'admin' }; // テスト用：admin/user
      setHasPermission(currentUser.role === 'admin');
    };
    // checkPermission();
    
    handleSearch();
  }, []);

  // 検索処理
  // const handleSearch = async (e?: React.FormEvent) => {
  //   e?.preventDefault();
  //   const queryString = new URLSearchParams(searchCondition).toString();
  //   const url = `/api/mst_manage/corpration/info?${queryString}`;
  //   const data = await getData(url, {});
  //   // 50音順ソート
  //   const sortedResults = data.result.sort((custBefore : CustomerCompany , custNext : CustomerCompany) =>
  //     custBefore.company_name.localeCompare(custNext.company_name, "ja")
  //   );
  //   setSearchResults(sortedResults);
  //   setShowResults(true);

  //   if (sortedResults.length === 0) {
  //     window.alert("該当する企業が見つかりません");
  //   }
  // };
  const handleSearch = async () => {
    setIsLoading(true); // 検索中スピナー表示
  
    try {
      const queryString = new URLSearchParams(searchCondition).toString();
      const url = `/api/mst_manage/corpration/info?${queryString}`;
      const data = await getData(url, {});
  
      const sortedResults = data.result.sort(
        (custBefore: CustomerCompany, custNext: CustomerCompany) =>
          custBefore.company_name.localeCompare(custNext.company_name, "ja")
      );
  
      setSearchResults(sortedResults);
    } catch (error) {
      console.error("検索エラー:", error);
      setSearchResults([]); // エラー時は空結果
    } finally {
      setIsLoading(false); // 検索終了
    }
  };

    // 検索条件変更時に検索
  const debouncedSearch = debounce(handleSearch, 300);
  useEffect(() => {
    debouncedSearch();
    return () => debouncedSearch.cancel();
  }, [searchCondition]);

  // 企業名クリック処理
  const handleCustomerNameClick = (company: CustomerCompany) => {
    navigate(`/master/mscs03`, {
      state: {
        customerData: company,
        mode:"refer"
       }
    });
  };

  // if (!hasPermission) {
  //   return <div style={{ padding: '40px', textAlign: 'center' }}>アクセス権限がありません</div>;
  // }

  const breadcrumbItems = [
    { title: "トップ", link: "/common/cmtp01" },
    { title: "お客さま企業マスタ", link: "" }
  ];

  return (
    <div style={{
      padding: '10px',
      // maxWidth: '',
      margin: '0 auto',
      fontFamily: 'Meiryo, sans-serif',
      color: '#333',
      maxHeight: '100vh',
      // overflowY: 'auto'
    }}>
      <div className='mx-auto'></div>
      
      <BreadCrumb items={breadcrumbItems} />

      {/* 新規登録ボタン */}
      <div className="flex justify-center items-start mb-4">
        <Link 
          to="/master/mscs02" 
          className="text-blue-600 underline text-xl font-bold"
        >
          お客さま企業の新規登録へ
        </Link>
      </div>
      
      {/* ▼検索条件 */}
      <div className="space-y-4">
        <h3 className="text-lg font-bold border-l-4 pl-2 border-blue-800">▼検索条件</h3>
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex items-center gap-4">
            <label htmlFor="company_name" className="min-w-[100px] text-left">
              お客さま名
            </label>
            <Command className="flex-1">
              <CommandInput
                id="company_name"
                placeholder="会社名"
                value={searchCondition.company_name}
                onValueChange={(value) =>
                  setSearchCondition({ ...searchCondition, company_name: value })
                }
              />
            </Command>
          </div>

          <div className="flex items-center gap-4">
            <label htmlFor="corporate_number" className="min-w-[100px] text-left">
              法人番号
            </label>
            <Command className="flex-1">
              <CommandInput
                id="corporate_number"
                placeholder="13桁"
                value={searchCondition.corporate_number}
                onValueChange={(value) =>
                  setSearchCondition({ ...searchCondition, corporate_number: value })
                }
              />
            </Command>
          </div>

          <div className="flex items-center gap-4">
            <label htmlFor="company_address" className="min-w-[100px] text-left">
              所在地
            </label>
            <Command className="flex-1">
              <CommandInput
                id="company_address"
                placeholder="都道府県・市区町村"
                value={searchCondition.company_address}
                onValueChange={(value) =>
                  setSearchCondition({ ...searchCondition, company_address: value })
                }
              />
            </Command>
          </div>

          <div className="flex justify-center gap-4 mt-4">
            <Button
              variant="secondary"
              onClick={() =>
                setSearchCondition({
                  company_name: "",
                  corporate_number: "",
                  company_address: "",
                })
              }
              className="w-40 px-4 py-2 bg-gray-400 text-white rounded-md"
            >
              リセット
            </Button>
            <Button
              variant="default"
              type="submit"
              className="w-40 px-4 py-2 bg-blue-800 text-white rounded-md"
            >
              検索
            </Button>
          </div>
        </form>
      </div>



    
      {/* ▼確認・編集対象企業の選択 */}
      {/* {showResults && ( */}
      <Command>
        <h3 className="text-lg font-bold border-l-4 pl-2 border-blue-800 mb-4">
          ▼確認・編集対象企業の選択
        </h3>

        <CommandList>
          {isLoading ? (
          <div className="flex justify-center items-center py-4">
            <LoadingSpinner /> {/* ローディングスピナー */}
          </div>
        ) : searchResults.length > 0 ? (
            <PageableTable
              columns={columns}
              totalCount={searchResults.length}
              data={searchResults}
              pageCount={Math.ceil(searchResults.length / 10)}  // ページごとの表示数
            />
          ) : (
            <CommandEmpty>該当する企業が見つかりません</CommandEmpty>
          )}
        </CommandList>
      </Command>

      {/* )} */}
    </div>
  );
};

export default CustomerMaster;
