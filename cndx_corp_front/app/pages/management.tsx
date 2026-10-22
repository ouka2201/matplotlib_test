import axios, { isAxiosError } from "axios";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useSession } from "~/components/layout/session-provider";
import {
  Button,
  Icon,
  Input,
  Layout,
  styles,
  Text,
} from "../components/import";

// CNTable コンポーネントは統合するため import 削除

//APIレスポンスの型定義
type CustomerResponseItem = {
  bank_code: string; //金融機関コード
  bank_name: string; //金融機関名
  branch_code: string; //支店コード
  branch_name: string; //支店名
  user_cd: string; //担当者コード
  user_name: string; //担当名
  corporate_number: string; //法人番号
  corporation_name: string; //企業名
  building_id: string; //建物ID
  fiscal_year: string; //対象年度
  registration_seq: string; //登録回数
  report_status: string; //ステータス
  report_location: string; //PDF格納先
  creation_datetime: string; //作成日時
  creator: string; //作成者
  delete_flg: string | null; //削除フラグ
  file_id: string; //ファイルID
  report_type: string; //レポート区分
  update_datetime: string; //更新日時
  updateor: string; //更新者
};

// POSTリクエストのパラメータ用型
type PostRequestData = {
  task_id: string;
  creation_info: {
    bank_code: string;
    branch_code: string;
    corporate_number: string;
    fiscal_year: string;
    registration_seq: string;
    current_status: string;
  };
};

type PDFRequestData = {
  bank_code: string; //金融機関コード
  branch_code: string; //支店コード
  corporate_number: string; //法人番号
  building_id: string; //建物ID
  fiscal_year: string; //対象年度
  registration_seq: string; //登録回数
  file_id: string; //ファイルID
  report_location: string; //PDF格納先
  current_status: string; //現状ステータス
};

// const CHECKBOX_STATE = {
//   SELECTED: 1, // 選択されている状態
//   NOT_SELECTED: 0, // 選択されていない状態
//   DISABLED_SELECTED: 2, // 非活性状態
// };

// CNTableのヘッダー情報
const headers = [
  { key: "bank_name", label: "金融機関名", width: 10 },
  { key: "branch_name", label: "支店名", width: 10 },
  { key: "corporation_name", label: "企業名", width: 15 },
  { key: "user_name", label: "担当者", width: 10 },
  { key: "fiscal_year", label: "対象年度", width: 8 },
  { key: "creation_datetime", label: "情報登録日", width: 15 },
  { key: "registration_seq", label: "登録回数", width: 8 },
  { key: "report_status", label: "CO2企業カルテ", width: 15 },
];
const BASE_URL = process.env.VITE_API_URL;
// const BASE_URL = `${window.location.protocol}${process.env.VITE_API_URL}`
//const BASE_URL = "http://10.191.30.4:10072";

const CNmanagement: React.FC = () => {
  const { session, clearSession } = useSession();
  const [token, setToken] = useState<string | null>(session?.token ?? null);
  useEffect(() => {
    const fetchTokenFromSessionStorage = () => {
      if (typeof window !== "undefined") {
        const sessionData = sessionStorage.getItem("session");
        if (sessionData) {
          const sessionObj = JSON.parse(sessionData);
          if (sessionObj?.token) {
            setToken(sessionObj.token); // トークンがあればセット
          } else {
            console.log("No token found in session.");
            setToken(null); // トークンがない場合はnull
          }
        } else {
          console.log("Session data is not available.");
          setToken(null); // sessionDataがない場合もnull
        }
      }
    };

    fetchTokenFromSessionStorage(); // 初回実行
  }, []);

  const [customerItems, setCustomerItems] = useState<CustomerResponseItem[]>(
    []
  ); // APIから取得したアイテムを格納
  const prevItemsRef = useRef<CustomerResponseItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null); // エラーメッセージを格納
  const [searchErrorMessage, setSearchErrorMessage] = useState("");
  const [selectedItem, setSelectedItem] = useState<{
    bank_code: string;
    branch_code: string;
    corporate_number: string;
    building_id: string;
    fiscal_year: string;
    report_type: string;
    registration_seq: string;
    file_id: string;
  } | null>(null); // 選択状態を管理する
  const [processingItem, setProcessingItem] = useState<{
    bank_code: string;
    branch_code: string;
    corporate_number: string;
    building_id: string;
    fiscal_year: string;
    report_type: string;
    registration_seq: string;
    file_id: string;
  } | null>(null); // 選択状態を管理する
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false); // 処理中の状態管理
  const [searchResultsVisible, setSearchResultsVisible] = useState(false);
  const [bankName, setBankName] = useState(""); // 金融機関名
  const [branchName, setBranchName] = useState(""); // 支店名
  const [corporationName, setCorporationName] = useState(""); // 企業名
  const [fiscalYear, setFiscalYear] = useState(""); // 対象年度
  const [creationDateFrom, setCreationDateFrom] = useState(""); // 登録年月日(始)
  const [creationDateTo, setCreationDateTo] = useState(""); // 登録年月日(終)
  //const [inputSheetName, setInputSheetName] = useState(""); // シート名
  const [reportStatus, setReportStatus] = useState(""); // ステータス

  // テーブルの列幅管理用の状態とリファレンス
  const [columnWidths, setColumnWidths] = useState(headers.map((h) => h.width));
  const resizingIndex = useRef<number | null>(null);
  const startX = useRef<number>(0);
  const startWidths = useRef<number[]>([]);

  // 検索フォームの入力を更新
  const handleBankNameChange = (value: string) => {
    setBankName(value); // bankNameを更新
  };
  const handleBranchNameChange = (value: string) => {
    setBranchName(value);
  };
  const handleCorporationNameChange = (value: string) => {
    setCorporationName(value);
  };
  const handleFiscalYearChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const inputValue = event.target.value;
    const numericValue = inputValue.replace(/\D/g, ""); // 半角数字以外を除去
    setFiscalYear(numericValue);
  };
  const handleCreationDateFromChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newFromDate = event.target.value;

    // 日本時間の今日の日付を取得
    const today = new Date()
      .toLocaleDateString("ja-JP", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      })
      .replace(/\//g, "-");

    if (newFromDate > today) {
      setSearchErrorMessage("未来日は選択できません。");
      return;
    }
    if (creationDateTo && newFromDate > creationDateTo) {
      setSearchErrorMessage("開始日は終了日を超えています。");
      return;
    }
    setSearchErrorMessage(""); // エラーをクリア
    setCreationDateFrom(newFromDate);
  };

  const handleCreationDateToChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newToDate = event.target.value;

    // 日本時間の今日の日付を取得
    const today = new Date()
      .toLocaleDateString("ja-JP", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      })
      .replace(/\//g, "-");

    if (newToDate > today) {
      setSearchErrorMessage("未来日は選択できません。");
      return;
    }
    if (creationDateFrom && newToDate < creationDateFrom) {
      setSearchErrorMessage("終了日は開始日より前に設定できません。");
      return;
    }
    setSearchErrorMessage(""); // エラーをクリア
    setCreationDateTo(newToDate);
  };

  // useEffect(() => {
  //   console.log("bankName updated:", bankName);
  //   console.log("BranchName updated:", branchName);
  //   console.log("corporationName updated:", corporationName);
  //   console.log("fiscalYear updated:", fiscalYear);
  //   console.log("creationDateFrom updated:", creationDateFrom);
  //   console.log("creationDateTo updated:", creationDateTo);
  //   console.log("reportStatus updated:", reportStatus);
  // }, [
  //   bankName,
  //   branchName,
  //   corporationName,
  //   fiscalYear,
  //   creationDateFrom,
  //   creationDateTo,
  //   reportStatus,
  // ]);

  const statusOptions = [
    { label: "未作成", value: "0" },
    { label: "処理中", value: "1" },
    { label: "作成済", value: "2" },
    { label: "登録エラー", value: "8" },
    { label: "エラー", value: "9" },
  ];

  // const { session, clearSession } = useSession();
  // const [token, setToken] = useState<string | null>(session?.token ?? null);

  // useEffect(() => {
  //   if (typeof window !== "undefined") {
  //     const sessionData = sessionStorage.getItem("session");
  //     if (sessionData) {
  //       setToken(JSON.parse(sessionData).token);
  //     }
  //   }
  // }, [session]);

  const handleReportStatusChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    setReportStatus(event.target.value); // APIに送る数値データを状態にセット
  };
  // APIからデータを取得する関数
  const loadItems = useCallback(async () => {
    if (!token) {
      console.log("Token is null, cannot proceed with API request.");
      return; // トークンがnullの場合はAPIリクエストをしない
    }

    try {
      const requestUrl = `${BASE_URL}/api/report/status/inquiry`;
      //const requestUrl = `http://10.191.30.4:10072/api/report/status/inquiry`;
      const requestParams = {
        bank_name: bankName,
        branch_name: branchName,
        corporation_name: corporationName,
        fiscal_year: fiscalYear,
        creation_date_from: creationDateFrom,
        creation_date_to: creationDateTo,
        report_status: reportStatus,
      };

      const response = await axios.get(requestUrl, {
        params: requestParams,
        headers: { Authorization: `Bearer ${token}` }, // トークンをヘッダーに設定
      });

      setSearchErrorMessage(""); //エラー表示のクリア

      // APIレスポンスを処理
      if (Array.isArray(response.data.report_info_list)) {
        setCustomerItems(response.data.report_info_list);
      } else {
        setSearchErrorMessage("データの形式が正しくありません。");
      }
    } catch (error) {
      if (isAxiosError(error) && error.response) {
        const statusCode = error.response.status;
        const errorData = error.response.data;

        if (statusCode == 401) {
          clearSession();
          sessionStorage.removeItem("session");
          return window.location.href = "/session-expired";
        }

        console.error("サーバーエラー:", errorData);
        console.error("HTTPステータスコード:", statusCode);

        switch (statusCode) {
          case 400:
            console.error("バリデーションチェック不正");
            setSearchErrorMessage(
              errorData.error_message_list || "不正な入力です"
            );
            break;
          // case 404:
          //   console.error("リソース存在しない");
          //   setSearchErrorMessage(
          //     "エラー: リソースが存在しません。。システム担当者に連絡してください。"
          //   );
          //   break;
          // case 409:
          //   console.error("コンフリクトエラー");
          //   setSearchErrorMessage(
          //     "エラー: コンフリクトが発生しました。システム担当者に連絡してください。"
          //   );
          //   break;
          case 500:
            console.error("システムエラー");
            setSearchErrorMessage("エラー: サーバーエラーが発生しました。");
            break;
          default:
            console.error(`予期しないステータスコード: ${statusCode}`);
            setSearchErrorMessage(
              `予期しないエラー。システム担当者に連絡してください。: ステータスコード ${statusCode}`
            );
            break;
        }
      } else {
        // ネットワークエラーまたはその他のエラー
        console.error("APIリクエスト中にエラーが発生しました:", error);
        setSearchErrorMessage(
          "APIリクエスト中にエラーが発生しました。システム担当者に連絡してください。"
        );
      }
    }
  }, [
    token,
    bankName,
    branchName,
    corporationName,
    fiscalYear,
    creationDateFrom,
    creationDateTo,
    reportStatus,
    clearSession,
    navigate,
  ]);

  useEffect(() => {
    if (token) {
      console.log("Token is available, loading items...");
      loadItems(); // トークンが存在する場合にアイテムをロード
    }
  }, [token]);

  const PageSize = 50; // 1ページに表示する件数
  const [currentPage, setCurrentPage] = useState(1); // 現在のページ

  // customerItems を creation_datetime の降順でソート
  const sortedCustomerItems = [...customerItems].sort((a, b) =>
    b.creation_datetime.localeCompare(a.creation_datetime)
  );

  // 総件数
  const totalCount = customerItems.length;

  // 総ページ数
  const totalPages = Math.ceil(totalCount / PageSize);

  // 現在のページに表示するアイテムを取得
  const currentItems = sortedCustomerItems.slice(
    (currentPage - 1) * PageSize, // 現在のページの開始インデックス
    currentPage * PageSize // 現在のページの終了インデックス
  );

  // 表示されているアイテム数
  const displayCount = currentItems.length;

  // ページ変更
  const handlePageChange = (newPage: number) => {
    if (newPage > 0 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  // 次のページに進む
  const handleNextPage = () => {
    handlePageChange(currentPage + 1);
  };

  // 前のページに戻る
  const handlePrevPage = () => {
    handlePageChange(currentPage - 1);
  };

  // フォーム送信時の処理
  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setCurrentPage(1);
    loadItems(); // フォーム送信時にデータを取得
    setSearchResultsVisible(true); // 検索結果が表示されるようにする
  };

  // 検索条件リセット関数
  const handleReset = () => {
    setBankName("");
    setBranchName("");
    setCorporationName("");
    setFiscalYear("");
    setCreationDateFrom("");
    setCreationDateTo("");
    setReportStatus("");

    setCustomerItems([]); // 検索結果をクリア
    setSearchResultsVisible(false); // 検索結果の表示を非表示
    setCurrentPage(1); // ページ番号をリセット

    setErrorMessage(null); // エラーメッセージもクリア
    setSearchErrorMessage(""); //エラー表示のクリア
  };

  // 状態変更の監視
  useEffect(() => {
    const handleStatusChanged = () => {
      loadItems();
    };

    if (prevItemsRef.current.length > 0) {
      customerItems.forEach((item, index) => {
        const prevItem = prevItemsRef.current[index];
        if (prevItem && item.report_status !== prevItem.report_status) {
          handleStatusChanged();
        }
      });
    }
    prevItemsRef.current = customerItems;
  }, [customerItems, loadItems]);

  // チェックボックスの変更ハンドラー
  const handleCheckboxChange = (item: {
    bank_code: string;
    branch_code: string;
    corporate_number: string;
    building_id: string;
    fiscal_year: string;
    report_type: string;
    registration_seq: string;
    file_id: string;
    report_status: string;
  }) => {
    // create_status が 1か2の場合、チェックボックスは非活性
    if (
      item.report_status === "1" ||
      item.report_status === "2" ||
      item.report_status === "8"
    ) {
      return;
    }
    // すべてのキーが一致するかを比較
    if (
      selectedItem &&
      selectedItem.bank_code === item.bank_code &&
      selectedItem.branch_code === item.branch_code &&
      selectedItem.corporate_number === item.corporate_number &&
      selectedItem.building_id === item.building_id &&
      selectedItem.fiscal_year === item.fiscal_year &&
      selectedItem.report_type === item.report_type &&
      selectedItem.registration_seq === item.registration_seq &&
      selectedItem.file_id === item.file_id
    ) {
      // すべての値が同じ場合、選択解除
      setSelectedItem(null);
    } else {
      // 新しいアイテムを選択
      setSelectedItem({
        bank_code: item.bank_code,
        branch_code: item.branch_code,
        corporate_number: item.corporate_number,
        building_id: item.building_id,
        fiscal_year: item.fiscal_year,
        report_type: item.report_type,
        registration_seq: item.registration_seq,
        file_id: item.file_id,
      });
    }
  };

  // レポート作成ボタンのクリック処理
  const handleRunButtonClick = async () => {
    if (!selectedItem) {
      setErrorMessage("アイテムを選択してください");
      return;
    }

    // 選択されたアイテムを取得
    const selectedData = customerItems.find(
      (item) =>
        selectedItem &&
        item.bank_code === selectedItem.bank_code &&
        item.branch_code === selectedItem.branch_code &&
        item.corporate_number === selectedItem.corporate_number &&
        item.building_id === selectedItem.building_id &&
        item.fiscal_year === selectedItem.fiscal_year &&
        item.report_type === selectedItem.report_type &&
        item.registration_seq === selectedItem.registration_seq &&
        item.file_id === selectedItem.file_id
    );

    if (!selectedData) return;

    setIsLoading(true);
    setProcessingItem(selectedItem);

    try {
      // データを送信
      const response = await axios.post(
        //"http://10.191.30.4:10072/api/report/pdf/create", //API通信
        `${BASE_URL}/api/report/pdf/create`,
        {
          task_id: "0", // タスクID
          creation_info: {
            bank_code: selectedData.bank_code, // 金融機関コード
            branch_code: selectedData.branch_code, // 支店コード
            corporate_number: selectedData.corporate_number, // 法人番号
            fiscal_year: selectedData.fiscal_year, // 対象年度
            registration_seq: selectedData.registration_seq, // 登録回数
            current_status: selectedData.report_status, // 現状ステータス
          },
        } as PostRequestData, // 型アサーションを使って明示的に型を指定
        {
          headers: {
            Authorization: `Bearer ${token}`, // 認証トークン
          },
        }
      );

      // APIのレスポンスを処理（例：PDF作成成功メッセージ）
      console.log("PDF作成成功:", response.data);
    } catch (error) {
      if (isAxiosError(error) && error.response) {
        const errorData = error.response.data;
        const errorMessage = `PDF作成に失敗しました。`;
        console.error(`PDF作成に失敗。${errorData.message}`);
        const statusCode = error.response.status;
        setErrorMessage(errorMessage); // エラーメッセージをまとめて表示
        if (statusCode == 401) {
          clearSession();
          sessionStorage.removeItem("session");
          return window.location.href = "/session-expired";
        }
      } else {
        setErrorMessage("PDF作成時にエラーが発生しました。");
      }

      await loadItems();
    } finally {
      setIsLoading(false); // 処理終了：isLoading を false にする
      setProcessingItem(null);
      await loadItems(); // 最新データを取得
    }
  };

  const handleNavigate = (item: {
    bank_code: string;
    branch_code: string;
    corporate_number: string;
    building_id: string;
    fiscal_year: string;
    report_type: string;
    registration_seq: string;
    file_id: string;
    report_status: string;
  }) => {
    //console.log("Navigating with:", item); // デバッグ用
    navigate(`/cndx-corp/input_data`, {
      state: {
        bank_code: item.bank_code,
        branch_code: item.branch_code,
        corporate_number: item.corporate_number,
        fiscal_year: item.fiscal_year,
        registration_seq: item.registration_seq,
      },
    });
  };

  //PDF出力処理
  const handleDownloadPdf = async (item: CustomerResponseItem) => {
    if (item.report_status === "2") {
      try {
        // APIリクエストのデータを作成
        const requestData: PDFRequestData = {
          bank_code: item.bank_code, // 金融機関コード
          branch_code: item.branch_code, // 支店コード
          corporate_number: item.corporate_number, // 法人番号
          building_id: item.building_id, //建物ID
          fiscal_year: item.fiscal_year, // 対象年度
          registration_seq: item.registration_seq, // 登録回数
          file_id: item.file_id, //ファイルID
          report_location: item.report_location, //PDF格納先
          current_status: item.report_status, // 現状ステータス
        };

        // APIリクエスト (PDF作成 & 取得)
        const response = await axios.post(
          //`${BASE_URL}/api/report/pdf/output`,
          // "http://localhost:5000/api/report/pdf/output",
          `${BASE_URL}/api/report/pdf/output`,
          requestData,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`, // 認証トークンの追加
            },
            responseType: "blob", // PDFを受け取るための設定
          }
        );

        // PDFデータをBlobに変換
        const blob = new Blob([response.data], { type: "application/pdf" });

        // 一時URLを作成
        const url = URL.createObjectURL(blob);

        // ダウンロード用のリンクを作成
        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank"; // 新しいタブで開く
        const filename = item.report_location.split("/").pop() as string;
        link.download = filename;
        // link.download = `report_${item.bank_code}_${item.fiscal_year}.pdf`;
        document.body.appendChild(link);

        // ダウンロードを実行
        link.click();

        // リンクを削除
        document.body.removeChild(link);

        // URLを解放
        URL.revokeObjectURL(url);

        console.log("PDFダウンロード成功");
      } catch (error) {
        if (isAxiosError(error) && error.response) {
          const statusCode = error.response.status;
          if (statusCode == 401) {
            clearSession();
            sessionStorage.removeItem("session");
            return window.location.href = "/session-expired";
          }
        }
        console.error("PDFダウンロードに失敗しました:", error);
        setErrorMessage("PDFのダウンロードに失敗しました。");
      }
    } else {
      setErrorMessage("登録済みのアイテムのみダウンロード可能です");
    }
  };

  //テーブルの列幅調整機能
  const handleMouseDown = (
    index: number,
    event: React.MouseEvent<HTMLSpanElement, MouseEvent>
  ) => {
    resizingIndex.current = index;
    startX.current = event.clientX;
    startWidths.current = [...columnWidths];

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleMouseMove = (event: MouseEvent) => {
    if (resizingIndex.current === null) return;

    const deltaX = event.clientX - startX.current;
    const totalWidth = startWidths.current.reduce((sum, w) => sum + w, 0);
    const parentWidth = 100;
    const widthPerPixel = totalWidth / parentWidth;
    const index = resizingIndex.current;
    const newWidths = [...startWidths.current];

    const deltaPercent = deltaX * widthPerPixel * 0.08;
    if (
      newWidths[index] + deltaPercent < 5 ||
      newWidths[index + 1] - deltaPercent < 5
    )
      return;

    newWidths[index] += deltaPercent;
    newWidths[index + 1] -= deltaPercent;

    setColumnWidths(newWidths);
  };

  const handleMouseUp = () => {
    resizingIndex.current = null;
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
  };

  // CSS Modules用のクラスを返すヘルパー
  const getInputClass = (base: keyof typeof styles) => `${styles[base]} `;

  return (
    <div className={styles.mainContainer}>
      <div className={styles.layoutTitle}>
        <Text content="CNレポート作成・検索" size="xl" weight="bold" />
      </div>
      {searchErrorMessage && (
        <div className={styles.errorBox}>
          <div className={styles.errorBoxLabel}>
            <Icon name="error-pink" />
            <Text content="エラーがあります" color="white" weight="bold" />
          </div>
          <div className="content-error-detail">
            {Array.isArray(searchErrorMessage) ? (
              <ul>
                {searchErrorMessage.map((message, index) => (
                  <li key={index}>{message}</li>
                ))}
              </ul>
            ) : (
              <div className="content-error-detail-text-main">
                {searchErrorMessage}
              </div>
            )}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ width: "100%" }}>
        <Layout direction="column" gap={10}>
          <Text content="検索条件" size="lg" weight="bold" />
          <Text content="【金融機関情報】" size="md" />
          <Layout direction="row" gap={10} align="end">
            <Input
              supportText="金融機関名"
              value={bankName}
              onChange={handleBankNameChange} // handleBankNameChangeはeventを受け取る
            />
            <Input
              supportText="支店名"
              value={branchName}
              onChange={handleBranchNameChange}
            />
            <Input
              supportText="企業名"
              value={corporationName}
              onChange={handleCorporationNameChange}
            />
          </Layout>
          <Text content="【レポート情報】" size="md" />
          <Layout direction="row" gap={16} align="end">
            <div>
              <span className="cn-report-management-report-filter-details-content-object-year-label-text">
                対象年度(半角数字)
              </span>
              <div className="cn-report-management-report-filter-bank-content-object">
                <input
                  className={getInputClass("inputField")}
                  type="text"
                  value={fiscalYear}
                  onChange={handleFiscalYearChange}
                  placeholder="入力してください"
                />
              </div>
            </div>
            <div className="cn-report-management-report-filter-details-content-object-date">
              <span className="cn-report-management-report-filter-details-content-object-date-label-text">
                情報登録日
              </span>
              <div className="cn-report-management-report-filter-details-content-object-date-input">
                <input
                  type="date"
                  className="datebox"
                  value={creationDateFrom || ""}
                  onChange={handleCreationDateFromChange}
                  max={
                    creationDateTo
                      ? new Date(creationDateTo) < new Date()
                        ? creationDateTo
                        : new Date()
                          .toLocaleDateString("ja-JP", {
                            year: "numeric",
                            month: "2-digit",
                            day: "2-digit",
                          })
                          .replace(/\//g, "-")
                      : new Date()
                        .toLocaleDateString("ja-JP", {
                          year: "numeric",
                          month: "2-digit",
                          day: "2-digit",
                        })
                        .replace(/\//g, "-")
                  }
                />
                <Text content="~" />
                <input
                  type="date"
                  className="datebox"
                  value={creationDateTo || ""}
                  onChange={handleCreationDateToChange}
                  min={creationDateFrom || undefined}
                  max={new Date()
                    .toLocaleDateString("ja-JP", {
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                    })
                    .replace(/\//g, "-")}
                />
              </div>
            </div>
            <div className="cn-report-management-report-filter-details-content-object">
              <span className="cn-report-management-report-filter-details-content-object-label-text">
                ステータス
              </span>
              <select
                value={reportStatus}
                className="selectbox"
                onChange={handleReportStatusChange}
                style={{ color: reportStatus ? "black" : "#98a1b2" }}
              >
                <option value="" style={{ color: "#98a1b2" }}>
                  選択してください
                </option>
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </Layout>
          <Layout direction="row" gap={16} align="center">
            <Layout>
              <></>
            </Layout>
            <button
              type="button"
              onClick={handleReset}
              className="report-clear-button"
            >
              <span className="report-clear-button-text">クリア</span>
            </button>
            <div className="button-space"></div>
            <button type="submit" className="report-search-button">
              <span className="report-search-button-text">検索</span>
            </button>
            <Layout>
              <></>
            </Layout>
          </Layout>
        </Layout>
      </form>

      {/* テーブル部分（CNTable の表示・列幅調整機能を統合） */}
      {searchResultsVisible && (
        <div className={styles.CNtableContainer}>
          {/* ドロップダウンとボタン、件数表示 */}
          <Layout justify="between" padding={16} align="center">
            <Layout gap={16} align="center">
              <Button
                variant="secondary"
                text="レポート作成"
                onClick={handleRunButtonClick}
              />
            </Layout>
            {/* 件数表示 */}
            <Text
              content={`${totalCount.toLocaleString()} 件中  ${displayCount.toLocaleString()} 件`}
              width="100px"
            />
          </Layout>
          {errorMessage && (
            <div className={styles.CNtableError}>
              <Text content={errorMessage} color="red" />
            </div>
          )}
          <div
            className={styles.tableContainer}
            style={{ paddingRight: "16px" }}
          >
            <table className={styles.CNtable}>
              <thead style={{ position: "sticky", top: 0, zIndex: 10 }}>
                <tr>
                  <th className={styles.checkboxColumn}></th>
                  {headers.map((header, index) => (
                    <th
                      key={header.key}
                      style={{
                        width: `${columnWidths[index]}%`,
                        position: "relative",
                      }}
                    >
                      <Text
                        content={header.label}
                        size="sm"
                        color="gray-dark"
                        weight="bold"
                      />
                      {index < headers.length - 1 && (
                        <span
                          role="button"
                          tabIndex={0}
                          className={styles.resizeHandle}
                          onMouseDown={(e) => handleMouseDown(index, e)}
                        />
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
            </table>
          </div>
          <div className={styles.tableScroll}>
            <table className={styles.CNtable}>
              <tbody>
                {currentItems.length > 0 ? (
                  currentItems.map((item, index) => {
                    const isSelected =
                      selectedItem &&
                      selectedItem.bank_code === item.bank_code &&
                      selectedItem.branch_code === item.branch_code &&
                      selectedItem.corporate_number === item.corporate_number &&
                      selectedItem.building_id === item.building_id &&
                      selectedItem.fiscal_year === item.fiscal_year &&
                      selectedItem.report_type === item.report_type &&
                      selectedItem.registration_seq === item.registration_seq &&
                      selectedItem.file_id === item.file_id;

                    const checkboxDisabled =
                      isLoading || // API 実行中は全てのチェックボックスを無効化
                      (processingItem && // 処理中のアイテムがある場合
                        !(
                          processingItem.bank_code === item.bank_code &&
                          processingItem.branch_code === item.branch_code &&
                          processingItem.corporate_number ===
                          item.corporate_number &&
                          processingItem.building_id === item.building_id &&
                          processingItem.fiscal_year === item.fiscal_year &&
                          processingItem.report_type === item.report_type &&
                          processingItem.registration_seq ===
                          item.registration_seq &&
                          processingItem.file_id === item.file_id
                        )) ||
                      item.report_status === "2" ||
                      item.report_status === "1" ||
                      item.report_status === "8";

                    return (
                      <tr key={index}>
                        <td className={styles.checkboxColumn}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleCheckboxChange(item)}
                            disabled={checkboxDisabled} // 修正済み
                          />
                        </td>
                        {headers.map((header, colIndex) => (
                          <td
                            key={header.key}
                            style={{ width: `${columnWidths[colIndex]}%` }}
                            title={String(
                              item[header.key as keyof CustomerResponseItem]
                            )}
                          >
                            {header.key === "corporation_name" ? (
                              item.report_status === "8" ? ( // report_status が 8 の場合はリンクなし
                                <span>
                                  {" "}
                                  <Text content={item.corporation_name} />
                                </span>
                              ) : (
                                <span
                                  role="button"
                                  tabIndex={0}
                                  onClick={() => handleNavigate(item)}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter" || e.key === " ") {
                                      handleNavigate(item);
                                    }
                                  }}
                                  className={styles.linkButton}
                                  style={{ cursor: "pointer" }}
                                >
                                  {item.corporation_name}
                                </span>
                              )
                            ) : header.key === "report_status" ? (
                              item.report_status === "2" ? (
                                <span
                                  role="button"
                                  tabIndex={0}
                                  onClick={() => handleDownloadPdf(item)}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter" || e.key === " ") {
                                      handleDownloadPdf(item);
                                    }
                                  }}
                                  className={styles.linkButton}
                                  style={{ cursor: "pointer" }}
                                  title={
                                    item.report_status === "2"
                                      ? "作成済"
                                      : undefined
                                  }
                                >
                                  作成済
                                </span>
                              ) : (
                                <span
                                  title={
                                    // ツールチップとして表示
                                    item.report_status === "0"
                                      ? "未作成"
                                      : item.report_status === "1"
                                        ? "処理中"
                                        : item.report_status === "8"
                                          ? "登録エラー"
                                          : item.report_status === "9"
                                            ? "エラー"
                                            : "不明"
                                  }
                                >
                                  {processingItem &&
                                    processingItem.bank_code === item.bank_code &&
                                    processingItem.branch_code ===
                                    item.branch_code &&
                                    processingItem.corporate_number ===
                                    item.corporate_number &&
                                    processingItem.building_id ===
                                    item.building_id &&
                                    processingItem.fiscal_year ===
                                    item.fiscal_year &&
                                    processingItem.report_type ===
                                    item.report_type &&
                                    processingItem.registration_seq ===
                                    item.registration_seq &&
                                    processingItem.file_id === item.file_id ? (
                                    <Text content="処理中" />
                                  ) : item.report_status === "0" ? (
                                    <Text content="未作成" />
                                  ) : item.report_status === "1" ? (
                                    <Text content="処理中" />
                                  ) : item.report_status === "8" ? (
                                    <Text content="登録エラー" />
                                  ) : item.report_status === "9" ? (
                                    <Text content="エラー" />
                                  ) : (
                                    <Text content="不明" />
                                  )}
                                </span>
                              )
                            ) : (
                              <Text
                                content={
                                  item[header.key as keyof CustomerResponseItem]
                                }
                              />
                            )}
                          </td>
                        ))}
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={headers.length + 1}>
                      <Text content="データがありません" />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {totalCount > PageSize && (
            <div className="pagination">
              <button onClick={handlePrevPage} disabled={currentPage === 1}>
                ＜
              </button>
              {(() => {
                const pages = [];
                const totalPagesToShow = 7;
                const startPage = Math.max(
                  1,
                  currentPage - Math.floor(totalPagesToShow / 2)
                );
                const endPage = Math.min(
                  totalPages,
                  startPage + totalPagesToShow - 1
                );

                if (startPage > 1) {
                  pages.push(
                    <button key={1} onClick={() => handlePageChange(1)}>
                      1
                    </button>
                  );
                  if (startPage > 2)
                    pages.push(<span key="start-dots">…</span>);
                }

                for (let i = startPage; i <= endPage; i++) {
                  pages.push(
                    <button
                      key={i}
                      onClick={() => handlePageChange(i)}
                      className={currentPage === i ? "active" : ""}
                      disabled={currentPage === i}
                    >
                      {i}
                    </button>
                  );
                }

                if (endPage < totalPages) {
                  if (endPage < totalPages - 1)
                    pages.push(<span key="end-dots">…</span>);
                  pages.push(
                    <button
                      key={totalPages}
                      onClick={() => handlePageChange(totalPages)}
                    >
                      {totalPages}
                    </button>
                  );
                }

                return pages;
              })()}
              <button
                onClick={handleNextPage}
                disabled={currentPage === totalPages}
              >
                ＞
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CNmanagement;
