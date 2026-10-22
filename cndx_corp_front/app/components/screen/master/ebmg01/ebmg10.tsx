import { MetaFunction } from "@remix-run/node";
import { useLocation, useNavigate } from "@remix-run/react";
import React from "react";
import SectionTitle from "~/components/common/section-title";
import { Button } from "~/components/ui/button";

// 受信データ型を定義する
interface CustomerCompanyList {
  company_address: string;
  company_name: string;
  company_name_kana: string;
  corporate_number: string;
}

interface LocationState {
  customerData: CustomerCompanyList;
  mode: string;
}

interface ReceiptDataTargetProps {
  orgId: string | null | undefined;
  data: CustomerCompanyList;
}

export const meta: MetaFunction = () => {
  return [{ title: "対象選択" }, { name: "description", content: "receipt data target" }];
};

const ReceiptDataTarget: React.FC<ReceiptDataTargetProps> = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // 受け渡されたデータを取得する
  const locationState = location.state as LocationState;
  const customerData = locationState?.customerData;
  const mode = locationState?.mode;
  const corporateData = JSON.parse(sessionStorage.getItem("corporateData") || "{}");

  const categories: string[] = corporateData.agreement_category ?? [];
  const isMiddleEnabled = categories.some((code) => code.startsWith("0"));
  const isMajorEnabled = categories.some((code) => code.startsWith("1"));

  // const [orgPrefix, setOrgPrefix] = useState<string | null>(null);
  // const [dialogMessage, setDialogMessage] = useState<string | null>(null);

  // 顧客データを次のページに引き続き渡す
  const handleDirectDataClick = () => {
    navigate("/energy-building/ebrc03", {
      state: {
        customerData: customerData,
        mode: mode,
        dataSource: "direct", // データソース識別子を追加する
        permission: 1, // 権限を1に設定
      },
    });
  };

  const handleVisualizationDataClick = () => {
    navigate("/energy-building/ebrc03", {
      state: {
        customerData: customerData,
        mode: mode,
        dataSource: "visualization", // データソース識別子を追加する
        permission: 2, // 権限を2に設定
      },
    });
  };

  return (
    <div>
      <SectionTitle className="justify-center">作成・管理するレポートの種類を選択してください</SectionTitle>
      {/* 社外機能へのアクセス制御実装 start */}
      <div className="flex pt-10 py-2 justify-center">
        <Button
          variant="default"
          size="lg"
          className="text-sm px-4 py-2 rounded w-[300px] overflow-hidden text-ellipsis"
          onClick={handleDirectDataClick}
          disabled={!isMiddleEnabled}
        >
          ミドル向けレポート
        </Button>
      </div>
      {/* 社外機能へのアクセス制御実装 end */}
      <div className="flex py-2 justify-center">
        <Button
          variant="default"
          size="lg"
          className="text-sm px-4 py-2 rounded w-[300px] overflow-hidden text-ellipsis"
          onClick={handleVisualizationDataClick}
          disabled={!isMajorEnabled}
        >
          メジャー向けレポート
        </Button>
      </div>
    </div>
  );
};

export default ReceiptDataTarget;
