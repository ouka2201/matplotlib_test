import { DoubleArrowLeftIcon, DoubleArrowRightIcon, TriangleDownIcon, TriangleUpIcon } from "@radix-ui/react-icons";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import SearchForm, { SearchField } from "~/components/common/search-form";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import { useSession } from "~/components/layout/session-provider";
import { Button } from "~/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Messages } from "~/constants/messages/message";
import { getData, postData } from "~/lib/fetch";
import UploadData from "~/routes/data-upload";
import buildingManagementStyle from "../styles/buildingManagement.module.css";
import { Icon, styles, Text } from "./import";

type Props = {
  customerData?: {
    company_name: string;
    company_name_kana: string;
    corporate_number: string;
    company_address_prefecture: string;
    company_address_city: string;
  };
};

// 各建物のグループオプション指定（group1 ～ group5）
type BuildingResponseItem = {
  building_id: string; // 建物ID
  // building_name: string; // 建物名
  location_identifier_name: string; // 拠点識別名
  building_address_prefecture: string; //建物所在地（都道府県）
  building_address_city: string; //建物所在地（都道府県）
  agreement_category: string; // 同意取得経路
  agreement_name?: string;
  industry_class_detail_code: string; // 産業分類(細分類)
  industry_class_detail_name: string; // 産業分類名称(細分類)
  updated_at: string; // 更新日時
  created_at: string; // 作成日時
  ep_office_code: string; // EP事業所コード
  ep_customer_number: string; // 顧客番号
  supply_point_number: string; // 供給点番号
  benchmark_denom: string; // 原単位分母
  benchmark_val: string; // 原単位分母数値
  building_consent_flag: string; // 建物の同意有無フラグ
  group1: string; // グループ1（例: "関東"）
  group2: string; // グループ2（例: "事務所"）
  group3: string; // グループ3（例: "自社利用"）
  group4: string; // グループ4（例: "10年未満"）
  group5: string; // グループ5（例: "等級1"）
  org_id: string; // 組織ID
};

// グループ設定情報の 1 グループ分
type GroupSettingInfoItem = {
  agreement_category: string; // 同意取得経路
  group_id: string; // グループID
  group_name: string; // グループ名（例: "エリア大"）
  group_options: string[]; // 選択肢（例: ["関東", "関西", "北海道", "中部"]）
  org_id: string; // 組織ID
  corporate_number: string; //法人番号
};

// group1〜group5のキー指定用
type SelectedGroupOptionKey = "group1" | "group2" | "group3" | "group4" | "group5";

// CNTableのヘッダー情報
const headers = [
  { key: "agreement_category", label: "同意取得経路", width: 20 },
  { key: "building_id", label: "拠点ID", width: 20 },
  { key: "location_identifier_name", label: "拠点名", width: 20 },
  { key: "industry_class_detail_code", label: "細分類番号", width: 20 },
  { key: "group1", label: "グループ1", width: 20 },
  { key: "group2", label: "グループ2", width: 20 },
  { key: "group3", label: "グループ3", width: 20 },
  { key: "group4", label: "グループ4", width: 20 },
  { key: "group5", label: "グループ5", width: 20 },
  { key: "created_at", label: "登録日", width: 20 },
];

const BuildingList: React.FC<Props> = ({ customerData }) => {
  const { session, clearSession } = useSession();
  const [orgId, setOrgId] = useState("");
  // EP管理者フラグ
  const [isEpAdmin, setIsEpAdmin] = useState(false);

  useEffect(() => {
    const userRoleFlags = JSON.parse(sessionStorage.getItem("userRoleFlags") || "{}");
    setIsEpAdmin(userRoleFlags.isEpAdmin ?? false);
  }, []);

  useEffect(() => {
    const sessionData = sessionStorage.getItem("session");
    if (sessionData) {
      const session = JSON.parse(sessionData);
      setOrgId(session?.authorityInfo?.org_id ?? "");
    }
  }, []);

  const [token, setToken] = useState<string | null>(null);
  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
      }
    }
  }, []);

  const [corporateNumber, setCorporateNumber] = useState<string>("");
  // useEffect(() => {
  //   const corpNo = sessionStorage.getItem("corporate_number") ?? "";
  //   setCorporateNumber(corpNo);
  // }, []);

  const [consentRoutes, setConsentRoutes] = useState<{ value: string; label: string }[]>([]);

  useEffect(() => {
    const fetchTokenFromSessionStorage = () => {
      if (typeof window !== "undefined") {
        const sessionData = sessionStorage.getItem("session");
        if (sessionData) {
          const sessionObj = JSON.parse(sessionData);
          if (sessionObj?.token) {
            setToken(sessionObj.token); // トークンがあればセット
          } else {
            console.log(Messages.VALIDATION.data.token_none);
            setToken(null); // トークンがない場合はnull
          }
        } else {
          console.log(Messages.VALIDATION.data.session_none);
          setToken(null); // sessionDataがない場合もnull
        }
      }
    };

    fetchTokenFromSessionStorage(); // 初回実行
  }, []);

  useEffect(() => {
    console.log(Messages.building_list.customer_data, customerData);
  }, [customerData]);

  const [allBuildingItems, setAllBuildingItems] = useState<BuildingResponseItem[]>([]);
  const [buildingItems, setBuildingItems] = useState<BuildingResponseItem[]>([]);
  const [allGroupSettings, setAllGroupSettings] = useState<GroupSettingInfoItem[]>([]);
  const [groupSettings, setGroupSettings] = useState<GroupSettingInfoItem[]>([]);
  const [groupSettingInfo, setGroupSettingInfo] = useState<GroupSettingInfoItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null); // エラーメッセージを格納
  const [searchErrorMessage, setSearchErrorMessage] = useState("");
  const [selectedItems, setSelectedItems] = useState<BuildingResponseItem[]>([]);
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false); // 処理中の状態管理
  const [agreementCategory, setAgreementCategory] = useState(""); // 同意書取得区分
  const [groupId, setGroupId] = useState(""); // グループ選択
  const [groupOption, setGroupOption] = useState(""); // グループ(選択肢)
  // テーブルの列幅管理用の状態とリファレンス
  const [columnWidths, setColumnWidths] = useState(headers.map((header) => header.width));

  const [registerSelectableGroupOptionItems, setRegisterSelectableGroupOptionItems] = useState<
    { label: string; value: string }[]
  >([]);
  const [searchCondition, setSearchCondition] = useState({
    buildingId: "",
    buildingName: "",
    agreementCategory: "",
    industryClassDetailCode: "",
    groupId: "",
    groupOption: "",
    updatedAtFrom: "",
    updatedAtTo: "",
  });
  const resizingIndex = useRef<number | null>(null);
  const startX = useRef<number>(0);
  const startWidths = useRef<number[]>([]);
  const [selectedAgreementCategory, setSelectedAgreementCategory] = useState<string>(""); //チェックボックス状態(同一取得区分)

  const [filteredAgreementCategoryOptions, setFilteredAgreementCategoryOptions] = useState<
    { label: string; value: string }[]
  >([]);

  const [groupIdOptions, setgroupIdOptions] = useState<{ label: string; value: string }[]>([]);

  useEffect(() => {
    if (selectedItems.length === 1) {
      setAgreementCategory(selectedItems[0].agreement_category);
    } else {
      setAgreementCategory("");
    }
  }, [selectedItems]);

  const [groupOptions, setGroupOptions] = useState<{ value: string; label: string }[]>([]);

  const [groupOptionCache, setGroupOptionCache] = useState<Record<string, { label: string; value: string }[]>>({});

  const handleDateChange = (type: "updatedAtFrom" | "updatedAtTo", value: string) => {
    const today = new Date()
      .toLocaleDateString("ja-JP", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      })
      .replace(/\//g, "-");

    if (value > today) {
      setSearchErrorMessage(Messages.building_list.feature_date_unselectable);
      return;
    }

    const other = type === "updatedAtFrom" ? searchCondition.updatedAtTo : searchCondition.updatedAtFrom;

    if (type === "updatedAtFrom" && other && value > other) {
      setSearchErrorMessage(Messages.building_list.invalid_start_date);
      return;
    }

    if (type === "updatedAtTo" && other && value < other) {
      setSearchErrorMessage(Messages.building_list.invalid_end_date);
      return;
    }

    setSearchErrorMessage("");

    setSearchCondition((prev) => ({
      ...prev,
      [type]: value,
    }));
  };

  const [registerGroupId, setRegisterGroupId] = useState<string | undefined>(); //グループ登録の状態管理(groupid)
  const [registerGroupOption, setRegisterGroupOption] = useState<string | undefined>(); //グループ登録の状態管理(groupoption)

  useEffect(() => {
    function isErrorWithStatus(error: unknown): error is { status: number; error_message_list?: string } {
      return (
        typeof error === "object" &&
        error !== null &&
        "status" in error &&
        typeof (error as { status: number }).status === "number"
      );
    }
    let isCancelled = false;

    const fetchMaster = async () => {
      if (!token) return;

      try {
        const masterEntries = [
          {
            name: "consent-route",
            params: {
              agreement_category__startswith: "1",
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
          console.error("同意書取得経路エラー:", err);

          // トークン期限切れエラーの処理
          if (isErrorWithStatus(err)) {
            if (err.status === 401) {
              sessionStorage.removeItem("session");
              window.location.href = "/session-expired";
              return;
            }

            // その他のエラーの処理
            console.error("マスターデータ取得エラー:", err);
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

  const sanitizeNaN = (obj: any): any => {
    if (obj === null || obj === undefined) return obj;
    if (typeof obj === "number" && isNaN(obj)) return 0;
    if (Array.isArray(obj)) return obj.map(sanitizeNaN);
    if (typeof obj === "object") {
      const cleaned: any = {};
      for (const key in obj) {
        cleaned[key] = sanitizeNaN(obj[key]);
      }
      return cleaned;
    }
    return obj;
  };

  const loadAllItems = useCallback(
    async (corporateNumberParam?: string) => {
      // 最新の corporateNumber を取得
      const corpNo = corporateNumberParam ?? sessionStorage.getItem("corporate_number") ?? "";
      if (!corpNo) {
        console.warn("corporate_number が取得できませんでした");
        return;
      }

      // state と sessionStorage にセット
      setCorporateNumber(corpNo);
      sessionStorage.setItem("corporate_number", corpNo);

      function isErrorWithStatus(error: unknown): error is { status: number; error_message_list?: string } {
        return (
          typeof error === "object" &&
          error !== null &&
          "status" in error &&
          typeof (error as { status: number }).status === "number"
        );
      }

      try {
        const requestUrl = `/api/building/info?corporate_number=${corpNo}`;
        const response = await getData(requestUrl, {
          Authorization: `Bearer ${token}`,
        });

        const safeResponse = sanitizeNaN(response);

        if (Array.isArray(response.building_info_list) && Array.isArray(response.group_setting_info)) {
          const normalizedList = safeResponse.building_info_list.map((item: BuildingResponseItem) => ({
            ...item,
            location_identifier_name: item.location_identifier_name ?? "",
            industry_class_detail_code: item.industry_class_detail_code ?? "",
          }));

          // group_setting_info の完全一致重複を削除
          const seen = new Set<string>();
          const uniqueGroupSettings = response.group_setting_info.filter((g) => {
            const key = JSON.stringify(g); // オブジェクト全体を文字列化
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });

          if (JSON.stringify(normalizedList) !== JSON.stringify(allBuildingItems)) {
            setAllBuildingItems(normalizedList);
          }

          // 最新の corporateNumber に紐づく groupSettings をセット
          setAllGroupSettings(uniqueGroupSettings);
          setGroupSettings(uniqueGroupSettings);
          setGroupSettingInfo(uniqueGroupSettings);

          setBuildingItems(normalizedList);
          setSearchErrorMessage("");

          const existingCategories = Array.from(
            new Set(response.building_info_list.map((item: BuildingResponseItem) => item.agreement_category))
          );

          const filtered = consentRoutes.filter((option) => existingCategories.includes(option.value));
          setFilteredAgreementCategoryOptions(filtered);
        } else {
          setSearchErrorMessage(Messages.VALIDATION.data.invalid);
          console.error(Messages.VALIDATION.data.invalid);
        }
      } catch (error: unknown) {
        console.error(Messages.VALIDATION.api.error, error);

        if (isErrorWithStatus(error)) {
          if (error.status === 401) {
            clearSession();
            sessionStorage.removeItem("session");
            return window.location.href = "/session-expired";
          }
          const errMsg =
            (error as any).data?.error_message_list?.[0] ||
            (error as any).data?.message ||
            (error.status === 400
              ? Messages.VALIDATION_ERROR
              : error.status === 500
                ? Messages.SYSTEM_ERROR
                : Messages.UNKNOWN_ERROR);

          setSearchErrorMessage(errMsg);
        } else {
          setSearchErrorMessage(Messages.VALIDATION.api.error);
        }
      }
    },
    [token, clearSession, navigate, consentRoutes]
  );

  const groupIdToKeyMap = useMemo(() => {
    const map: Record<string, keyof BuildingResponseItem> = {};
    allGroupSettings.forEach((groupSetting) => {
      const groupId = groupSetting.group_id;
      const lastDigit = groupId.slice(-1); // 末尾1文字を取り出す
      const groupKey = `group${lastDigit}` as keyof BuildingResponseItem;
      map[groupId] = groupKey;
    });
    return map;
  }, [allGroupSettings]);

  //建物情報登録後の画面更新
  const handleUploadComplete = async () => {
    setShowEnergyPopup(false);
    await loadAllItems(); // 一覧更新
    // toast({
    //   title: "一覧を更新しました",
    //   description: "最新の建物情報を表示しています。",
    // });
  };

  const filterItems = useCallback(() => {
    let filtered = allBuildingItems;
    const {
      buildingId,
      buildingName,
      agreementCategory,
      groupId,
      groupOption,
      industryClassDetailCode,
      updatedAtFrom,
      updatedAtTo,
    } = searchCondition;

    if (buildingId) {
      filtered = filtered.filter((item) => item.building_id?.toLowerCase().includes(buildingId.toLowerCase()));
    }

    if (buildingName) {
      filtered = filtered.filter((item) =>
        item.location_identifier_name?.toLowerCase().includes(buildingName.toLowerCase())
      );
    }

    if (agreementCategory) {
      filtered = filtered.filter((item) => item.agreement_category === agreementCategory);
    }

    if (groupId && !groupOption) {
      const groupKey = groupIdToKeyMap[groupId];
      if (groupKey) {
        filtered = filtered.filter((item) => item[groupKey] !== undefined && item[groupKey] !== null);
      }
    }

    if (groupId && groupOption) {
      const groupKey = groupIdToKeyMap[groupId];
      const setting = groupSettings.find(
        (s) =>
          String(s.group_id) === String(groupId) &&
          s.group_options.some((opt) => opt.trim().toLowerCase() === groupOption.trim().toLowerCase())
      );
      let groupValueNumber: string | null = null;
      if (setting) {
        const index = setting.group_options.findIndex(
          (opt) => opt.trim().toLowerCase() === groupOption.trim().toLowerCase()
        );
        if (index !== -1) {
          groupValueNumber = String(index + 1);
        }
      }
      if (groupKey && groupValueNumber !== null) {
        filtered = filtered.filter((item) => item[groupKey] === groupValueNumber);
      }
    }

    if (industryClassDetailCode) {
      filtered = filtered.filter((item) => item.industry_class_detail_code?.includes(industryClassDetailCode));
    }

    if (updatedAtFrom) {
      filtered = filtered.filter((item) => new Date(item.created_at) >= new Date(updatedAtFrom));
    }

    if (updatedAtTo) {
      const toDate = new Date(updatedAtTo);
      toDate.setHours(23, 59, 59, 999); // 終日の23:59:59.999までを含める
      filtered = filtered.filter((item) => new Date(item.created_at) <= toDate);
    }
    setBuildingItems(filtered);
  }, [allBuildingItems, searchCondition]);

  useEffect(() => {
    setGroupSettings([]);
    setAllGroupSettings([]);
    setGroupSettingInfo([]);

    if (token && customerData?.corporate_number && consentRoutes.length > 0) {
      loadAllItems(customerData.corporate_number);
    }
  }, [token, customerData, consentRoutes, loadAllItems]);

  useEffect(() => {
    const selectedCategory = searchCondition.agreementCategory;
    if (!selectedCategory || !allGroupSettings.length) return;

    const filteredGroups = allGroupSettings
      .filter((group) => group.agreement_category === selectedCategory && group.corporate_number === corporateNumber)
      // label の重複をまとめる
      .reduce<Record<string, { label: string; value: string }>>((acc, group) => {
        if (!acc[group.group_name]) {
          acc[group.group_name] = { label: group.group_name, value: String(group.group_id) };
        }
        return acc;
      }, {});

    setgroupIdOptions(Object.values(filteredGroups));
    setSearchCondition((prev) => ({ ...prev, groupId: "", groupOption: "" }));
  }, [searchCondition.agreementCategory, allGroupSettings]);

  const [initialBuildingItems, setInitialBuildingItems] = useState<BuildingResponseItem[]>([]);

  useEffect(() => {
    if (buildingItems.length > 0 && initialBuildingItems.length === 0) {
      setInitialBuildingItems(buildingItems);
    }
  }, [buildingItems, initialBuildingItems.length]);

  //agreementCategoryに紐づいたgroupIdを表示
  useEffect(() => {
    if (!agreementCategory || !groupSettings.length) return;

    // 該当する設定を抽出
    const matchedGroupSettings = groupSettings.filter(
      (group) => group.agreement_category === agreementCategory && group.corporate_number === corporateNumber
    );

    // データが存在する building に基づいて、使われている groupX を探す
    const filteredBuildings = initialBuildingItems.filter((item) => item.agreement_category === agreementCategory);

    const usedGroupIds = matchedGroupSettings.flatMap((setting) => {
      const groupId = setting.group_id;
      const lastDigit = Number(groupId.slice(-1)); // 下一桁を取得
      const groupKey = `group${lastDigit}` as SelectedGroupOptionKey;

      const isUsed = filteredBuildings.some((item) => item[groupKey] !== null && item[groupKey] !== undefined);
      return isUsed ? [groupId] : [];
    });

    // 実際に表示する options を生成
    const groupIdOpts = usedGroupIds
      .map((gid) => {
        const setting = matchedGroupSettings.find((s) => s.group_id === gid);
        return setting ? { label: setting.group_name, value: gid } : null;
      })
      .filter((opt): opt is { label: string; value: string } => opt !== null);

    setgroupIdOptions(groupIdOpts);

    // 不正な groupId をリセット
    if (!usedGroupIds.includes(groupId)) {
      setGroupId("");
    }
    setGroupOption("");
  }, [agreementCategory, groupSettings, initialBuildingItems, groupId]);

  //agreementCategory と groupId に紐づいた groupOption を表示する処理
  useEffect(() => {
    if (!agreementCategory || !groupId) {
      setGroupOptions([]);
      return;
    }

    const options = groupSettingInfo
      .filter(
        (group) =>
          group.agreement_category === agreementCategory &&
          group.group_id === groupId &&
          group.corporate_number === corporateNumber
      )
      .flatMap((group) =>
        group.group_options.map((label, index) => ({
          label,
          value: String(index + 1),
        }))
      );
    setGroupOptions(options);
  }, [agreementCategory, groupId, groupSettingInfo]);

  //building に実際に存在する値だけを選択肢として出す処理
  useEffect(() => {
    if (!agreementCategory || !groupId) {
      setGroupOptions([]);
      setGroupOption("");
      return;
    }

    let groupOptionList: { label: string; value: string }[] = [];

    const cacheKey = `${agreementCategory}_${groupId}`;

    if (groupOptionCache[cacheKey]) {
      groupOptionList = groupOptionCache[cacheKey];
      setGroupOptions(groupOptionList);
    } else {
      const filteredItems = initialBuildingItems.filter((item) => {
        return item.agreement_category === agreementCategory;
      });

      // groupSettings から groupId に対応する groupX キーを探す
      const matchedSetting = groupSettings.find(
        (setting) => setting.agreement_category === agreementCategory && setting.group_id === groupId
      );

      if (!matchedSetting) {
        setGroupOptions([]);
        setGroupOption("");
        return;
      }

      // group_id の末尾の数値で groupKey を決定
      const groupKey = `group${groupId.slice(-1)}` as SelectedGroupOptionKey;

      if (!groupKey) {
        setGroupOptions([]);
        setGroupOption("");
        return;
      }
      const groupOptionsSet = new Set<string>();

      // フィルタしたアイテムからグループオプションを収集
      filteredItems.forEach((item) => {
        const option = item[groupKey]; // group1 ～ group5 の値を取得
        if (option) {
          groupOptionsSet.add(option); // 値があれば Set に追加
        }
      });

      // オプションリストに変換
      groupOptionList = Array.from(groupOptionsSet).map((option) => {
        const label = findGroupOptionLabel(
          groupSettings, //  全グループ設定
          agreementCategory, //  同意取得経路
          groupId, //  グループID
          option //  値（例: "1", "2"）
        );
        return {
          label,
          value: option,
        };
      });

      // キャッシュに追加
      setGroupOptionCache((prev) => ({
        ...prev,
        [cacheKey]: groupOptionList,
      }));
      setGroupOptions(groupOptionList);
    }

    // 現在の選択肢が存在しない場合リセット
    if (!groupOptionList.find((opt) => opt.value === groupOption)) {
      setGroupOption("");
    }
  }, [groupId, agreementCategory, initialBuildingItems, groupSettings]);

  useEffect(() => {
    setGroupId("");
    setGroupOption("");
    setGroupOptions([]);
  }, [agreementCategory]);

  const findGroupOptionLabel = (
    allGroupSettings: GroupSettingInfoItem[],
    agreementCategory: string,
    groupId: string,
    optionValue: string
  ): string => {
    const targetGroup = allGroupSettings.find(
      (setting) =>
        setting.agreement_category === agreementCategory &&
        setting.group_id === groupId &&
        setting.corporate_number === corporateNumber
    );

    if (!targetGroup) return optionValue;

    // optionValue は値そのものとして扱い、配列から探す
    const matchedLabel = targetGroup.group_options.find((label, index) => {
      // 値は 1始まりの番号（value = index + 1）で渡っている前提なら比較可能
      return String(index + 1) === optionValue;
    });

    return matchedLabel ?? optionValue;
  };

  const getAgreementCategoryLabel = (value: string) => {
    const match = consentRoutes.find((opt) => opt.value === value);
    return match ? match.label : value;
  };

  // ソート機能
  const [sorting, setSorting] = useState<{ key: string; direction: "asc" | "desc" | null }>({
    key: "",
    direction: null,
  });

  const handleSort = (key: string) => {
    setSorting((prev) => {
      if (prev.key === key) {
        // 同じ列をクリックしたら昇順 → 降順 → 解除
        if (prev.direction === "asc") return { key, direction: "desc" };
        if (prev.direction === "desc") return { key: "", direction: null };
      }
      return { key, direction: "asc" };
    });
  };

  const pageSizeOptions = [5, 10, 20, 50];

  const [pagination, setPagination] = useState({
    pageIndex: 0, // 0スタート
    pageSize: 5, // 初期1ページあたり件数
  });

  // ソート後の全件
  const sortedAllItems = useMemo(() => {
    if (!sorting.key || !sorting.direction) return buildingItems;
    return [...buildingItems].sort((a, b) => {
      const aValue = String(a[sorting.key as keyof BuildingResponseItem] ?? "");
      const bValue = String(b[sorting.key as keyof BuildingResponseItem] ?? "");

      if (sorting.direction === "asc") return aValue.localeCompare(bValue, "ja");
      if (sorting.direction === "desc") return bValue.localeCompare(aValue, "ja");
      return 0;
    });
  }, [buildingItems, sorting]);

  const totalCount = sortedAllItems.length;
  const totalPages = Math.ceil(totalCount / pagination.pageSize);

  useEffect(() => {
    if (pagination.pageIndex >= totalPages) {
      setPagination((prev) => ({ ...prev, pageIndex: totalPages > 0 ? totalPages - 1 : 0 }));
    }
  }, [totalPages]);

  const startIndex = pagination.pageIndex * pagination.pageSize;
  const startRow = Math.min(totalCount, startIndex + 1);
  const endRow = Math.min(startIndex + pagination.pageSize, sortedAllItems.length);

  const currentItems = sortedAllItems.slice(startIndex, endRow);

  // フォーム送信時の処理
  const handleSearch = () => {
    filterItems();
  };

  const handleReset = () => {
    // 検索条件の入力値をすべてクリア
    const emptyValues = {
      buildingId: "",
      buildingName: "",
      agreementCategory: "",
      industryClassDetailCode: "",
      groupId: "",
      groupOption: "",
      updatedAtFrom: "",
      updatedAtTo: "",
    };
    setSearchCondition(emptyValues);

    // 一覧を初期状態に戻す
    setBuildingItems(allBuildingItems);
  };
  const [selectionGroup, setSelectionGroup] = useState<{
    agreement_category: string;
    org_id: string;
    corporate_number: string;
  } | null>(null);

  // チェックボックスの変更ハンドラー
  const handleCheckboxChange = (clickedItem: BuildingResponseItem) => {
    setSelectedItems((prev) => {
      const isSelected = prev.some(
        (selected) =>
          selected.building_id === clickedItem.building_id &&
          selected.agreement_category === clickedItem.agreement_category
      );

      if (isSelected) {
        const updated = prev.filter(
          (selected) =>
            !(
              selected.building_id === clickedItem.building_id &&
              selected.agreement_category === clickedItem.agreement_category
            )
        );

        if (updated.length === 0) {
          setSelectionGroup(null);
          setSelectedAgreementCategory("");
        }

        return updated;
      } else {
        const newSelected = [...prev, clickedItem];

        if (prev.length === 0) {
          setSelectedAgreementCategory(clickedItem.agreement_category);
          setSelectionGroup({
            agreement_category: clickedItem.agreement_category,
            org_id: clickedItem.org_id,
            corporate_number: customerData?.corporate_number ?? "",
          });
        }

        return newSelected;
      }
    });
  };

  const isAllSelected =
    currentItems.length > 0 &&
    currentItems.every((item) =>
      selectedItems.some(
        (selected) =>
          selected.agreement_category === item.agreement_category &&
          selected.building_id === item.building_id &&
          selected.org_id === item.org_id &&
          selected.location_identifier_name === item.location_identifier_name &&
          selected.industry_class_detail_code === item.industry_class_detail_code
      )
    );

  const handleSelectAllChange = () => {
    // agreement_category が複数の場合は選択できない
    const agreementCategories = new Set(currentItems.map((item) => item.agreement_category));
    if (agreementCategories.size > 1) {
      return; // 非活性のまま
    }

    if (isAllSelected) {
      // 選択解除
      setSelectedItems((prev) =>
        prev.filter(
          (selected) =>
            !currentItems.some(
              (item) =>
                selected.agreement_category === item.agreement_category &&
                selected.building_id === item.building_id &&
                selected.location_identifier_name === item.location_identifier_name &&
                selected.org_id === item.org_id &&
                selected.industry_class_detail_code === item.industry_class_detail_code
            )
        )
      );

      // 選択解除なので selectionGroup もリセット
      setSelectionGroup(null);
      setSelectedAgreementCategory("");
    } else {
      // 全選択
      setSelectedItems((prev) => {
        const newSelected = [
          ...prev,
          ...currentItems.filter(
            (item) =>
              !prev.some(
                (selected) =>
                  selected.agreement_category === item.agreement_category &&
                  selected.building_id === item.building_id &&
                  selected.location_identifier_name === item.location_identifier_name &&
                  selected.org_id === item.org_id &&
                  selected.industry_class_detail_code === item.industry_class_detail_code
              )
          ),
        ];

        // 一括選択後に selectionGroup を更新
        const firstItem = currentItems[0];
        setSelectedAgreementCategory(firstItem.agreement_category);
        setSelectionGroup({
          agreement_category: firstItem.agreement_category,
          org_id: firstItem.org_id,
          corporate_number: customerData?.corporate_number ?? "",
        });

        return newSelected;
      });
    }
  };

  const getGroupLabel = (
    agreementCategory: string,
    groupNo: number,
    groupValue: string,
    groupSettings: GroupSettingInfoItem[]
  ): string => {
    const groupIdSuffix = groupNo.toString();
    const targetGroup = groupSettings.find(
      (g) =>
        g.agreement_category === agreementCategory &&
        g.group_id.endsWith(groupIdSuffix) &&
        g.corporate_number === corporateNumber
    );
    if (!targetGroup || !targetGroup.group_options) return "";
    const optionIndex = Number(groupValue) - 1;
    return targetGroup.group_options[optionIndex] ?? "";
  };

  const handleBuildingClick = (item: BuildingResponseItem) => {
    const buildingData = {
      corporate_number: customerData?.corporate_number ?? "",
      agreement_code: item.agreement_category,
      org_id: item.org_id,
      building_id: item.building_id,
    };

    sessionStorage.setItem("selectedBuildingData", JSON.stringify(buildingData));
    navigate("/master/msbd04", { state: { customerData, fromScreen: "msbd01", } });
  };

  //テーブルの列幅調整機能
  const handleMouseDown = (index: number, event: React.MouseEvent<HTMLSpanElement, MouseEvent>) => {
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
    if (newWidths[index] + deltaPercent < 5 || newWidths[index + 1] - deltaPercent < 5) return;

    newWidths[index] += deltaPercent;
    newWidths[index + 1] -= deltaPercent;

    setColumnWidths(newWidths);
  };

  const handleMouseUp = () => {
    resizingIndex.current = null;
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
  };

  // 最初のプルダウンの選択肢を変更する処理
  const registerSelectableGroupIdOptions = useMemo(() => {
    if (selectedItems.length === 0) return [];

    const selectedAgreementCategories = Array.from(new Set(selectedItems.map((item) => item.agreement_category)));

    const options = groupSettings
      .filter((group) => selectedAgreementCategories.includes(group.agreement_category))
      .map((group) => ({
        value: group.group_id,
        label: group.group_name,
      }));

    return Array.from(new Map(options.map((item) => [item.value, item])).values());
  }, [selectedItems, groupSettings]);

  //登録プルダウンのリセット
  useEffect(() => {
    if (registerSelectableGroupIdOptions.length === 0) {
      setRegisterGroupId("");
      setRegisterGroupOption("");
    }
  }, [registerSelectableGroupIdOptions]);

  const [adjustedGroupSettings, setAdjustedGroupSettings] = useState<GroupSettingInfoItem[]>([]);

  useEffect(() => {
    if (!groupSettings.length || !selectionGroup?.corporate_number) return;

    const filtered = groupSettings.filter(
      (g) =>
        g.agreement_category === selectionGroup.agreement_category && // agreement_category に絞る
        g.corporate_number === selectionGroup.corporate_number // corporate_number に絞る
    );
    setAdjustedGroupSettings(filtered);
  }, [groupSettings, selectionGroup?.corporate_number, selectionGroup?.agreement_category, registerGroupId]);

  //登録API
  const handleUpdateGroupSetting = async () => {
    if (selectedItems.length === 0) {
      setErrorMessage(Messages.building_list.select_checkbox_target);
      return;
    }

    if (!registerGroupId || registerGroupOption === "") {
      setErrorMessage(Messages.building_list.select_group);
      return;
    }

    const isErrorWithStatus = (error: unknown): error is { status: number; error_message_list?: string } =>
      typeof error === "object" &&
      error !== null &&
      "status" in error &&
      typeof (error as { status: number }).status === "number";

    setIsLoading(true);

    try {
      const token = sessionStorage.getItem("token") ?? "TEST_TOKEN";
      const selectedItem = selectedItems[0];
      const selectedOrgId = selectedItem.org_id;
      const selectedSetting = groupSettings.find(
        (setting) =>
          setting.group_id === registerGroupId &&
          setting.agreement_category === selectedItem.agreement_category &&
          setting.corporate_number === corporateNumber
      );

      if (!selectedSetting) {
        setErrorMessage(Messages.building_list.group_none);
        return;
      }

      const optionIndex = selectedSetting.group_options.findIndex((opt) => opt === registerGroupOption);

      if (optionIndex === -1) {
        setErrorMessage(Messages.building_list.invalid_option);
        return;
      }

      const requestPayload = {
        corporate_number: customerData?.corporate_number ?? "",
        agreement_category: selectedItem.agreement_category,
        org_id: selectedOrgId,
        building_ids: selectedItems.map((item) => item.building_id),
        selected_options: {
          [registerGroupId]: String(optionIndex + 1),
        },
      };

      await postData("/api/building/group/master/detail", requestPayload, {
        Authorization: `Bearer ${token}`,
      });
    } catch (error: unknown) {
      console.error(Messages.VALIDATION.api.error, error);

      if (isErrorWithStatus(error)) {
        if (error.status === 401) {
          clearSession();
          sessionStorage.removeItem("session");
          return window.location.href = "/session-expired";
        }

        const errMsg =
          (error as any).data?.error_message_list?.[0] ||
          (error as any).data?.message ||
          (error.status === 400
            ? Messages.VALIDATION_ERROR
            : error.status === 500
              ? Messages.SYSTEM_ERROR
              : Messages.UNKNOWN_ERROR);

        setErrorMessage(errMsg);
      } else {
        setErrorMessage(Messages.building_list.group_update_error);
      }
    } finally {
      setIsLoading(false);
      await loadAllItems(); // データ再取得
    }
  };

  const cleanOptions = (opts?: { value: string | null | undefined; label: string }[]) =>
    opts
      ? opts
        .map((opt) => ({
          value: opt.value?.trim() ?? "",
          label: opt.label?.trim() ?? "",
        }))
        .filter((opt) => opt.value !== "" && opt.label !== "")
      : [];

  const getRow1Fields = (condition: Record<string, string>): SearchField[] => [
    { id: "buildingId", label: "拠点ID", type: "text" },
    { id: "buildingName", label: "拠点名", type: "text" },
    {
      id: "agreementCategory",
      label: "同意取得経路",
      type: "select",
      options: consentRoutes,
    },
    {
      id: "groupId",
      label: "グループ選択",
      type: "select",
      options: condition.agreementCategory ? cleanOptions(groupIdOptions) : [{ label: "選択不可", value: "" }],
      disabled: !condition.agreementCategory,
    },
    {
      id: "groupOption",
      label: "グループ（選択肢）",
      type: "select",
      options: condition.groupId ? cleanOptions(groupOptions) : [{ label: "選択不可", value: "" }],
      disabled: !condition.groupId,
    },
    {
      id: "industryClassDetailCode",
      label: "日本産業分類 細分類番号",
      type: "text",
      placeholder: "産業分類コード",
    },
  ];

  const [showEnergyPopup, setShowEnergyPopup] = useState(false);
  const uploadData = [
    {
      company_name: customerData?.company_name,
      company_name_kana: customerData?.company_name_kana,
      corporate_number: customerData?.corporate_number,
    },
  ];

  return (
    <div className="w-full max-w-[1480px]  mt-4">
      <div className="w-full max-w-[1480px] space-y-4 mb-10 mt-12">
        {searchErrorMessage && (
          <div className={styles.errorBox}>
            <div className={styles.errorBoxLabel}>
              <Icon name="error-pink" />
              <Text content="エラーがあります" color="white" weight="bold" />
            </div>
            <div className={buildingManagementStyle.contentErrorDetail}>
              {Array.isArray(searchErrorMessage) ? (
                <ul>
                  {searchErrorMessage.map((message, index) => (
                    <li key={index}>{message}</li>
                  ))}
                </ul>
              ) : (
                <div className={buildingManagementStyle.contentErrorDetailText}>{searchErrorMessage}</div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="w-full max-w-[1480px] space-y-4 mb-10 mt-8 relative">
        <div className="absolute top-0 right-0 flex flex-col gap-2">
          <Button
            variant="primary"
            size="third"
            onClick={() => navigate("/master/msbg01", { state: { customerData } })}
            className="w-[200px] "
          >
            拠点グループマスタ設定
          </Button>
          {isEpAdmin && (
            <Button onClick={() => setShowEnergyPopup(true)} variant="primary" size="third" className="w-[200px]">
              拠点情報登録
            </Button>
          )}
          <UploadData
            data={uploadData}
            modalOpen={showEnergyPopup}
            onOpenChange={() => setShowEnergyPopup(false)}
            uploadFileType="buildingMaster"
            onUploadComplete={handleUploadComplete}
          />
        </div>
        <Text content="絞り込み条件" size="lg" weight="bold" />
        <div className="pt-12 space-y-4">
          <div className="flex gap-x-6">
            <SearchForm
              fields={getRow1Fields(searchCondition)}
              columns={3}
              values={searchCondition}
              onValueChange={(newValues) => {
                const isGroupIdChanged = newValues.groupId !== undefined;

                if (isGroupIdChanged) {
                  const selectedGroupSetting = groupSettingInfo.find(
                    (setting) =>
                      setting.group_id === newValues.groupId &&
                      setting.agreement_category === searchCondition.agreementCategory &&
                      setting.corporate_number === corporateNumber
                  );
                  if (selectedGroupSetting) {
                    const uniqueOptions = Array.from(
                      new Map(
                        selectedGroupSetting.group_options
                          .map((opt) => opt.trim())
                          .filter((opt) => opt)
                          .map((opt) => [opt.toLowerCase(), { value: opt, label: opt }])
                      ).values()
                    ).filter((opt) => opt.label !== "" && opt.value !== "");

                    setGroupOptions(uniqueOptions.filter((opt) => opt.value && opt.value.trim() !== ""));
                  } else {
                    setGroupOptions([]);
                  }
                }

                setSearchCondition((prev) => ({
                  ...prev,
                  ...newValues,
                  ...(isGroupIdChanged ? { groupOption: "" } : {}),
                }));
              }}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <div className="pt-2">
            <span className="text-sm font-medium text-[#667085]">情報登録日</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="date"
              className="border rounded px-3 py-2 text-sm min-w-[160px]"
              value={searchCondition.updatedAtFrom || ""}
              onChange={(e) => handleDateChange("updatedAtFrom", e.target.value)}
              max={
                searchCondition.updatedAtTo
                  ? new Date(searchCondition.updatedAtTo) < new Date()
                    ? searchCondition.updatedAtTo
                    : new Date().toISOString().slice(0, 10)
                  : new Date().toISOString().slice(0, 10)
              }
            />
            <Text content="~" />
            <input
              type="date"
              className="border rounded px-3 py-2 text-sm min-w-[160px]"
              value={searchCondition.updatedAtTo || ""}
              onChange={(e) => handleDateChange("updatedAtTo", e.target.value)}
              min={searchCondition.updatedAtFrom || undefined}
              max={new Date().toISOString().slice(0, 10)}
            />
          </div>
        </div>
        <div className="flex gap-4 justify-end mt-4">
          <Button variant="second" size="third" onClick={handleReset} className="w-[100px]">
            クリア
          </Button>
          <Button variant="primary" size="second" onClick={handleSearch} className="w-[100px]">
            検索
          </Button>
        </div>
      </div>

      {/* テーブル部分（CNTable の表示・列幅調整機能を統合） */}
      {
        <div className="w-full max-w-[1480px] ">
          <div className={buildingManagementStyle.CNtableContainer} style={{ overflowX: "auto" }}>
            {/* ドロップダウンとボタン、件数表示 */}
            {errorMessage && (
              <div className={buildingManagementStyle.CNtableError}>
                <Text content={errorMessage} color="red" />
              </div>
            )}
            <div style={{ width: "100%", overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  tableLayout: "fixed",
                  borderCollapse: "collapse",
                  fontSize: "12px",
                }}
              >
                <thead
                  style={{
                    position: "sticky",
                    top: 0,
                    zIndex: 10,
                    height: "34px",
                  }}
                >
                  <tr>
                    <th
                      style={{
                        width: "40px",
                        textAlign: "center",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                      }}
                    >
                      <div>
                        <input
                          type="checkbox"
                          onChange={handleSelectAllChange}
                          checked={isAllSelected}
                          disabled={
                            isLoading ||
                            currentItems.length === 0 ||
                            new Set(currentItems.map((item) => item.agreement_category)).size > 1
                          }
                        />
                      </div>
                    </th>
                    {headers.map((header, index) => (
                      <th
                        key={header.key}
                        style={{
                          width: `${columnWidths[index]}%`,
                          textAlign: "center",
                          cursor: "pointer",
                        }}
                        aria-sort={
                          sorting.key === header.key
                            ? sorting.direction === "asc"
                              ? "ascending"
                              : "descending"
                            : "none"
                        }
                        onClick={() => handleSort(header.key)}
                      >
                        <Text content={header.label} size="sm" color="gray-dark" weight="bold" />
                        {sorting.key === header.key && sorting.direction === "asc" && (
                          <TriangleUpIcon className="inline-block h-4 w-4 align-middle" />
                        )}
                        {sorting.key === header.key && sorting.direction === "desc" && (
                          <TriangleDownIcon className="inline-block h-4 w-4 align-middle" />
                        )}
                        {index < headers.length - 1 && (
                          <span
                            role="button"
                            tabIndex={0}
                            className={buildingManagementStyle.resizeHandle}
                            onMouseDown={(e) => handleMouseDown(index, e)}
                          />
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {currentItems.length > 0 ? (
                    (() => {
                      const uniqueCurrentItems = Array.from(
                        new Map(
                          currentItems.map((item, i) => {
                            const key = [
                              item.agreement_category,
                              item.building_id,
                              item.location_identifier_name?.trim(),
                              item.industry_class_detail_code,
                              i,
                            ].join("_");
                            return [key, item];
                          })
                        ).values()
                      );
                      return uniqueCurrentItems.map((item, i) => {
                        const rowKey = [
                          item.agreement_category,
                          item.building_id,
                          item.location_identifier_name?.trim(),
                          item.industry_class_detail_code,
                          i,
                        ].join("_");

                        const isSelected = selectedItems.some(
                          (selected) =>
                            selected.agreement_category === item.agreement_category &&
                            selected.building_id === item.building_id &&
                            selected.location_identifier_name === item.location_identifier_name &&
                            selected.industry_class_detail_code === item.industry_class_detail_code
                        );

                        const checkboxDisabled =
                          !!isLoading ||
                          (!!selectionGroup &&
                            !(
                              item.agreement_category === selectionGroup.agreement_category &&
                              (customerData?.corporate_number ?? "") === selectionGroup.corporate_number
                            ));
                        return (
                          <tr key={rowKey} style={{ lineHeight: "1.2", height: "26px" }}>
                            <td className={buildingManagementStyle.checkboxColumn}>
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => handleCheckboxChange(item)}
                                disabled={checkboxDisabled}
                              />
                            </td>
                            {headers.map((header, index) => {
                              const value = item[header.key as keyof BuildingResponseItem];
                              const isGroupField = /^group[1-5]$/.test(header.key);
                              const isAgreementCategory = header.key === "agreement_category";
                              const isBuildingName =
                                header.key === "location_identifier_name" &&
                                item.location_identifier_name &&
                                item.location_identifier_name.trim() !== "";

                              // groupNo を group1 → 1 のように変換
                              const groupNo = isGroupField ? Number(header.key.replace("group", "")) : null;

                              let cellContent = "";
                              let tooltipText = "";

                              if (isGroupField && groupNo) {
                                const label = getGroupLabel(
                                  item.agreement_category,
                                  groupNo,
                                  String(value),
                                  groupSettings
                                );
                                const groupSetting = groupSettings.find(
                                  (setting) =>
                                    setting.agreement_category === item.agreement_category &&
                                    setting.group_id.endsWith(String(groupNo)) &&
                                    setting.corporate_number === corporateNumber
                                );
                                const groupName = groupSetting?.group_name ?? `グループ${groupNo}`;
                                cellContent = label;
                                tooltipText = `${groupName}: ${label}`;
                              } else if (isAgreementCategory) {
                                cellContent = getAgreementCategoryLabel(String(value));
                                tooltipText = cellContent;
                              } else {
                                cellContent = String(value);
                                tooltipText = cellContent;
                              }
                              return (
                                <td
                                  key={`${rowKey}_${header.key}`}
                                  onClick={() => isBuildingName && handleBuildingClick(item)}
                                  title={tooltipText}
                                  // style={{
                                  //   padding: "4px 4px",
                                  //   width: `${columnWidths[index]}%`,
                                  //   wordBreak: "break-word",
                                  //   textAlign: "center",
                                  //   ...(isBuildingName ? { cursor: "pointer", color: "blue" } : {}),
                                  // }}
                                  className={`px-1 py-1 text-center break-words ${isBuildingName ? "cursor-pointer table-link hover:underline" : ""}`}
                                  style={{
                                    width: `${columnWidths[index]}%`,
                                  }}
                                >
                                  {isGroupField && groupNo
                                    ? getGroupLabel(item.agreement_category, groupNo, String(value), groupSettings)
                                    : isAgreementCategory
                                      ? getAgreementCategoryLabel(String(value))
                                      : String(value)}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      });
                    })()
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
          </div>
          <div className="flex flex-col items-center justify-end gap-2 space-x-2 py-4 sm:flex-row">
            <div className="flex w-full items-center justify-between">
              <div className="flex-1 text-sm text-muted-foreground">
                {totalCount} 件中 {startRow}–{endRow} 件
              </div>

              <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-6 lg:gap-8">
                <div className="flex items-center space-x-2">
                  <p className="whitespace-nowrap text-sm font-medium">1ページの行数:</p>
                  <Select
                    value={`${pagination.pageSize}`}
                    onValueChange={(value) =>
                      setPagination({
                        pageIndex: 0,
                        pageSize: Number(value),
                      })
                    }
                  >
                    <SelectTrigger className="h-8 w-[70px]">
                      <SelectValue placeholder={`${pagination.pageSize}`} />
                    </SelectTrigger>
                    <SelectContent side="top">
                      {pageSizeOptions.map((size) => (
                        <SelectItem key={size} value={`${size}`}>
                          {size}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* ページ遷移ボタン */}
            <div className="flex w-full items-center justify-between gap-2 sm:justify-end mt-2">
              <div className="flex w-[100px] items-center justify-center text-sm font-medium">
                {pagination.pageIndex + 1} / {totalPages} ページ
              </div>

              <div className="flex items-center space-x-2">
                {/* 最初のページ */}
                <Button
                  aria-label="Go to first page"
                  variant="outline"
                  className="hidden h-8 w-8 p-0 lg:flex"
                  onClick={() => setPagination((prev) => ({ ...prev, pageIndex: 0 }))}
                  disabled={pagination.pageIndex === 0}
                >
                  <DoubleArrowLeftIcon className="h-4 w-4" />
                </Button>

                {/* 前のページ */}
                <Button
                  aria-label="Go to previous page"
                  variant="outline"
                  className="h-8 w-8 p-0"
                  onClick={() => setPagination((prev) => ({ ...prev, pageIndex: Math.max(0, prev.pageIndex - 1) }))}
                  disabled={pagination.pageIndex === 0}
                >
                  <ChevronLeftIcon className="h-4 w-4" />
                </Button>

                {/* 次のページ */}
                <Button
                  aria-label="Go to next page"
                  variant="outline"
                  className="h-8 w-8 p-0"
                  onClick={() =>
                    setPagination((prev) => ({ ...prev, pageIndex: Math.min(totalPages - 1, prev.pageIndex + 1) }))
                  }
                  disabled={pagination.pageIndex >= totalPages - 1}
                >
                  <ChevronRightIcon className="h-4 w-4" />
                </Button>

                {/* 最後のページ */}
                <Button
                  aria-label="Go to last page"
                  variant="outline"
                  className="hidden h-8 w-8 p-0 lg:flex"
                  onClick={() => setPagination((prev) => ({ ...prev, pageIndex: totalPages - 1 }))}
                  disabled={pagination.pageIndex >= totalPages - 1}
                >
                  <DoubleArrowRightIcon className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      }
      <div className="flex items-end gap-2 mb-4">
        {/* グループ選択 */}
        <div className="w-[200px] mt-4">
          <Text content="グループ設定" size="lg" weight="bold" />
          <div className="text-sm font-medium text-[#667085] mt-4">グループ選択</div>
          <Select
            value={registerGroupId}
            onValueChange={(value) => {
              if (value === "none") {
                setRegisterGroupId("none");
                setRegisterGroupOption(undefined);
                setRegisterSelectableGroupOptionItems([]);
                return;
              }

              setRegisterGroupId(value);
              setRegisterGroupOption("");

              const matchedGroup = adjustedGroupSettings.find(
                (g) =>
                  g.group_id === value &&
                  g.agreement_category === selectionGroup?.agreement_category &&
                  g.corporate_number === selectionGroup?.corporate_number
              );

              if (matchedGroup) {
                const options = Array.from(
                  new Map(
                    matchedGroup.group_options
                      .map((opt) => opt.trim())
                      .filter((opt) => opt !== "")
                      .map((opt) => [opt, { value: opt, label: opt }])
                  ).values()
                );

                setRegisterSelectableGroupOptionItems(options);
              } else {
                setRegisterSelectableGroupOptionItems([]);
              }
            }}
            disabled={!selectionGroup || registerSelectableGroupIdOptions.length === 0}
          >
            <SelectTrigger className="w-full mt-2">
              <SelectValue placeholder="選択してください" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">未選択</SelectItem>

              {Array.from(
                new Map(
                  groupSettings
                    .filter(
                      (g) =>
                        g.agreement_category === selectionGroup?.agreement_category &&
                        g.corporate_number === selectionGroup?.corporate_number
                    )
                    .filter((g) => g.group_id?.trim() && g.group_name?.trim())
                    .map((g) => [g.group_id, g])
                ).values()
              )
                .sort((a, b) => Number(a.group_id) - Number(b.group_id))
                .map((option, index) => (
                  <SelectItem key={`${option.group_id}_${index}`} value={option.group_id}>
                    {option.group_name}(グループ{option.group_id})
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        {/* グループ（選択肢） */}
        <div className="mr-2 w-[200px]">
          <div className="text-sm font-medium text-[#667085]">グループ（選択肢）</div>
          <Select
            value={registerGroupOption}
            onValueChange={(value) => {
              if (value === "none") {
                setRegisterGroupOption("none");
              } else {
                setRegisterGroupOption(value);
              }
            }}
            disabled={!registerGroupId || registerGroupId === "none"}
          >
            <SelectTrigger className="w-full mt-2">
              <SelectValue placeholder="選択してください" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">未選択</SelectItem>

              {registerSelectableGroupOptionItems
                .filter((opt) => opt.value && opt.label)
                .map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        {/* グループ登録ボタン */}
        <div>
          <Button
            variant="primary"
            size="third"
            onClick={() => {
              console.log(Messages.building_list.clicked_button);
              handleUpdateGroupSetting();
            }}
            className="w-[120px]"
            disabled={!registerGroupOption || registerGroupOption === "none"}
          >
            グループ登録
          </Button>
        </div>
      </div>
    </div>
  );
};

export default BuildingList;
