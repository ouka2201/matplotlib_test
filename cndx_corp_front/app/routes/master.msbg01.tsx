// import { MetaFunction } from "@remix-run/node";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  PaginationState,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ZodError } from "zod";
import SectionTitle from "~/components/common/section-title";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import MasterLayout from "~/components/layout/master-layout";
import { useSession } from "~/components/layout/session-provider";
import { columns as tableColumns } from "~/components/screen/master/msbg01/columns";
import { Button } from "~/components/ui/button";
import { Command, CommandList } from "~/components/ui/command";
import { ScrollArea, ScrollBar } from "~/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Messages } from "~/constants/messages/message";
import { useScrollToError } from "~/hooks/useScrollToError";
import { createBuildingGroupListSchema } from "~/lib/validations/msbg";
import { BuildingGroup, Encoding } from "~/types/screen/master/msbg/msbgType";
import { Icon, Text } from "../components/import";
import { toast } from "../components/ui/use-toast";
import { getData, postData } from "../lib/fetch";

const BuildingGroupMaster: React.FC = () => {
  const { session, clearSession } = useSession();
  const [token, setToken] = useState<string | null>(session?.token ?? null);
  const [userId, setUserId] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const location = useLocation();
  const customerData = location.state?.customerData;
  const [agreementCategory, setAgreementCategory] = useState<{ value: string; label: string }[]>([]);
  const [selectedAgreementCategory, setSelectedAgreementCategory] = useState("");
  const [isEditing, setIsEditing] = useState(location.state?.mode === "edit");
  const [buildingGroupInfo, setBuildingGroupInfo] = useState<BuildingGroup[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);
  const navigate = useNavigate();
  const [originalData, setOriginalData] = useState<BuildingGroup[]>([]);
  const [editedData, setEditedData] = useState<Record<number, Partial<BuildingGroup>>>({});
  const [isDataLoading, setIsDataLoading] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const isErrorWithMessage = (error: unknown): error is { message: string } => {
    return (
      typeof error === "object" &&
      error !== null &&
      "message" in error &&
      typeof (error as { message: unknown }).message === "string"
    );
  };

  // パンくず
  const breadcrumbItems = [
    { title: customerData?.company_name ?? "会社名", link: "/master/mscs03", state: { customerData } },
    { title: "拠点マスタ", link: "/master/msbd01", state: { customerData } },
    { title: "拠点グループマスタ", link: "" },
  ];

  // 同意書取得経路データを取得
  const fetchAgreementCategoryMaster = useCallback(async () => {
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
      const masterData = await getMasterDataForCondition(masterEntries, token);
      const consentRouteData = masterData["consent-route"];

      // 複数形式への対応処理
      let rawData = [];

      // ケース1：配列をそのまま返す
      if (Array.isArray(consentRouteData)) {
        rawData = consentRouteData;
      }
      // ケース2：res プロパティを含むオブジェクト
      else if (consentRouteData?.res && Array.isArray(consentRouteData.res)) {
        rawData = consentRouteData.res;
      }
      // ケース3：data プロパティを含むオブジェクト
      else if (consentRouteData?.data && Array.isArray(consentRouteData.data)) {
        rawData = consentRouteData.data;
      }
      //ケース4：その他の形式
      else {
        console.error(Messages.VALIDATION.data.invalid, consentRouteData);
        setErrorMessage(Messages.VALIDATION.data.invalid);
        setAgreementCategory([]);
        return;
      }

      // データ変換
      const transformedData = rawData
        .map((item) => {
          // 複数のプロパティ名に対応
          const value = item.id || item.value || item.code;
          const label = item.name || item.label || item.text;

          if (!value || !label) {
            console.warn(Messages.master.msbg01.invalid_data, item);
            return null;
          }

          return { value, label };
        })
        .filter(Boolean); // 無効な項目を除外

      setAgreementCategory(transformedData);

      // データが空であることへの警告
      if (transformedData.length === 0) {
        setErrorMessage(Messages.VALIDATION.data.none);
      }
    } catch (error) {
      console.error(Messages.VALIDATION.api.fetch_error, error);
      setErrorMessage(Messages.VALIDATION.api.fetch_error);
      setAgreementCategory([]);
    } finally {
      console.log("get");
    }
  }, [token]);

  useEffect(() => {
    const fetchTokenAndUserInfoFromSessionStorage = () => {
      if (typeof window !== "undefined") {
        const sessionData = sessionStorage.getItem("session");

        if (sessionData) {
          const sessionObj = JSON.parse(sessionData);

          // トークン処理
          if (sessionObj?.token) {
            setToken(sessionObj.token);
          } else {
            console.log(Messages.VALIDATION.data.token_none);
            setToken(null);
          }

          // email を user_id として扱う
          if (sessionObj?.email) {
            setUserId(sessionObj.email);
          } else {
            console.log(Messages.VALIDATION.data.session_none);
            setUserId(null);
          }

          if (sessionObj?.authorityInfo.org_id) {
            setOrgId(sessionObj.authorityInfo.org_id);
          } else {
            console.log(Messages.VALIDATION.data.session_none);
            setOrgId(null);
          }
        } else {
          console.log(Messages.VALIDATION.data.session_none);
          setToken(null);
          setUserId(null);
          setOrgId(null);
        }
      }
    };
    fetchTokenAndUserInfoFromSessionStorage();
  }, [location.state]);

  useEffect(() => {
    // コンポーネントロード時に同意書取得パスのデータを取得する
    fetchAgreementCategoryMaster();
  }, [fetchAgreementCategoryMaster]);

  const loadItems = useCallback(
    async (agreementCategoryParam: string) => {
      function isErrorWithStatus(error: unknown): error is { status: number; error_message_list?: string } {
        return (
          typeof error === "object" &&
          error !== null &&
          "status" in error &&
          typeof (error as { status: number }).status === "number"
        );
      }

      if (!token || !customerData?.corporate_number || !agreementCategoryParam) {
        return null;
      }

      setIsDataLoading(true);
      setHasLoadedOnce(true);

      const params = {
        // user_id: userId,
        org_id: orgId,
        corporate_number: customerData?.corporate_number ?? "",
        agreement_category: agreementCategoryParam,
      };

      const query = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, v as ""])).toString();

      const requestUrl = `/api/building/group/master/detail${query ? `?${query}` : ""}`;

      try {
        const data = await getData(requestUrl, {
          Authorization: `Bearer ${token}`,
        });

        if (data && data.result && Array.isArray(data.result.building_group_info)) {
          const buildingGroups: BuildingGroup[] = data.result.building_group_info.filter(
            (group) => group.agreement_category === agreementCategoryParam
          );
          setBuildingGroupInfo(buildingGroups);
          setErrorMessage("");
          return buildingGroups;
        } else {
          setErrorMessage(Messages.VALIDATION.data.invalid);
          console.error(Messages.VALIDATION.data.invalid, data);
          return null;
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

          setErrorMessage(errMsg);
        } else {
          setErrorMessage(Messages.VALIDATION.api.error);
        }

        return null;
      } finally {
        setIsDataLoading(false);
      }
    },
    [token, customerData, orgId, userId, clearSession, navigate]
  );

  const handleAgreementCategoryChange = useCallback(
    async (value: string) => {
      setSelectedAgreementCategory(value);
      setIsEditing(false);
      setEditedData({});

      if (!value) return;

      try {
        const result = await loadItems(value);
        if (result) {
          setOriginalData(result);
        }
      } catch (error) {
        console.error(Messages.VALIDATION.api.load_error, error);
        setErrorMessage(Messages.VALIDATION.api.load_error);
      }
    },
    [loadItems]
  );

  const handleInputChange = (groupNumber: number, key: keyof BuildingGroup, value: string) => {
    setEditedData((prev) => ({
      ...prev,
      [groupNumber]: {
        ...(prev[groupNumber] || {}),
        [key]: value,
      },
    }));
  };

  const handleRegister = async () => {
    function isErrorWithStatus(error: unknown): error is { status: number; data?: any } {
      return (
        typeof error === "object" &&
        error !== null &&
        "status" in error &&
        typeof (error as { status: number }).status === "number"
      );
    }
    if (!selectedAgreementCategory) {
      // toast({
      //   title: "登録エラー",
      //   description: Messages.AGREEMENT_CATEGORY.unselected,
      //   type: "error",
      //   duration: 5000,
      // });
      return;
    }

    const updated = Object.entries(editedData)
      .map(([groupIdSuffix, values]) => {
        const existing = buildingGroupInfo.find((d) => d.group_id.endsWith(groupIdSuffix));

        const base: BuildingGroup = {
          corporate_number: customerData?.corporate_number ?? "",
          agreement_category: selectedAgreementCategory,
          org_id: orgId || "",
          group_id: existing?.group_id || `${groupIdSuffix}`,
          group_name: existing?.group_name ?? "",
          select_item1: existing?.select_item1 ?? "",
          select_item2: existing?.select_item2 ?? "",
          select_item3: existing?.select_item3 ?? "",
          select_item4: existing?.select_item4 ?? "",
          select_item5: existing?.select_item5 ?? "",
          select_item6: existing?.select_item6 ?? "",
          select_item7: existing?.select_item7 ?? "",
        };

        const updatedGroup: BuildingGroup = {
          ...base,
          ...values,
        };

        const hasDiff = Object.keys(values).some((key) => {
          const k = key as keyof BuildingGroup;
          return base[k] !== values[k];
        });

        return hasDiff ? updatedGroup : null;
      })
      .filter((entry): entry is BuildingGroup => entry !== null);

    if (updated.length === 0) {
      toast({
        title: "変更なし",
        description: Messages.master.msbg01.changed_item_none,
        type: "info",
        duration: 3000,
      });
      return;
    }

    const encoding: Encoding = "utf-8";
    const schema = createBuildingGroupListSchema(encoding);
    try {
      schema.parse(updated); // バリデーションチェック

      await postData(
        "/api/building/group/master/update",
        {
          editedGroupData: updated,
          userId: userId,
          agreement_category: selectedAgreementCategory,
        },
        {
          Authorization: `Bearer ${token}`,
        }
      );

      toast({title: "更新完了", duration: 2000,});
      setIsEditing(false);
      setEditedData({});

      // 更新後のデータを再取得
      const items = await loadItems(selectedAgreementCategory);
      if (items) {
        setBuildingGroupInfo(items);
        setOriginalData(items);
      }
      setErrorMessage("");
    } catch (err: unknown) {
      if (err instanceof ZodError) {
        const messageList = err.errors.map((e) => e.message);
        setErrorMessage(messageList);

        // toast({
        //   title: "登録エラー",
        //   description: Messages.VALIDATION_ERROR,
        //   type: "error",
        //   duration: 5000,
        // });
      } else if (isErrorWithStatus(err)) {
        if (err.status === 401) {
          clearSession();
          sessionStorage.removeItem("session");
          return window.location.href = "/session-expired";
        }

        const errMsg =
          (err as any).data?.error_message_list?.[0] ||
          (err as any).data?.message ||
          (err.status === 400
            ? Messages.VALIDATION_ERROR
            : err.status === 500
              ? Messages.SYSTEM_ERROR
              : Messages.UNKNOWN_ERROR);

        setErrorMessage(errMsg);

        // toast({
        //   title: "登録エラー",
        //   description: errMsg,
        //   type: "error",
        //   duration: 5000,
        // });
      } else if (isErrorWithMessage(err)) {
        setErrorMessage(err.message);
        // toast({
        //   title: "登録失敗",
        //   description: err.message || Messages.REGISTER_ERROR,
        //   type: "error",
        //   duration: 5000,
        // });
      } else {
        console.error(Messages.REGISTER_FAILED, err);
        const errorMsg = Messages.REGISTER_FAILED;
        setErrorMessage(errorMsg);

        // toast({
        //   title: "システムエラー",
        //   description: errorMsg,
        //   type: "error",
        //   duration: 5000,
        // });
      }
    }
  };

  //テーブル表示用
  const fullRows = useMemo(() => {
    return [1, 2, 3, 4, 5].map((groupNumber) => {
      const match = buildingGroupInfo.find((d) => d.group_id.endsWith(groupNumber.toString()));

      return {
        ...(match || {}),
        group_id: `group-${groupNumber}`,
      };
    });
  }, [buildingGroupInfo]);

  const columns = tableColumns;
  const data = agreementCategory && selectedAgreementCategory ? fullRows : [];
  const [{ pageIndex, pageSize }, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 5,
  });

  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    pageCount: 1,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    manualPagination: true,
    manualFiltering: true,
    manualSorting: false,
    state: {
      pagination: { pageIndex, pageSize },
      sorting,
    },
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
  });

  return (
    <div className="">
      <MasterLayout
        breadcrumbItems={breadcrumbItems}
        isEditing={isEditing}
        showRegisterButton={isEditing}
        showCancelButton={isEditing}
        processClick={handleRegister}
        onCancelClick={async () => {
          setIsEditing(false);
          setEditedData({});
          const items = await loadItems(selectedAgreementCategory);
          if (items) {
            setBuildingGroupInfo(items);
          }
        }}
      >
        <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />
        {errorMessage && (
          <div className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden mt-5">
            <div className="flex flex-row items-center bg-red-500 px-4 py-2 gap-1">
              <Icon name="error-pink" />
              <Text content="エラーがあります" color="white" weight="bold" />
            </div>
            <div className="flex flex-col items-start bg-[#fee4e2] border border-[#d92d20] px-4 py-6 rounded-b text-[#d92d20] cursor-pointer gap-[25px]">
              {Array.isArray(errorMessage) ? (
                <ul>
                  {errorMessage.map((message, index) => (
                    <li key={index}>{message}</li>
                  ))}
                </ul>
              ) : (
                <div className="text-[#d92d20] text-[14px] font-normal leading-[21px] text-left whitespace-nowrap ">
                  {errorMessage}
                </div>
              )}
            </div>
          </div>
        )}
        <SectionTitle className="space-y-4 mb-10 mt-8">同意書取得経路</SectionTitle>
        <div className="flex items-center gap-4">
          <Select value={selectedAgreementCategory} onValueChange={handleAgreementCategoryChange}>
            <SelectTrigger className="w-1/3" disabled={isEditing}>
              <SelectValue placeholder="同意書取得経路を選択してください" />
            </SelectTrigger>
            <SelectContent className="z-[400] bg-white" side="bottom" sideOffset={4}>
              {agreementCategory.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="primary"
            size="third"
            onClick={() => {
              if (!isEditing) {
                setIsEditing(true);
              }
            }}
            disabled={!selectedAgreementCategory || isEditing}
            className="ml-auto"
          >
            グループ編集
          </Button>
        </div>

        <SectionTitle className="space-y-4 mb-10 mt-8">グループ設定一覧</SectionTitle>
        <Command>
          <CommandList className="p-0 m-0 space-y-0">
            <ScrollArea className="max-h-fit rounded-md border">
              <Table className="w-full">
                <TableHeader className="sticky top-0 z-200 bg-gray-100">
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <TableHead key={header.id} className="text-black" colSpan={header.colSpan}>
                          <div
                            role="button"
                            tabIndex={0}
                            className="flex items-center justify-center bg-gray-100 whitespace-nowrap"
                          >
                            {header.isPlaceholder ? null : (
                              <>{flexRender(header.column.columnDef.header, header.getContext())}</>
                            )}
                          </div>
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>
                <TableBody>
                  {hasLoadedOnce ? (
                    isDataLoading ? (
                      <TableRow>
                        <TableCell colSpan={columns.length} className="h-24 text-center">
                          {selectedAgreementCategory
                            ? "該当するデータがありません"
                            : "同意書取得経路を選択してください"}
                        </TableCell>
                      </TableRow>
                    ) : fullRows.length > 0 ? (
                      fullRows.map((item, index) => {
                        const groupNumber = index + 1;

                        return (
                          <tr key={item.group_id}>
                            {tableColumns.map((column) => {
                              const key =
                                "accessorKey" in column ? column.accessorKey : "id" in column ? column.id : undefined;

                              if (!key || typeof key !== "string") return null;

                              let value = "";
                              if (key === "No") {
                                value = groupNumber.toString();
                              } else if (isEditing) {
                                value =
                                  editedData[groupNumber]?.[key as keyof BuildingGroup] ??
                                  item[key as keyof BuildingGroup] ??
                                  "";
                              } else {
                                value = item[key as keyof BuildingGroup] ?? "";
                              }

                              return (
                                <td
                                  key={`${key}-${item.group_id}`}
                                  className={`p-2 text-center ${column.meta?.className ?? ""}`}
                                >
                                  {isEditing && key !== "No" ? (
                                    <input
                                      className="w-full border rounded px-2 py-1 text-sm overflow-x-auto"
                                      value={value}
                                      title={value}
                                      onChange={(e) =>
                                        handleInputChange(groupNumber, key as keyof BuildingGroup, e.target.value)
                                      }
                                    />
                                  ) : (
                                    value
                                  )}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })
                    ) : (
                      <TableRow>
                        <TableCell colSpan={columns.length} className="h-24 text-center border">
                          {!hasLoadedOnce ? Messages.AGREEMENT_CATEGORY.unselected : Messages.VALIDATION.data.none}
                        </TableCell>
                      </TableRow>
                    )
                  ) : (
                    <TableRow>
                      <TableCell colSpan={columns.length} className="h-24 text-center border">
                        {Messages.AGREEMENT_CATEGORY.unselected}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>
          </CommandList>
        </Command>
        <div className="min-h-[60px]"></div>
      </MasterLayout>
    </div>
  );
};

export default BuildingGroupMaster;
