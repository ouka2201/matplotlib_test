//import React, { useState, useRef } from "react";
//import React from "react";
import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
//import axios, { isAxiosError } from "axios";
import axios, { isAxiosError } from "axios";
import { Icon, styles, Text } from "../components/import";
import "../styles/middle-test2.css";
import { useSession } from "./layout/session-provider";


type GetRequestInputData = {
  bank_code: string;
  branch_code: string;
  corporate_number: string;
  fiscal_year: string;
  registration_seq: string;
};

type BasicInfo = {
  area_information: string; // 事業所情報
  building_name: string; // 建物名
  industry_category_small: string; // 業種分類（小分類）
  address: string; // 住所
  gross_floor_area: string; // 延床面積
  electric_power_corporate_name: string; // 電力会社名
  ep_store_number: string; // 事業所コード
  //registration_number: string; //事業者登録番号
  customer_number_ep: string; // お客さま番号
  supply_point_number: string; // 供給地点番号
  contracted_power: string; // 契約電力
  start_year: string; // 年度
  start_month: string; // 月別
};

type BranchesEnergyInfo = {
  basic_info: BasicInfo;
  energy_usage_info: {
    import_raw_charcoal: number[]; // 輸入原料炭
    coking_coal: number[]; // コークス用原料炭
    pci_coal: number[]; // 吹込用原料炭
    import_ordinary_charcoal: number[]; // 輸入一般炭
    domestic_standard_coal: number[]; // 国産一般炭
    import_smokeless_coal: number[]; // 輸入無煙炭
    coal_coke: number[]; // 石炭コークス
    petroleum_coke: number[]; // 石油コークス
    fcc_coke: number[]; // FCCコーク
    coal_tar: number[]; // コールタール
    petroleum_asphalt: number[]; // 石油アスファルト
    crude_oil_condensate: number[]; // コンデンセート（NGL）
    crude_oil_condensate_except: number[]; // 原油（コンデンセート（NGL）を除く）
    gasoline: number[]; // 揮発油
    naphtha: number[]; // ナフサ
    jet_fuel: number[]; // ジェット燃料油
    kerosene: number[]; // 灯油
    light_oil: number[]; // 軽油
    heavy_oil_a: number[]; // Ａ重油
    heavy_oil_bc: number[]; // Ｂ・Ｃ重油
    lubricating_oil: number[]; // 潤滑油
    lpg: number[]; // 液化石油ガス（LPG）
    petroleum_hydrocarbon_gas: number[]; // 石油系炭化水素ガス
    lng: number[]; // 液化天然ガス（LNG）
    natural_gas: number[]; // 天然ガス（液化天然ガス（LNG）を除く。）
    coke_oven_gas: number[]; // コークス炉ガス
    blast_furnace_gas: number[]; // 高炉ガス
    power_generation_blast_furnace_gas: number[]; // 発電用高炉ガス
    converter_gas: number[]; // 転炉ガス
    city_gas: number[]; // 都市ガス
    industrial_steam: number[]; // 産業用蒸気
    industrial_except_steam: number[]; // 産業用以外の蒸気
    warm_water: number[]; // 温水
    cold_water: number[]; // 冷水
    electric_power: number[]; // 電気
  };
};


type ApiResponseData = BranchesEnergyInfo[];

const BASE_URL = process.env.VITE_API_URL;
// const BASE_URL = `${window.location.protocol}${process.env.VITE_API_URL}`
//const BASE_URL = "http://10.191.30.4:10072"


const InputDisplay: React.FC = () => {
  const location = useLocation();
  const Manegedata = location.state as GetRequestInputData | undefined; // 送られてきたデータを取得
  if (!Manegedata) {
    //console.log("データなし");
  }

  // パラメータが存在しない場合のデフォルト値を設定
  const requestData: GetRequestInputData = useMemo(
    () => ({
      bank_code: Manegedata?.bank_code ?? "",
      branch_code: Manegedata?.branch_code ?? "",
      corporate_number: Manegedata?.corporate_number ?? "",
      fiscal_year: Manegedata?.fiscal_year ?? "",
      registration_seq: Manegedata?.registration_seq ?? "",
    }),
    [Manegedata]
  );

  // 状態管理
  const [detailedInfo, setDetailedInfo] = useState<ApiResponseData>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false); // ローディング状態
  const [noData, setNoData] = useState<boolean>(false); // データが無い場合のフラグ
  const [currentPage, setCurrentPage] = useState(1); // 現在のページ
  const [itemsPerPage] = useState(1); // 1ページあたりの表示アイテム数
  const [totalPages, setTotalPages] = useState(1); // 総ページ数

  const navigate = useNavigate();
  const { session, clearSession } = useSession();
  const [token, setToken] = useState<string | null>(session?.token ?? null);

  // requestData のバリデーション
  const validateRequestData = (): boolean => {
    if (
      !requestData.bank_code ||
      !requestData.branch_code ||
      !requestData.corporate_number ||
      !requestData.fiscal_year ||
      !requestData.registration_seq
    ) {
      setErrorMessage("必要なパラメータが不足しています");
      return false;
    }
    return true;
  };

  // トークンの設定
  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
      }
    }
  }, [session]);

  // API リクエストデータ取得
  const getInputData = async () => {
    if (loading || !validateRequestData()) return; // 読み込み中またはパラメータが不足している場合は処理しない

    setLoading(true); // 読み込み開始時にローディングを true に
    setNoData(false); // データがない状態をリセット

    const apiUrl = `${BASE_URL}/api/building-energy/info/inquiry`;

    // 無効なURL形式をチェック
    // const validateUrl = (url: string) => {
    //   try {
    //     new URL(url); // URLが無効な場合、例外が発生
    //     return true;
    //   } catch (e) {
    //     setErrorMessage(`無効なURLです。: ${url}`);
    //     return false;
    //   }
    // };

    // if (!validateUrl(apiUrl)) return;

    try {
      const response = await axios.get<ApiResponseData | string>(apiUrl, {
        params: requestData,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      let data: ApiResponseData;

      // レスポンスが文字列の場合、パースしてオブジェクトに変換
      if (typeof response.data === "string") {
        try {
          const sanitizedData = response.data.replace(/NaN/g, "null");
          data = JSON.parse(sanitizedData) as ApiResponseData;
        } catch (error) {
          setErrorMessage("データの取得に失敗しました。");
          return;
        }
      } else {
        data = response.data;
      }

      // データの存在チェック
      if (Array.isArray(data) && data.length === 0) {
        setNoData(true);
      } else {
        setDetailedInfo(data);
      }
    } catch (error: unknown) {
      console.error("エラー発生", error);

      if (isAxiosError(error) && error.response) {
        const statusCode = error.response.status;
        if (statusCode === 401) {
          clearSession();
          sessionStorage.removeItem("session");
          return window.location.href = "/session-expired";
        }
        //const errorMsg = error.response?.data?.message || "詳細情報の取得に失敗しました";
        setErrorMessage(`予期しないエラーが発生しました。システム管理者へお問い合わせください。`);
      } else if (error instanceof Error) {
        setErrorMessage("予期しないエラーが発生しました");
      }
    } finally {
      setLoading(false); // ローディング終了
    }
  };

  // 初回実行時に getInputData を呼び出す
  useEffect(() => {
    if (token) {
      getInputData();
    }
  }, [requestData, token]);

  // 詳細情報が更新された時の処理
  useEffect(() => {
    if (detailedInfo) {
      const totalItems = detailedInfo.length;
      setTotalPages(Math.ceil(totalItems / itemsPerPage));
    }
  }, [detailedInfo, itemsPerPage]);

  // エラーメッセージの更新時
  useEffect(() => {
    if (errorMessage) {
      console.error("エラーメッセージ更新:", errorMessage);
    }
  }, [errorMessage]);

  // ローディング状態と noData の監視
  useEffect(() => {
    if (loading) {
      console.log("loading: true");
    }
    if (noData) {
      console.log("noData: true");
    }
  }, [loading, noData]);

  // ページ変更処理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // ページネーション用の表示するアイテムを取得
  const getCurrentPageData = () => {
    // console.log("detailedInfo:", detailedInfo); // 追加
    if (!detailedInfo) return [];
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    //return detailedInfo.slice(startIndex, endIndex);
    //const data = detailedInfo.slice(startIndex, endIndex);
    // console.log("getCurrentPageData():", data); // 追加
    return uniqueEnergyData.slice(startIndex, endIndex);
  };

  // 月に基づいて年を修正する関数
  const adjustYearForMonth = (
    month: number,
    startMonth: number,
    startYear: number
  ) => {
    // 月が `startMonth` から始まった場合、startMonth 以降はその年、それより前の月は翌年
    const adjustedYear = month >= startMonth ? startYear : startYear + 1;
    return adjustedYear;
  };

  // 合計を求める関数
  const calculateTotal = (arr: number[]) =>
    arr.reduce((acc, curr) => acc + curr, 0);
  console.log("detailedInfoの確認中:", detailedInfo);
  // 複数支店のデータを取得
  const branches = detailedInfo;
  // console.log(
  //   "確認: detailedInfo",
  //   Array.isArray(detailedInfo) ? detailedInfo.length : "データなし",
  //   detailedInfo
  // );
  // if (!branches || branches.length === 0) return null;

  // 配列を一元的に扱うため、対象となるフィールドをリストにする
  const energyFields: {
    field: keyof BranchesEnergyInfo["energy_usage_info"];
    label: string;
    unit: string;
  }[] = [
      {
        field: "electric_power",
        label: "電気",
        unit: "千kWh",
      },
      {
        field: "import_raw_charcoal",
        label: "輸入原料炭",
        unit: "t",
      },
      { field: "coking_coal", label: "コークス用原料炭", unit: "t" },
      { field: "pci_coal", label: "吹込用原料炭", unit: "t" },
      {
        field: "import_ordinary_charcoal",
        label: "輸入一般炭",
        unit: "t",
      },
      {
        field: "domestic_standard_coal",
        label: "国産一般炭",
        unit: "t",
      },
      {
        field: "import_smokeless_coal",
        label: "輸入無煙炭",
        unit: "t",
      },
      { field: "coal_coke", label: "石炭コークス", unit: "t" },
      { field: "petroleum_coke", label: "石油コークス", unit: "t" },
      { field: "fcc_coke", label: "FCCコーク", unit: "t" },
      { field: "coal_tar", label: "コールタール", unit: "t" },
      {
        field: "petroleum_asphalt",
        label: "石油アスファルト",
        unit: "t",
      },
      {
        field: "crude_oil_condensate",
        label: "コンデンセート（NGL）",
        unit: "kl",
      },
      {
        field: "crude_oil_condensate_except",
        label: "原油",
        unit: "kl",
      },
      { field: "gasoline", label: "揮発油", unit: "kl" },
      { field: "naphtha", label: "ナフサ", unit: "kl" },
      { field: "jet_fuel", label: "ジェット燃料油", unit: "kl" },
      { field: "kerosene", label: "灯油", unit: "kl" },
      { field: "light_oil", label: "軽油", unit: "kl" },
      { field: "heavy_oil_a", label: "Ａ重油", unit: "kl" },
      { field: "heavy_oil_bc", label: "Ｂ・Ｃ重油", unit: "kl" },
      { field: "lubricating_oil", label: "潤滑油", unit: "kl" },
      { field: "lpg", label: "液化石油ガス（LPG）", unit: "t" },
      {
        field: "petroleum_hydrocarbon_gas",
        label: "石油系炭化水素ガス",
        unit: "千m3",
      },
      { field: "lng", label: "液化天然ガス（LNG）", unit: "t" },
      {
        field: "natural_gas",
        label: "その他可燃性天然ガス",
        unit: "千m3",
      },
      {
        field: "coke_oven_gas",
        label: "コークス炉ガス",
        unit: "千m3",
      },
      {
        field: "blast_furnace_gas",
        label: "高炉ガス",
        unit: "千m3",
      },
      {
        field: "power_generation_blast_furnace_gas",
        label: "発電用高炉ガス",
        unit: "千m3",
      },
      { field: "converter_gas", label: "転炉ガス", unit: "千m3" },
      { field: "city_gas", label: "都市ガス", unit: "千m3" },
      { field: "industrial_steam", label: "産業用蒸気", unit: "GJ" },
      {
        field: "industrial_except_steam",
        label: "産業用以外の蒸気",
        unit: "GJ",
      },
      { field: "warm_water", label: "温水", unit: "GJ" },
      { field: "cold_water", label: "冷水", unit: "GJ" },
    ];

  type EnergyInfo = BranchesEnergyInfo["energy_usage_info"]; // energy_usage_infoの型を参照

  type EnergyItem = {
    field: keyof EnergyInfo;
    total: number;
    data: number[];
    label: string;
    unit: string;
    start_month: string[];
    start_year: string[];
  };

  // 合計を計算し、2つに分割
  const getEnergyData = (
    energyInfo: EnergyInfo,
    field: keyof EnergyInfo,
    basicInfo: { start_year: string; start_month: string }
  ): EnergyItem => {
    const data = energyInfo?.[field] || [];
    const total = calculateTotal(data);

    const roundedTotal = Math.round(total * 10_000) / 10_000;

    // month と year のデータを取得
    const startMonth = Number(basicInfo?.start_month) || 1; // デフォルトを1月にする
    const startYear = Number(basicInfo?.start_year) ?? new Date().getFullYear(); // 数値型に変換

    const months: number[] = [];
    const years: number[] = [];

    for (let i = 0; i < 12; i++) {
      const currentMonth = ((startMonth - 1 + i) % 12) + 1; // 1~12の範囲にする
      const currentYear = startYear + Math.floor((startMonth - 1 + i) / 12); // 数値計算

      months.push(currentMonth);
      years.push(currentYear);
    }

    //console.log(months, years); // 正しいデータが出力されるか確認

    // field を key として取得し、label を追加
    const label =
      energyFields.find((item) => item.field === field)?.label ?? "";
    const unit = energyFields.find((item) => item.field === field)?.unit ?? "";

    return {
      total: roundedTotal,
      data,
      field,
      label,
      unit,
      start_month: months.map(String),
      start_year: years.map(String),
    };
  };

  //const energyData: { department_branch_name: string; data: EnergyItem[] }[] =
  const energyData: { uniqueKey: string; basicInfo: BasicInfo; data: EnergyItem[] }[] =
    Array.isArray(branches)
      ? branches.map((branch) => {
        const energyInfo = branch.energy_usage_info;
        const basicInfo = branch.basic_info;
        // const branchName =
        // branch.basic_info?.department_branch_name || "不明な支店";

        if (!basicInfo || !basicInfo)
          return null;
        //return { department_branch_name: branchName, data: [] };

        const uniqueKey = `${basicInfo.area_information}_${basicInfo.building_name}_${basicInfo.industry_category_small}_${basicInfo.address}_${basicInfo.gross_floor_area}_${basicInfo.electric_power_corporate_name}_${basicInfo.ep_store_number}_${basicInfo.customer_number_ep}_${basicInfo.supply_point_number}_${basicInfo.contracted_power}`;


        const data = energyFields.map((energy) => ({
          ...energy,
          ...getEnergyData(
            energyInfo,
            energy.field as keyof EnergyInfo,
            basicInfo
          ),
        }));

        return { uniqueKey, basicInfo, data };
      }).filter((item): item is { uniqueKey: string; basicInfo: BasicInfo; data: EnergyItem[] } => item !== null)
      //return { department_branch_name: branchName, data };
      : [];

  const uniqueEnergyData = Array.from(
    new Map(energyData.map((item) => [item.uniqueKey, item])).values()
  );

  //console.log("エネルギーデータ:", JSON.stringify(energyData, null, 2));
  //console.log("エネルギーデータ2:", (energyData));
  // console.log("レンダリングチェック: ", errorMessage);
  if (errorMessage) {
    console.log("エラーメッセージが表示されるはず！", errorMessage);
  }

  if (loading) {
    return <div></div>; // loadingがtrueの間はaaaaを表示
  }
  console.log("return確認")
  return (
    <div className="main-container">
      {loading && <div>読み込み中...</div>}
      {/* エラーメッセージの表示 */}
      {errorMessage && (
        <div className={styles.errorBox}>
          <div className={styles.errorBoxLabel}>
            <Icon name="error-pink" />
            <Text content="エラーがあります" color="white" weight="bold" />
          </div>
          <div className="content-error-detail">
            {Array.isArray(errorMessage) ? (
              <ul>
                {errorMessage.map((message, index) => (
                  <li key={index}>{message}</li>
                ))}
              </ul>
            ) : (
              <div className="content-error-detail-text-main">
                {errorMessage}
              </div>
            )}
          </div>
        </div>
      )}

      {/* データが無い場合 */}
      {noData && !loading && !errorMessage && (
        <div>データがありません</div> // noDataがtrueの場合に表示
      )}
      {!loading &&
        !noData &&
        getCurrentPageData().map((branch, index) => {
          console.log("Rendering branch:", branch);
          const branchUniqueKey = `${branch.basicInfo.area_information}_${branch.basicInfo.building_name}_${branch.basicInfo.industry_category_small}_${branch.basicInfo.address}_${branch.basicInfo.gross_floor_area}_${branch.basicInfo.electric_power_corporate_name}_${branch.basicInfo.ep_store_number}_${branch.basicInfo.customer_number_ep}_${branch.basicInfo.supply_point_number}_${branch.basicInfo.contracted_power}`; const relatedEnergyData = uniqueEnergyData.filter((branchEnergyData) => {
            // console.log(" [フィルター前] 対象データ:", branchEnergyData);
            // console.log(" [比較対象] branch.basic_info.department_branch_name:", branch.basic_info.department_branch_name);
            // console.log(" [比較対象] branch.basic_info.area_information:", branch.basic_info.area_information);

            return (
              branchEnergyData.uniqueKey === branchUniqueKey
            );
            //return branchEnergyData.department_branch_name === branch.basic_info.department_branch_name;
          });

          console.log(" [フィルター後] relatedEnergyData:", relatedEnergyData);
          // const startIndex = (currentPage - 1) * itemsPerPage; // 現在のページの開始インデックス
          // const endIndex = startIndex + itemsPerPage; // 現在のページの終了インデックス

          // // ページごとのデータを取得
          // const energyDataForPage = relatedEnergyData.slice(
          //   startIndex,
          //   endIndex
          // );
          // // console.log(" [エネルギーデータ（ページ別）]", energyDataForPage);

          return (
            <div key={index}>
              {/* ページネーション */}
              <div className="pagination">
                {/* 前のページボタン */}
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1} // 1ページ目では非活性に
                >
                  ＜
                </button>

                {/* ページ番号ボタン */}
                {Array.from({ length: totalPages }, (_, index) => (
                  <button
                    key={index + 1}
                    onClick={() => handlePageChange(index + 1)}
                    className={currentPage === index + 1 ? "active" : ""} // 現在のページにはクラス active を追加
                  >
                    {index + 1}
                  </button>
                ))}

                {/* 次のページボタン */}
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages} // 最後のページでは非活性に
                >
                  ＞
                </button>
              </div>
              <div className="heading">
                <span className="heading-title">
                  {branch.basicInfo.area_information}
                  {/* {branch.basic_info.department_branch_name} */}
                </span>
              </div>
              <div className="frame-1">
                <div className="heading-2">
                  <span className="heading-title-3">基本情報</span>
                </div>
                <div className="frame-4">
                  <div className="frame-5">
                    <div className="preview-title">
                      <div className="frame-6">
                        <div className="frame-7">
                          <span className="title">事業所名</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell">
                      <div className="frame-8">
                        <div className="frame-9">
                          <span className="content">
                            {branch.basicInfo.area_information}
                            {/* {branch.basic_info.department_branch_name} */}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-title-a">
                      <div className="frame-b">
                        <div className="frame-c">
                          <span className="title-d">建物名</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-e">
                      <div className="frame-f">
                        <div className="frame-10">
                          <span className="content-11">
                            {branch.basicInfo.building_name}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="frame-12">
                    <div className="preview-title-13">
                      <div className="frame-14">
                        <div className="frame-15">
                          <span className="title-16">業種分類</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-17">
                      <div className="frame-18">
                        <div className="frame-19">
                          <span className="content-1a">
                            {branch.basicInfo.industry_category_small}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="frame-1b">
                    <div className="preview-title-1c">
                      <div className="frame-1d">
                        <div className="frame-1e">
                          <span className="title-1f">住所</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-20">
                      <div className="frame-21">
                        <div className="frame-22">
                          <span className="content-23">
                            {branch.basicInfo.address}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="frame-24">
                    <div className="preview-title-25">
                      <div className="frame-26">
                        <div className="frame-27">
                          <span className="title-28">延床面積</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-29">
                      <div className="frame-2a">
                        <div className="frame-2b">
                          <span className="content-2c">
                            {branch.basicInfo.gross_floor_area} m2
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="frame-2d">
                <div className="heading-2">
                  <span className="heading-title-3">電力情報</span>
                </div>
                <div className="frame-30">
                  <div className="frame-31">
                    <div className="preview-title-32">
                      <div className="frame-33">
                        <div className="frame-34">
                          <span className="title-35">契約先電気事業者</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-36">
                      <div className="frame-37">
                        <div className="frame-38">
                          <span className="content-39">
                            {branch.basicInfo.electric_power_corporate_name}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="frame-3a">
                    <div className="preview-title-3b">
                      <div className="frame-3c">
                        <div className="frame-3d">
                          <span className="title-3e">事業所コード</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-3f">
                      <div className="frame-40">
                        <div className="frame-41">
                          <span className="content-42">
                            {branch.basicInfo.ep_store_number}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-title-43">
                      <div className="frame-44">
                        <div className="frame-45">
                          <span className="title-46">お客さま番号</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-47">
                      <div className="frame-48">
                        <div className="frame-49">
                          <span className="content-placeholder">
                            {branch.basicInfo.customer_number_ep}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="frame-4a">
                    <div className="preview-title-4b">
                      <div className="frame-4c">
                        <div className="frame-4d">
                          <span className="title-4e">供給地点特定番号</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-4f">
                      <div className="frame-50">
                        <div className="frame-51">
                          <span className="content-placeholder-52">
                            {branch.basicInfo.supply_point_number}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-title-53">
                      <div className="frame-54">
                        <div className="frame-55">
                          <span className="title-56">契約電力</span>
                        </div>
                      </div>
                    </div>
                    <div className="preview-sell-57">
                      <div className="frame-58">
                        <div className="frame-59">
                          <span className="content-placeholder-5a">
                            {branch.basicInfo.contracted_power} kW
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="frame-5b">
                <div className="heading-2">
                  <span className="heading-title-3">エネルギー使用量</span>
                </div>
                <div className="frame-5e">
                  <div className="frame-5f">
                    {relatedEnergyData.map((branchEnergyData, branchIndex) => {
                      return (
                        <div key={branchIndex} className="branch-container">
                          {branchEnergyData.data.map((energy) => {
                            if (!energy.data || energy.data.length === 0) {
                              return null;
                            }
                            return (
                              <div key={energy.field} className="energy-item">
                                <div className="content-container">
                                  <div className="preview-title-60">
                                    <span className="title-63">
                                      {energy.label}
                                    </span>
                                    <div className="frame-61">
                                      <div className="frame-62"></div>
                                    </div>
                                  </div>
                                  <div className="frame-64">
                                    <div className="preview-sell-65">
                                      <div className="frame-66">
                                        <div className="frame-67">
                                          <span className="content-placeholder-68">
                                            {energy.total.toFixed(4)}{" "}
                                            {energy.unit}
                                          </span>
                                        </div>
                                      </div>
                                    </div>
                                    <div className="frame-69">
                                      {/* energy.data をそのまま使う */}
                                      {energy.data.map((value, index) => {
                                        const month = Number(
                                          energy.start_month[index]
                                        );
                                        const yearForMonth = adjustYearForMonth(
                                          month,
                                          Number(branch.basicInfo.start_month),
                                          Number(branch.basicInfo.start_year)
                                        );
                                        const monthString = `${yearForMonth}/${month
                                          .toString()
                                          .padStart(2, "0")}`;
                                        return (
                                          <div
                                            key={energy.start_month[index]}
                                            className="frame-6a"
                                          >
                                            <div className="title-input">
                                              <span className="date-input">
                                                {monthString}
                                              </span>
                                            </div>
                                            <div className="sell-input">
                                              <span className="text-data">
                                                {value != null ? value : "0"}
                                              </span>
                                            </div>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
              <div style={{ height: "150px" }}></div>
            </div>
          );
        })}
    </div>
  );
};
export default InputDisplay;
