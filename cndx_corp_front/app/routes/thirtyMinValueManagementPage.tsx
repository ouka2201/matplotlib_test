import { useEffect, useRef, useState } from "react";
import { useNavigate } from 'react-router-dom';
import "../styles/ThirtyMinValueManagementPage.css";
import { useEffect } from "react";

const ReadOnlyRow: React.FC<Props> = ({ value }) => (
  <div className="readonly-box">
    <span>{value || "※手動入力不可※"}</span>
  </div>
);

type Props = {
  label: string;
  value: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  // readOnly?: boolean;

};


interface CustomerInfo {
  customerName: string; // お客さま名
  corpNumber: string;   // 法人番号
  address: string;      // 所在地
}

interface BuildingInfo {
  building_id: string; 
  route: string;           // 同意取得経路（可编辑）
  officeName: string;      // 事業所名
  officeAddress: string;   // 事業所所在地
  epCustomerNumber: string;        // EPお客さま番号
  supplyNumber: string;    // 供給地点特定番号
}

type UploadRecord = {
  filename: string;
  startMonth: string; // yyyy/mm
  endMonth: string;   // yyyy/mm
  uploadedAt: string; // yyyy/mm/dd
};


export default function CustomerMasterForm() {
  const navigate = useNavigate();
  
  
  
  const [isDataSelected, setIsDataSelected] = useState(false);
  const [customerInfo, setCustomerInfo] = useState<CustomerInfo>({
    customerName: "",
    corpNumber: "",
    address: ""
  });
  
  const [buildingInfo, setBuildingInfo] = useState<BuildingInfo>({
    building_id: "",
    route: "",// 同意取得経路
    officeName: "",//建物・事業所名
    officeAddress: "",//建物所在地(都道府県)
    epCustomerNumber: "",//EPお客さま番号
    supplyNumber: "",//供給地点特定番号
  });

 

  
  const handleRouteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setBuildingInfo(prev => ({ ...prev, route: e.target.value }));
  };

 


  const [selectedFile, setSelectedFile] = useState<File | null>(null);
const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
const [uploadRecords, setUploadRecords] = useState<UploadRecord[]>([]);
const fileInputRef = useRef<HTMLInputElement | null>(null);

useEffect(() => {
  const data = sessionStorage.getItem("selectedCorporateItem");
  if (data) {
     try {
      const parsed = JSON.parse(data);

      // customerInfo
      setCustomerInfo({
        customerName: parsed.company_name || "",
        corpNumber: parsed.corporate_number || "",
        address: parsed.company_address || "",
      });

      // buildingInfo
      setBuildingInfo((prev) => ({
        ...prev,
        route: parsed.agreement_category || "",
        officeName: parsed.building_name || "",
        officeAddress:`${parsed.building_address_prefecture ?? ""} ${parsed.building_address_city ?? ""}`,
        epCustomerNumber: parsed.ep_customer_number || "",
        supplyNumber: parsed.supply_point_number || "",
      }));
      setIsDataSelected(true);

      console.log("前画面から受け取ったデータ:", parsed);
    } catch (e) {
      console.error("JSON解析エラー:", e);
    }
  }
    sessionStorage.setItem("user_id", "user0@example.com");
}, []);








// チェック部分
const handleRegister = async () => {
  const confirm = window.confirm("登録してよいか？");
  if (!confirm) return; 

  if (!selectedFile  || !selectedFile.name.toLowerCase().endsWith(".csv")) {
    alert("ファイルを選択してください");
    return;
  }
  const corpNumber = customerInfo.corpNumber;        
  const buildingId = buildingInfo.building_id;
  const epCustomerNumber = buildingInfo.epCustomerNumber;
  const userId = sessionStorage.getItem("user_id")!;

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("corp_number", corpNumber);
  formData.append("building_id", buildingId);
  formData.append("ep_customer_number", epCustomerNumber);
  formData.append("user_id", userId);

  const filename = selectedFile.name;
  formData.append("file", selectedFile);

  try {
    const response = await fetch("http://192.168.1.21:5000/api/file/per-30m-data", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("アップロードに失敗しました");
    }



     const responsedata = await fetch(
      "http://192.168.1.22:5000/api/file/per-30m-data", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
  const errorText = await response.text(); // 获取错误详情
  console.error("上传失败，后端返回：", errorText);
  throw new Error("アップロードに失敗しました");
}

    const resultdata = await responsedata.json();


   
    const startDate = resultdata.startDate ?? "";
    const endDate = resultdata.endDate ?? "";
    console.log("日付範囲APIの戻り値：", resultdata);

    if (!startDate || !endDate) {
      alert("取得年月日が取得できませんでした");
      return;
    }

    const uploadDate = new Date();
    const formatYM = (dateStr: string) => {
      if (!dateStr || dateStr.length !== 8) return "NaN/NaN";
      const year = dateStr.slice(0, 4);
      const month = dateStr.slice(4, 6);
      return `${year}/${month}`;
    };

    const formatYMD = (date: Date) => {
      return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, "0")}/${String(date.getDate()).padStart(2, "0")}`;
    };


    const newRecord: UploadRecord = {
      filename,
      startMonth: formatYM(startDate),
      endMonth: formatYM(endDate),
      uploadedAt: formatYMD(uploadDate),
    };

    setUploadedFiles(prev => [...prev, filename]);
    setUploadRecords(prev => {
      const filtered = prev.filter(record => record.filename !== filename);
      const updated = [...filtered, newRecord];
      return updated.sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
    });
    setSelectedFile(null);

    alert("アップロードが完了しました");
  } catch (error) {
    console.error(error);
    alert("アップロード中にエラーが発生しました");
  }
};





  return (
   <div className="page-container">
    
         <div className="page-title">
            <h2>30分値データ管理</h2>
         </div>
         <div className="page-title">
        <h3 className="section-title">▼対象企業・事業所の選択</h3> 
        </div>
        <div style={{ marginBottom: 10 }}>
          <button
            onClick={() => navigate('/energy-building/ebmv02')}
            className="choose-button"
          >
            マスタ登録済み情報から選択
          </button>
        </div>

        <div className="table-wrapper">
          
          <table className="left-table">
          <tbody>
             <tr>
             <td>
             お客さま名
              </td>
              <td className="readonly-cell">
               <ReadOnlyRow label="" value={customerInfo.customerName} />
               </td>
             </tr>

               <tr>
               <td>
               法人番号
              </td>
              <td className="readonly-cell">
               <ReadOnlyRow label="" value={customerInfo.corpNumber} />
               </td>
               </tr>
               <tr>
               <td>
               所在地
              </td>
               <td className="readonly-cell">
               <ReadOnlyRow label="" value={customerInfo.address} />
               </td>
               </tr>
               </tbody>
           </table>
           
          <table className="right-table">
          <tbody>
             <tr>
             <td>
             同意取得経路
              </td>
              <td className="readonly-cell">
              <ReadOnlyRow label="" value={buildingInfo.route} />
               </td>
             </tr>

               <tr>
               <td>
               事業所名
              </td>
              <td className="readonly-cell">
              <ReadOnlyRow label="" value={buildingInfo.officeName} />
               </td>
               </tr>
               <tr>
               <td>
               事業所所在地
              </td>
               <td className="readonly-cell">
               <ReadOnlyRow label="" value={buildingInfo.officeAddress} />
               </td>
               </tr>
               <tr>
               <td>
               EPお客さま番号
              </td>
               <td className="readonly-cell">
               <ReadOnlyRow label="" value={buildingInfo.epCustomerNumber} />
               </td>
               </tr>
               <tr>
               <td>
               供給地点特定番号
              </td>
               <td className="readonly-cell">
               <ReadOnlyRow label="" value={buildingInfo.supplyNumber} />
               </td>
               </tr>
               </tbody>
           </table>
           </div>
       
        <h3 className="section-title">▼30分値アップロード （新規アップロード）</h3> 
        <div> 
        <input
                type="file"
                ref={fileInputRef}
                style={{ display: "none" }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                if (file) {
                      setSelectedFile(file);
                         }
                      e.target.value = "";
                       }}
                      />
             
              <button className="action-button"
              onClick={() => {
                fileInputRef.current?.click();  
              }}
              disabled={!isDataSelected}>
            アップロードファイルを選択
          </button>
       
          <button
            onClick={handleRegister}
            className="last-button"
            disabled={!isDataSelected}
          >
            登録
          </button>
        </div>
        <div className="table-container">
        <table className="data-table">
          <tbody>
             <tr>
             <td style={{ padding: "10px", textAlign: "center" }}>
             ファイル名
              </td>
              <td>
              <input  type="text"
                      value={selectedFile?.name || "※手動入力不可※"}
                      readOnly
               style={{
                     border: "1px solid #ccc !important",
                     padding: "4px 6px",
                     fontSize: "14px",
                     backgroundColor: "#fff8dc",
                   }} 
                  />
               </td>
             </tr>
             </tbody>
           </table>
           </div>

        {isDataSelected  && ( 
        <>  

           <h3 className="section-title">▼30分値登録状況（登録状況の確認）</h3> 
        <div>
          <div 
         className="table-container">
          <table className="data-table">
            <thead>
              <tr >
                <th>開始月</th>
                <th>終了年月</th>
               
                <th>  アップロード日時</th>
                
              </tr>
              
              
            </thead>
            <tbody>
                 {uploadRecords.map((record, index) => (
              <tr key={index}className="table-row">
                <td>{record.startMonth}</td>
                <td>{record.endMonth}</td>
                <td>{new Date().toLocaleString()}</td>
              </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
      </>
       )}
       
    </div>
  );
}