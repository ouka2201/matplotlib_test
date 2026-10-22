import React, { useEffect, useState } from "react";
import MasterLayout from "~/components/layout/master-layout";
import { getData } from "~/lib/fetch";

import { SelectField } from "~/components/common/select-field";

type Criteria = {
  user_org_name: string;
  // user_org_id: string;
  sales_user_name: string;
  target_year_month: string;
};

const breadcrumbItems = [
  { title: "レポート一括ダウンロード", link: "" },
];

const selectFields = [
  {
    label:"担当組織", 
    name:"user_org_name", 
    Option:[{id:"A", name:"A"},{id:"B", name:"B"},{id:"C", name:"C"}], 
    value:"a"
  },
  {
    label:"顧客 所有者", 
    name:"sales_user_name", 
    Option:[{id:"A", name:"A"},{id:"B", name:"B"},{id:"C", name:"C"}],
    value:"a"
  },
  {
    label:"作成対象年月", 
    name:"target_year_month", 
    Option:[{id:"A", name:"A"},{id:"B", name:"B"},{id:"C", name:"C"}],
    value:"a"
  },
];

function App() {
  const [token, setToken] = useState<string | null>(null);
  // 検索条件
  const [criteria, setCriteria] = useState<Criteria>({
    user_org_name: "",
    user_org_id: "",
    sales_user_name: "",
    target_year_month: "",
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

  const handleChange = (name, newValue)=>{
    setValues(prev => ({ ...prev, [name]:newValue}));
  }

  // 検索&リセット
  const buttonComponent=()=>{
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
      const cleared = { user_org_name: "", sales_user_name: "", target_year_month: "" };

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

    // return <onSearch={handleSearch} onReset={handleReset}/>;
  
  };


  //ファイルダウンロード
  const [serverFiles, setServerFiles] = useState([
    {name:"dummy_2gb.txt",
      size: 2*1024*1024*1024
    }
  ]);
  // const [downloadTarget, setDownloadTarget] = useState("");
  const [status, setStatus] = useState("");

  const formatFileSize = (size) => {
    if (typeof size !== "number" || Number.isNaN(size)) {
      return "-";
    }
    if (size < 1024) {
      return `${size} B`;
    }
    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleDownload = async (fileName) => {
    try{
      const response=await getData("/api/report/power-report/contact_download");
      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName)
      document.body.appendChild(link);
      link.click();
    } catch (error){
      setStatus("ダウンロードエラー")
    }

  };


  return (
    <MasterLayout breadcrumbItems={breadcrumbItems} isEditing={false}>
      <section 
      className="card"
      >
      {/* 検索条件 */}
        <div className="space-y-4 mb-10">
          <div className="flex flex-wrap gap-x-4 gap-y-4 items-end w-full">
            {selectFields.map((item) => (
              <div key={item.name} className="flex flex-col gap-1 flex-1 min-w-[200px]">
                <SelectField
                  key={item.name}
                  label={item.label}
                  name={item.name}
                  options={item.Option}
                  value={item.value}
                  onChange={(value)=> handleChange(item.name, value)}
                />
              </div>         
            ))}
          </div>  
          {/* {onSearch && (
          <div className="flex items-end gap-2 flex-none">
            <Button variant="second" size="second" onClick={onSearch} className="w-[100px]">
              検索
            </Button>
            {onReset && (
              <Button variant="third" size="third" onClick={onReset} className="w-[100px]">
                リセット
              </Button>
            )} */}
        </div>
        {(serverFiles && serverFiles.length) > 0 ? (
          <>
          <ul>
            {serverFiles.map((file)=>(
              <li key={file.name}>
                <button onClick={()=>handleDownload(file.name)}>
                  {file.name}({formatFileSize(file.size)})
                </button>
              </li>
            ))}
          </ul>
          </>
        ) : (
          <p>該当するデータが見つかりません。</p>
        )}
      </section>
      {status && <p className="status">{status}</p>}
    </MasterLayout>
  );
}

export default App;
