import { useEffect, useState } from "react";
import { Outlet } from "@remix-run/react";
import HeaderWithB from "~/components/layout/headerWithBread";
import { CustomerCompany } from "~/types/screen/master/mscs/mscsType";
import { useLocation } from "react-router-dom";
// import Sidebar from "~/components/layout/sidebar";

// アプリケーションの主要なレイアウトコンポーネント
// すべての認証が必要なページで使用されます。
export default function App() {
  useEffect(() => {
    const originalHtmlOverflow = document.documentElement.style.overflow;
    const originalBodyOverflow = document.body.style.overflow;

    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";

    return () => {
      document.documentElement.style.overflow = originalHtmlOverflow;
      document.body.style.overflow = originalBodyOverflow;
    };
  }, []);

  const location = useLocation();
  const [corporateData, setCorporateData] = useState<CustomerCompany | null>(null);
  const [, setRegistrationSeq] = useState(0); // 登録回数
  const [, setStartYearMonth] = useState(""); // 対象年月(始)
  const [headerTitle, setHeaderTitle] = useState<string>("");
  useEffect(() => {
    const fetchCorporateData = () => {
      const stateData = location.state as CustomerCompany | undefined;
      if (stateData) {
        setCorporateData(stateData);
        sessionStorage.setItem("corporateData", JSON.stringify(stateData));
      } else {
        const stored = sessionStorage.getItem("corporateData");
        if (stored) {
          setCorporateData(JSON.parse(stored));
        } else {
          const dummyData: CustomerCompany = {
            //corporate_number: "2025062401001",
            corporate_number: "2025071400001",
            company_name: "○○株式会社",
            company_address_prefecture: "東京",
          };
          setCorporateData(dummyData);
          sessionStorage.setItem("corporateData", JSON.stringify(dummyData));
        }
      }
    };

    const fetchTargetYearMonth = () => {
      const storedReportInfo = sessionStorage.getItem("reportStatusInfo");
      let reportInfo: {
        start_year_month: string;
        registration_seq?: number;
      } | null = null;

      try {
        reportInfo = storedReportInfo ? JSON.parse(storedReportInfo) : null;
      } catch (e) {
        console.warn("reportStatusInfo のパースに失敗しました");
      }
      const start = reportInfo?.start_year_month ?? "";

      const stored = sessionStorage.getItem("maxRegistrationInfoList");
      const startYear = start.slice(0, 4);
      const list = stored ? JSON.parse(stored) : [];

      const fiscal_year = Number(startYear);

      const matched = list.reduce((res, curr) => {
        if (fiscal_year === Number(curr.fiscal_year)) {
          if (res == undefined) {
            return curr;
          } else if (res.max_registration_seq < curr.max_registration_seq) {
            return curr;
          } else {
            return res;
          }
        }
        return res;
      }, undefined);
      const maxRegistrationSeq = matched?.max_registration_seq ?? "none";

      const seq = reportInfo?.registration_seq;

      let registrationSeq;

      if (seq == null || seq === 0) {
        registrationSeq = maxRegistrationSeq == null || maxRegistrationSeq === "none" ? 1 : maxRegistrationSeq + 1;
      } else {
        registrationSeq = seq; // seq >= 1
      }
      setStartYearMonth(start);
      setRegistrationSeq(registrationSeq);
      sessionStorage.setItem("new_registrationSeq", JSON.stringify(registrationSeq));
    };
    fetchCorporateData();
    fetchTargetYearMonth();
  }, [location.state]);

  // パンくず
  const breadcrumbItems = [
    { title: "レポート作成・管理", link: "/energy-building/ebmg01" },
    {
      title: corporateData?.company_name,
      link: "/energy-building/ebrc04",
    },
    { title: `${headerTitle}`, link: "/energy-building-info/ebmg03" },
  ];

  return (
    <>
      <div className="flex flex-col h-screen overflow-hidden">
        <HeaderWithB breadcrumbItems={breadcrumbItems} />

        {/* ★ main は「高さを配るだけ」 */}
        <main className="flex-1 min-h-0 overflow-hidden">
          <Outlet context={{ setHeaderTitle }} />
        </main>
      </div>
    </>
    // <div className="flex flex-col min-h-screen">
    //   <HeaderWithB breadcrumbItems={breadcrumbItems} />
    //   <div className="flex flex-1 min-h-0">
    //     <main className="flex-1 min-h-0">
    //       <div className="flex h-full  w-full overflow-auto py-10">
    //         <Outlet /> {/* ここで左右スクロール */}
    //       </div>
    //     </main>
    //   </div>
    // </div>
  );
}
