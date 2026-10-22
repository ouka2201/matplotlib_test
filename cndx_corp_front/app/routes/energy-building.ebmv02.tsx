// import { MetaFunction } from "@remix-run/node";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ErrorHint from "~/components/common/error-hint";
import MasterLayout from "~/components/layout/master-layout";
import { columns } from "~/components/screen/common/ebmv02/columns";
import { Button } from "~/components/ui/button";
import { Command, CommandEmpty, CommandList } from "~/components/ui/command";
import { PageableTable } from "~/components/ui/pageable-table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import main_styles from "~/styles/middleBase.module.css";

import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import { Messages } from "~/constants/messages/message";
import { getData } from "../lib/fetch";

// export const meta: MetaFunction = () => {
//   return [
//     { title: "30分値データ管理_対象企業・事業所の選択" },
//     { name: "description", content: "ebmv02" },
//   ];
// };

type CorporateResponseItem = {
  agreement_category: string;
  company_name: string;
  corporate_number: string;
  company_address_prefecture: string;
  company_address_city: string;
  building_id: string;
  building_name: string;
  building_address_prefecture: string;
  building_address_city: string;
  ep_customer_number: string;
  supply_point_number: string;
  // agreementCategoryName?: string;
};

// 状態管理インターフェース
interface ThirtyMinState {
  isLoading: boolean;
  searchCondition: {
    companyName: string;
    corporateNumber: string;
    companyAddress: string;

    epCustomerNumber: string;
    supplyPointNumber: string;
    epOfficeCode: string;
    buildingName: string;
    buildingAddress: string;

    agreementCategory: string;
    agreementCategoryName: string;
  };
  corporateInfo: CorporateResponseItem[];
  initialCorporateInfo: CorporateResponseItem[];
  persistedAgreementCategoryOptions: { label: string; value: string }[];
  filteredAgreementCategoryOptions: { label: string; value: string }[];
  selectedItem: CorporateResponseItem | null;
  errorMessage: string | null;
  searchErrorMessage: string;
}

// アクションタイプ
type ThirtyMinAction =
  | { type: "SET_LOADING"; payload: boolean }
  | {
    type: "SET_SEARCH_CONDITION";
    payload: Partial<ThirtyMinState["searchCondition"]>;
  }
  | { type: "SET_CORPORATE_INFO"; payload: CorporateResponseItem[] }
  | { type: "SET_INITIAL_CORPORATE_INFO"; payload: CorporateResponseItem[] }
  | {
    type: "SET_PERSISTED_AGREEMENT_OPTIONS";
    payload: { label: string; value: string }[];
  }
  | {
    type: "SET_FILTERED_AGREEMENT_OPTIONS";
    payload: { label: string; value: string }[];
  }
  | { type: "SET_SELECTED_ITEM"; payload: CorporateResponseItem | null }
  | { type: "SET_ERROR_MESSAGE"; payload: string | null }
  | { type: "SET_SEARCH_ERROR_MESSAGE"; payload: string }
  | { type: "RESET_SEARCH" }; // 新しいアクションタイプを追加

// リデューサー関数
const thirtyMinReducer = (
  state: ThirtyMinState,
  action: ThirtyMinAction
): ThirtyMinState => {
  switch (action.type) {
    case "SET_LOADING":
      return { ...state, isLoading: action.payload };
    case "SET_SEARCH_CONDITION":
      return {
        ...state,
        searchCondition: {
          ...state.searchCondition,
          ...action.payload,
        },
      };
    case "SET_CORPORATE_INFO":
      return { ...state, corporateInfo: action.payload };
    case "SET_INITIAL_CORPORATE_INFO":
      return { ...state, initialCorporateInfo: action.payload };
    case "SET_PERSISTED_AGREEMENT_OPTIONS":
      return { ...state, persistedAgreementCategoryOptions: action.payload };
    case "SET_FILTERED_AGREEMENT_OPTIONS":
      return { ...state, filteredAgreementCategoryOptions: action.payload };
    case "SET_SELECTED_ITEM":
      return { ...state, selectedItem: action.payload };
    case "SET_ERROR_MESSAGE":
      return { ...state, errorMessage: action.payload };
    case "SET_SEARCH_ERROR_MESSAGE":
      return { ...state, searchErrorMessage: action.payload };
    case "RESET_SEARCH": // 新しいリセットアクション
      return {
        ...state,
        searchCondition: initialState.searchCondition,
        corporateInfo: state.initialCorporateInfo,
        selectedItem: null,
        searchErrorMessage: "",
      };
    default:
      return state;
  }
};

const generateItemKey = (item: CorporateResponseItem): string => {
  const keysToCompare = [
    "building_id",
    "agreement_category",
    "company_name",
    "corporate_number",
    "building_name",
    "ep_customer_number",
    "supply_point_number",
  ];
  return keysToCompare
    .map((key) => item[key as keyof CorporateResponseItem] || "")
    .join("::");
};

// パンくず
const breadcrumbItems = [
  { title: "電力30分値登録", link: "/energy-building/ebmv01" },
  { title: "お客さま・拠点の選択", link: "" },
];

// 初期状態
const initialState: ThirtyMinState = {
  isLoading: false,
  searchCondition: {
    companyName: "",
    companyAddress: "",
    corporateNumber: "",
    agreementCategory: "",
    epCustomerNumber: "",
    epOfficeCode: "",
    supplyPointNumber: "",
    buildingName: "",
    buildingAddress: "",
    agreementCategoryName: "",
  },
  corporateInfo: [],
  initialCorporateInfo: [],
  persistedAgreementCategoryOptions: [],
  filteredAgreementCategoryOptions: [],
  selectedItem: null,
  errorMessage: null,
  searchErrorMessage: "",
};

const ThirtyMinTargetSelection: React.FC = () => {
  const navigate = useNavigate();
  const [consentRoutes, setConsentRoutes] = useState<
    { value: string; label: string }[]
  >([]);
  const initialDataLoadedRef = useRef(false);
  const searchConditionRef = useRef(initialState.searchCondition);

  const [token] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      return sessionData ? JSON.parse(sessionData).token : null;
    }
    return null;
  });

  const [state, dispatch] = useReducer(thirtyMinReducer, initialState);

  // useEffect(() => {
  //   const from = sessionStorage.getItem("from") || "";
  //   if (from === "ebmv01") {
  //     sessionStorage.removeItem("from");
  //     location.reload();
  //   }
  // }, []);

  // 検索条件のrefを更新
  useEffect(() => {
    searchConditionRef.current = state.searchCondition;
  }, [state.searchCondition]);

  // データ取得関数
  const loadItems = useCallback(
    async (condition = searchConditionRef.current) => {
      function isErrorWithStatus(
        error: unknown
      ): error is { status: number; error_message_list?: string } {
        return (
          typeof error === "object" &&
          error !== null &&
          "status" in error &&
          typeof (error as { status: number }).status === "number"
        );
      }
      const params = {
        company_name: condition.companyName || "",
        company_address: condition.companyAddress || "",
        corporate_number: condition.corporateNumber || "",
        agreement_category: condition.agreementCategory || "",
        ep_customer_number: condition.epCustomerNumber || "",
        ep_office_code: condition.epOfficeCode || "",
        supply_point_number: condition.supplyPointNumber || "",
        building_name: condition.buildingName || "",
        building_address: condition.buildingAddress || "",
      };

      const query = new URLSearchParams(
        Object.entries(params)
          .filter(([_, v]) => v !== undefined && v !== "")
          .map(([k, v]) => [k, v as string])
      ).toString();

      const requestUrl = `/api/corp/building/list${query ? `?${query}` : ""}`;

      try {
        dispatch({ type: "SET_LOADING", payload: true });

        const data = await getData(requestUrl, {
          Authorization: `Bearer ${token}`,
        });

        if (data && Array.isArray(data.result)) {
          const items: CorporateResponseItem[] = data.result;

          const existingCategories = Array.from(
            new Set(items.map((item) => item.agreement_category))
          );

          const filtered = consentRoutes.filter((option) =>
            existingCategories.includes(option.value)
          );

          dispatch({ type: "SET_CORPORATE_INFO", payload: items });
          dispatch({ type: "SET_SEARCH_ERROR_MESSAGE", payload: "" });
          dispatch({
            type: "SET_FILTERED_AGREEMENT_OPTIONS",
            payload: filtered,
          });

          // 初回のみ初期データ保存
          if (!initialDataLoadedRef.current) {
            dispatch({ type: 'SET_INITIAL_CORPORATE_INFO', payload: items });
            initialDataLoadedRef.current = true;
          }
        } else {
          dispatch({ type: 'SET_SEARCH_ERROR_MESSAGE', payload: Messages.VALIDATION.data.invalid });
        }
      } catch (error: unknown) {
        console.error(Messages.VALIDATION.api.error, error);

        if (isErrorWithStatus(error)) {
          if (error.status === 401) {
            sessionStorage.removeItem("session");
            window.location.href = "/session-expired";
            return;
          }

          let errorMessage = "";
          switch (error.status) {
            case 400:
              errorMessage = error.error_message_list || Messages.VALIDATION_ERROR;
              break;
            case 500:
              errorMessage = Messages.SYSTEM_ERROR;
              break;
            default:
              errorMessage = Messages.UNKNOWN_ERROR;
              break;
          }
          dispatch({ type: 'SET_SEARCH_ERROR_MESSAGE', payload: errorMessage });

        } else {
          dispatch({
            type: 'SET_SEARCH_ERROR_MESSAGE',
            payload: Messages.VALIDATION.api.error
          });
        }
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    }, [token, consentRoutes, navigate]);

  // 初回データ取得
  useEffect(() => {
    if (token) {
      loadItems();
    }
  }, [token]);



  //同意書取得経路API呼び出し
  useEffect(() => {
    let isCancelled = false;

    const fetchMaster = async () => {
      if (!token) return;

      try {
        const masterEntries = [
          {
            name: "consent-route",
            params: {
              agreement_category__startswith: "",
            },
          },
        ];

        const data = await getMasterDataForCondition(masterEntries, token);

        if (!isCancelled) {
          const consentRouteData = data["consent-route"] || [];
          const transformedRoutes = consentRouteData.map((item: any) => ({
            value: item.id,
            label: item.name,
          }));

          setConsentRoutes(transformedRoutes);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          console.error(Messages.VALIDATION.agreement_category.error, err);

          // トークン期限切れエラーの処理
          if (isErrorWithStatus(err)) {
            if (err.status === 401) {
              sessionStorage.removeItem("session");
              window.location.href = "/session-expired";
              return;
            }

            // その他のエラーの処理
            console.error(Messages.VALIDATION.data.fetch_master_error, err);
          } else if (typeof err === "string" && err.includes("Token has expired")) {
            // 明示的なトークン期限切れメッセージの処理
            sessionStorage.removeItem("session");
            window.location.href = "/session-expired";
            return;
          }
        }
      }
    };

    if (token) {
      fetchMaster();
    }

    return () => {
      isCancelled = true;
    };
  }, [token, navigate]);

  // 検索条件更新
  const updateSearchCondition = useCallback((newValues) => {
    dispatch({ type: "SET_SEARCH_CONDITION", payload: newValues });
  }, []);

  // 検索実行
  const handleSearch = useCallback(async () => {
    console.log("検索条件:", state.searchCondition);
    try {
      await loadItems(state.searchCondition);
    } catch (error) {
      console.error(Messages.VALIDATION.api.search_error, error);
    }
  }, [loadItems, state.searchCondition]);

  // リセット - 修正版
  const handleReset = useCallback(() => {
    // リセットアクションをディスパッチ
    dispatch({ type: "RESET_SEARCH" });
  }, []);

  // 選択ボタンクリック
  const handleEbmv01 = () => {
    if (!state.selectedItem) {
      dispatch({ type: 'SET_ERROR_MESSAGE', payload: Messages.VALIDATION.data.unselected });
      return;
    }

    const agreementCategory = state.selectedItem.agreement_category ?? "";

    const selectedRoute = consentRoutes.find(
      (r) => r.value === agreementCategory
    );

    const agreementCategoryName = selectedRoute?.label ?? "";

    const payload = {
      ...state.selectedItem,
      agreementCategory,
      agreementCategoryName
    };
    sessionStorage.setItem("selectedCorporateItem", JSON.stringify(payload));
    navigate("/energy-building/ebmv01", { state: payload });
  };

  // 選択処理
  const handleCheckboxChange = (item: CorporateResponseItem) => {
    if (
      state.selectedItem &&
      generateItemKey(state.selectedItem) === generateItemKey(item)
    ) {
      dispatch({ type: "SET_SELECTED_ITEM", payload: null });
    } else {
      dispatch({ type: "SET_SELECTED_ITEM", payload: item });
    }
  };

  //テーブルの描画ロジック
  const renderCellContent = (
    column: any,
    item: CorporateResponseItem
  ): React.ReactNode => {
    const key = column.accessorKey as keyof CorporateResponseItem;

    if (key === "select") {
      const isSelected =
        state.selectedItem &&
        generateItemKey(state.selectedItem) === generateItemKey(item);

      return (
        <input
          type="radio"
          className="w-4 h-4 accent-green"
          name="ebmv02-select"
          checked={!!isSelected}
          onChange={() => handleCheckboxChange(item)}
        />
      );
    }

    let cellValue = "";

    switch (key) {
      case "company_address":
        cellValue = `${item.company_address_prefecture ?? ""}${item.company_address_city ?? ""
          }`;
        break;

      case "building_address":
        cellValue = `${item.building_address_prefecture ?? ""}${item.building_address_city ?? ""
          }`;
        break;

      case "agreement_category":
        const category = item.agreement_category as string;
        const matchedOption = consentRoutes.find(
          (option) => option.value === category
        );
        cellValue = matchedOption ? matchedOption.label : category;
        break;

      default:
        cellValue = String(item[key] ?? "");
        break;
    }

    return cellValue;
  };



  return (
    <MasterLayout breadcrumbItems={breadcrumbItems} isEditing={false}>
      <div className={main_styles.div_class}>
        {/* エラーメッセージ表示 */}
        {state.searchErrorMessage && (
          <ErrorHint
            message={state.searchErrorMessage}
            className="mb-4"
          />
        )}

        {/* 検索フォーム */}
        <div className="w-full flex gap-8 mb-10 text-sm">

          <div className="w-1/2 flex flex-col gap-4">
            {/* お客さま情報カード */}
            <div className="border border-gray-300 rounded">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="bg-gray-200 text-left p-2" colSpan={2}>お客さま基本情報</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="p-2 font-medium text-gray-600 w-[200px]">お客さま名</td>
                    <td className="p-2">
                      <input
                        id="companyName"
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        placeholder="xx株式会社"
                        value={state.searchCondition.companyName}
                        onChange={(e) =>
                          updateSearchCondition({ companyName: e.target.value })
                        }
                      />
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2 font-medium text-gray-600">法人番号</td>
                    <td className="p-2">
                      <input
                        id="corporateNumber"
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        placeholder="半角数字13桁"
                        value={state.searchCondition.corporateNumber}
                        onChange={(e) =>
                          updateSearchCondition({ corporateNumber: e.target.value })
                        }
                      />
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2 font-medium text-gray-600">本社所在地</td>
                    <td className="p-2">
                      <input
                        id="companyAddress"
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        placeholder="東京都xx区…"
                        value={state.searchCondition.companyAddress}
                        onChange={(e) =>
                          updateSearchCondition({ companyAddress: e.target.value })
                        }
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="w-1/2 flex flex-col gap-4">
            {/* 拠点情報カード */}
            <div className="border border-gray-300 rounded">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="bg-gray-200 text-left p-2" colSpan={2}>拠点情報</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="p-2 font-medium text-gray-600 w-[200px]">拠点名</td>
                    <td className="p-2">
                      <input
                        id="buildingName"
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        placeholder="xx拠点"
                        value={state.searchCondition.buildingName}
                        onChange={(e) =>
                          updateSearchCondition({ buildingName: e.target.value })
                        }
                      />
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2 font-medium text-gray-600">拠点所在地</td>
                    <td className="p-2">
                      <input
                        id="buildingAddress"
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        placeholder="東京都xx区…"
                        value={state.searchCondition.buildingAddress}
                        onChange={(e) =>
                          updateSearchCondition({ buildingAddress: e.target.value })
                        }
                      />
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2 font-medium text-gray-600">事業所コード</td>
                    <td className="p-2">
                      <input
                        id="officeCode"
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        placeholder="半角数字3桁"
                        value={state.searchCondition.epOfficeCode}
                        onChange={(e) =>
                          updateSearchCondition({ epOfficeCode: e.target.value })
                        }
                      />
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2 font-medium text-gray-600">お客さま番号</td>
                    <td className="p-2">
                      <input
                        id="epCustomerNumber"
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        placeholder="半角数字13桁"
                        value={state.searchCondition.epCustomerNumber}
                        onChange={(e) =>
                          updateSearchCondition({ epCustomerNumber: e.target.value })
                        }
                      />
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2 font-medium text-gray-600">供給地点特定番号</td>
                    <td className="p-2">
                      <input
                        id="supplyPointNumber"
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        placeholder="半角数字22桁"
                        value={state.searchCondition.supplyPointNumber}
                        onChange={(e) =>
                          updateSearchCondition({ supplyPointNumber: e.target.value })
                        }
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            {/* 同意書取得経路カード */}
            <div className="border border-gray-300 rounded">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="bg-gray-200 text-left p-2" colSpan={2}>同意書取得経路情報</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="p-2 font-medium text-gray-600 w-[200px]">同意書取得経路</td>
                    <td className="p-2">
                      <Select
                        value={state.searchCondition.agreementCategory || ""}
                        onValueChange={(value) => {
                          const selectedRoute = consentRoutes.find(
                            (route) => route.value === value
                          );
                          updateSearchCondition({
                            agreementCategory: value,
                            agreementCategoryName: selectedRoute?.label ?? "",
                          });
                        }}
                      >
                        <SelectTrigger className="h-8 text-sm border border-gray-300">
                          <SelectValue placeholder="選択してください" />
                        </SelectTrigger>
                        <SelectContent className="w-[300px]">
                          {consentRoutes.map((route) => (
                            <SelectItem key={route.value} value={route.value}>
                              {route.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="second" size="second" onClick={handleSearch}>
            検索
          </Button>
          <Button variant="third" size="third" onClick={handleReset}>
            リセット
          </Button>
        </div>

        {/* 結果表示 */}
        <Command className=" text-left">
          <div className="space-y-4 mb-10 mt-8"></div>
          <CommandList>
            {state.isLoading ? (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
              </div>
            ) : state.corporateInfo.length > 0 ? (
              <PageableTable<CorporateResponseItem, unknown>
                columns={columns}
                totalCount={state.corporateInfo.length}
                data={state.corporateInfo}
                pageCount={Math.ceil(state.corporateInfo.length / 10)}
                renderRow={(item, index) => (
                  <tr key={generateItemKey(item)}>
                    {columns
                      .flatMap((group) =>
                        "columns" in group ? group.columns : [group]
                      )
                      .map((column, colIndex) => (
                        <td
                          key={`${column.id}-${index}-${colIndex}`}
                          className="text-left p-2 break-words whitespace-pre-wrap"
                        >
                          {renderCellContent(column, item)}
                        </td>
                      ))}
                  </tr>
                )}
              />
            ) : (
              <CommandEmpty>{Messages.SEARCH_NONE}</CommandEmpty>
            )}
          </CommandList>
        </Command>
      </div>

      {/* 操作ボタン */}
      <div className="flex justify-end mt-4 relative z-10">
        <Button
          variant="second"
          onClick={handleEbmv01}
          disabled={!state.selectedItem}
        >
          選択
        </Button>
      </div>
    </MasterLayout>
  );
};

export default ThirtyMinTargetSelection;