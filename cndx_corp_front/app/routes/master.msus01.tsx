import React, { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";

import { zodResolver } from "@hookform/resolvers/zod";
import { FieldError, useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import SearchForm from "~/components/common/search-form";
import SectionTitle from "~/components/common/section-title";
import { postMasterUserDataForCondition } from "~/components/layout/master-fetcher";
import MasterLayout from "~/components/layout/master-layout";
import { useSession } from "~/components/layout/session-provider";
import { AlertModal } from "~/components/modal/alert-modal";
import { userInfoColumns, userInfoConfirmColumns } from "~/components/screen/master/msus01/userInfo-columns";
import { Button } from "~/components/ui/button";
import { Command, CommandList } from "~/components/ui/command";
import { Modal } from "~/components/ui/modal";
import { PageableTable } from "~/components/ui/pageable-table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Messages } from "~/constants/messages/message";
import { useLoadingSpinner } from "~/hooks/use-loadingspinner";
import { useScrollToError } from "~/hooks/useScrollToError";
import { postData } from "~/lib/fetch";
import { msusSchema } from "~/lib/validations/msus";
import "~/loader.css";
import { MasterRequest, UserInfoForm, UserInfoList, UserMasterState } from "~/types/screen/master/msus/msusType";
import { Icon, Text } from "../components/import";
import { toast } from "../components/ui/use-toast";

const UserManagement: React.FC = () => {
  // stateを更新するAction
  type UserMasterAction =
    | { type: "SET_LOADING"; payload: boolean }
    | { type: "SET_PERMISSION"; payload: boolean }
    | {
      type: "SET_SEARCH_CONDITION";
      payload: Partial<UserMasterState["searchCondition"]>;
    }
    | { type: "SET_SEARCH_RESULTS"; payload: UserInfoList[] }
    | { type: "SET_SHOW_RESULTS"; payload: boolean };

  // state更新用Reducer
  const userMasterReducer = (state: UserMasterState, action: UserMasterAction): UserMasterState => {
    switch (action.type) {
      case "SET_LOADING":
        return { ...state, isLoading: action.payload };
      case "SET_PERMISSION":
        return { ...state, hasPermission: action.payload };
      case "SET_SEARCH_CONDITION":
        return {
          ...state,
          searchCondition: { ...state.searchCondition, ...action.payload },
        };
      case "SET_SEARCH_RESULTS":
        return { ...state, searchResults: action.payload };
      case "SET_SHOW_RESULTS":
        return { ...state, showResults: action.payload };
      default:
        return state;
    }
  };

  const { withLoading } = useLoadingSpinner();
  const [state, dispatch] = useReducer(userMasterReducer, {
    isLoading: false,
    hasPermission: false,
    searchCondition: {
      company_name: "",
      branch_name: "",
      user_name: "",
      user_status: "",
    },
    searchResults: [],
    showResults: false,
  });

  const { session, clearSession } = useSession();
  const [token, setToken] = useState<string | null>(session?.token ?? null);
  const [loginUserId, setLoginUserId] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>();
  const [role, setRole] = useState<string | null>();
  const [companyOptions, setCompanyOptions] = useState<{ value: string; label: string }[]>([]);
  const [statusOptions, setStatusOptions] = useState<{ value: string; label: string }[]>([]);
  const [userRoleOptions, setUserRoleOptions] = useState<{ value: string; label: string }[]>([]);
  const location = useLocation();
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [logOutOpen, setLogOutOpen] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isEditing, setIsEditing] = useState(location.state?.mode === "edit");
  // 読み込み中フラグ
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRows, setSelectedRows] = useState<Record<string, boolean>>({});
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [statusError, setStatusError] = useState<string>("");
  const [isEpAdmin, setIsEpAdmin] = useState(false);
  const [isBank, setIsBank] = useState(false);
  // 変更確認モーダル用 state
  const [confirmUpdateOpen, setConfirmUpdateOpen] = useState(false);
  const [rowsToConfirm, setRowsToConfirm] = useState<
    {
      user_id: string;
      user_name_before: string;
      user_name_after: string;
      email_before: string;
      email_after: string;
      role_before: string;
      role_after: string;
      status_before: string;
      status_after: string;
    }[]
  >([]);

  const form = useForm<UserInfoForm>({
    defaultValues: {
      rows: state.searchResults.map((r) => ({
        ...r,
        user_role: r.user_role ?? "",
        user_status: r.user_status ?? "",
        email_address: r.email_address ?? "",
        user_name: r.user_name ?? "",
        company_name: r.company_name ?? "",
        branch_name: r.branch_name ?? "",
        start_date: r.start_date ?? "",
        end_date: r.end_date ?? "",
        last_login_datetime: r.last_login_datetime ?? "",
      })),
    },
    resolver: zodResolver(msusSchema),
  });

  const { control, reset } = form;

  const [changedCount, setChangedCount] = useState(0);

  // rows の変更をチェックして changedCount を更新
  const updateChangedCount = useCallback(() => {
    const rows = form.getValues("rows") || [];
    const count = rows.reduce((acc, row, i) => {
      const original = state.searchResults[i];
      if (!original) return acc;

      if (!selectedRows[row.user_id]) return acc;

      const keys: Array<keyof UserInfoList> = ["user_name", "email_address", "user_role", "user_status"];
      return keys.some((k) => row[k] !== original[k]) ? acc + 1 : acc;
    }, 0);

    setChangedCount(count);
  }, [form, selectedRows, state.searchResults]);

  const isDirty = form.formState.isDirty;

  useEffect(() => {
    if (!isDirty) return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = ""; // Chrome用
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  useEffect(() => {
    updateChangedCount();
  }, [selectedRows, state.searchResults]);

  useEffect(() => {
    const userRoleFlags = JSON.parse(sessionStorage.getItem("userRoleFlags") || "{}");
    setIsEpAdmin(userRoleFlags.isEpAdmin ?? false);
    setIsBank(userRoleFlags.isBank ?? false);
  }, []);

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

          if (sessionObj?.email) {
            setLoginUserId(sessionObj.email);
          } else {
            console.log(Messages.VALIDATION.data.session_none);
            setLoginUserId(null);
          }

          if (sessionObj?.authorityInfo.org_id) {
            setOrgId(sessionObj.authorityInfo.org_id);
          } else {
            console.log(Messages.VALIDATION.data.session_none);
            setOrgId(null);
          }

          if (sessionObj?.authorityInfo.role) {
            setRole(sessionObj.authorityInfo.role);
          } else {
            console.log(Messages.VALIDATION.data.session_none);
            setRole(null);
          }
        } else {
          console.log(Messages.VALIDATION.data.session_none);
          setToken(null);
          setLoginUserId(null);
          setOrgId(null);
          setRole(null);
        }
      }
    };
    fetchTokenAndUserInfoFromSessionStorage();
  }, [location.state]);

  const didInit = useRef(false);

  useEffect(() => {
    let isCancelled = false;

    const fetchMaster = async () => {
      if (!token) return;

      const masterEntries: MasterRequest[] = [
        { name: "company_name", params: {} },
        { name: "user_status", params: {} },
        { name: "user_role", params: {} },
      ];

      try {
        const data = await postMasterUserDataForCondition(masterEntries, token);

        if (!isCancelled) {
          setCompanyOptions(
            (data["company_name"]?.result ?? [])
              .slice() // 念のため元配列を壊さない
              .sort((a: any, b: any) =>
                a.company_name.localeCompare(b.company_name)
              )
              .map((item: any) => ({
                value: JSON.stringify({
                  bank_code: item.bank_code,
                  branch_code: item.branch_code,
                  company_code: item.company_code,
                }),
                label: item.company_name,
              }))
          );
          setStatusOptions(
            (data["user_status"]?.result ?? []).map((item: any) => ({
              value: item.code,
              label: item.jp_code_name,
            })),
          );
          setUserRoleOptions(
            (data["user_role"]?.result ?? []).map((item: any) => ({
              value: item.code,
              label: item.jp_code_name,
            })),
          );
          if (!didInit.current) {
            form.reset({
              rows: state.searchResults.map((r) => ({
                ...r,
                user_role: r.user_role ?? "",
                user_status: r.user_status ?? "",
                email_address: r.email_address ?? "",
                user_name: r.user_name ?? "",
                company_name: r.company_name ?? "",
                branch_name: r.branch_name ?? "",
                start_date: r.start_date ?? "",
                end_date: r.end_date ?? "",
                last_login_datetime: r.last_login_datetime ?? "",
              })),
            });

            didInit.current = true;
          }
        }
      } catch (err) {
        if (!isCancelled) {
          console.error(err);
        }
      }
    };

    fetchMaster();

    return () => {
      isCancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!isEditing) return;

    // 🔹 searchResults が空なら reset しない（空上書きを防止）
    if (!state.searchResults || state.searchResults.length === 0) return;

    // 🔹 初回ロードの reset が完了してからだけ実行
    if (!didInit.current) return;

    form.reset({ rows: state.searchResults });
  }, [isEditing, state.searchResults]);

  // 検索Form必要情報
  const searchFields = [
    {
      id: "company_name",
      label: "企業名",
      type: "select",
      options: companyOptions,
      placeholder: "企業を選択",
    },
    {
      id: "branch_name",
      label: "支店名",
      type: "text",
      placeholder: "xx支店",
    },
    {
      id: "user_name",
      label: "氏名",
      type: "text",
      placeholder: "東電 太郎",
    },
    {
      id: "user_status",
      label: "ステータス",
      type: "select",
      options: statusOptions,
      placeholder: "ステータスを選択",
    },
  ];

  // 検索条件更新
  const updateSearchCondition = (updates: Partial<typeof state.searchCondition>) => {
    dispatch({
      type: "SET_SEARCH_CONDITION",
      payload: { ...updates },
    });
  };

  // 検索処理イベント
  const handleSearch = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setErrorMessage("");
    dispatch({ type: "SET_LOADING", payload: true });

    function isErrorWithStatus(error: unknown): error is { status: number; error_message_list?: string } {
      return (
        typeof error === "object" &&
        error !== null &&
        "status" in error &&
        typeof (error as { status: number }).status === "number"
      );
    }

    try {
      const url = `/api/mst_user/search/info`;

      const data = await withLoading(() => postData(url, state.searchCondition, { Authorization: `Bearer ${token}` }));
      dispatch({ type: "SET_SEARCH_RESULTS", payload: data });

      if (isEditing) {
        form.reset({
          rows: data.map((r: any) => ({
            ...r,
            user_role: r.user_role ?? "",
            user_status: r.user_status ?? "",
            email_address: r.email_address ?? "",
            user_name: r.user_name ?? "",
            company_name: r.company_name ?? "",
            branch_name: r.branch_name ?? "",
            start_date: r.start_date ?? "",
            end_date: r.end_date ?? "",
            last_login_datetime: r.last_login_datetime ?? "",
          })),
        });

        // チェックボックスも初期化したいなら
        setSelectedRows({});
      }
    } catch (error: unknown) {
      console.error(Messages.VALIDATION.api.error);

      if (isErrorWithStatus(error)) {
        if (error.status === 401) {
          clearSession();
          sessionStorage.removeItem("session");
          return window.location.href = "/session-expired";
        }

        switch (error.status) {
          case 400:
            setErrorMessage(
              (error as any).data?.error_message_list?.[0] || (error as any).data?.message || Messages.VALIDATION_ERROR,
            );
            break;

          case 500:
            setErrorMessage(Messages.SYSTEM_ERROR);
            break;

          default:
            setErrorMessage((error as any).data?.message || Messages.UNKNOWN_ERROR);
            break;
        }
      } else {
        setErrorMessage(Messages.VALIDATION.api.error);
      }
    } finally {
      setIsLoading(false);
      dispatch({ type: "SET_LOADING", payload: false });
    }
  }, [state.searchCondition, withLoading]);

  // 初期表示時検索実行
  useEffect(() => {
    if (role && loginUserId && orgId) {
      handleSearch();
    }
  }, [role, loginUserId, orgId]);

  // 検索条件リセット実行
  const handleReset = () => {
    setIsResetting(true);
    if (isEditing) {
      setSelectedRows({});
    }
    updateSearchCondition({
      company_name: "",
      branch_name: "",
      user_name: "",
      user_status: "",
    });
  };

  useEffect(() => {
    if (isResetting) {
      handleSearch();
      setIsResetting(false);
    }
  }, [state.searchCondition, isResetting]);

  // パンくず
  const handleBreadcrumbClick = () => {
    setIsEditing(false); // 編集状態を解除
    window.scrollTo(0, 0); // 画面トップに戻す場合
  };

  const breadcrumbItems = isEditing
    ? [
      {
        title: "ユーザー登録・管理",
        link: "/master/msus01",
        onClick: handleBreadcrumbClick,
      },
      { title: "編集", link: "" },
    ]
    : [{ title: "ユーザー登録・管理", link: "" }];

  //強制ログアウトAPI
  const handleLogOut = async () => {
    if (!token) return;

    // 選択されたユーザーのみ抽出
    const rowsToLogOut = Object.entries(selectedRows)
      .filter(([userId, isSelected]) => isSelected && userId !== loginUserId)
      .map(([userId]) => {
        const row = state.searchResults.find((r) => r.user_id === userId);
        if (!row || !row.user_id || !row.org_id) return null;
        return { user_id: row.user_id, org_id: row.org_id };
      })
      .filter((r): r is { user_id: string; org_id: string } => r !== null);

    if (rowsToLogOut.length === 0) {
      setErrorMessage(Messages.master.msus01.logout_target_not_selected);
      return;
    }

    try {
      const res = await postData(
        "/api/mst_user/search/logout",
        { users: rowsToLogOut },
        { Authorization: `Bearer ${token}` },
      );

      toast({
        title: "強制ログアウト完了",
        description: `${rowsToLogOut.length} 件のユーザーをログアウトしました。`,
        type: "success",
        duration: 3000,
      });

      setLogOutOpen(false);
      // チェックボックスリセット
      setSelectedRows({});

      handleSearch();
    } catch (err: unknown) {
      console.error(err);
      // if (isErrorWithStatus(err)) {
      //   setErrorMessage(err.data?.message || `ステータスコード: ${err.status}`);
      // } else {
      //   setErrorMessage("強制ログアウト中にエラーが発生しました");
      // }
      setErrorMessage(Messages.master.msus01.force_logout_failed);
      setLogOutOpen(false);
    }
  };

  //ステータス一括選択のセレクトボックス権限制御
  const filteredStatusOptions = useMemo(() => {
    return statusOptions.filter((item) => {
      if (isEpAdmin) {
        return ["2", "1", "3", "0", "5"].includes(item.value);
      }
      if (isBank) {
        return ["2", "3", "5"].includes(item.value);
      }
      return false;
    });
  }, [statusOptions, isEpAdmin, isBank]);

  useEffect(() => {
    const messagesSet = new Set<string>();

    const rowsErrors = form.formState.errors.rows;
    if (rowsErrors && Array.isArray(rowsErrors)) {
      rowsErrors.forEach((rowError) => {
        if (!rowError) return;
        Object.values(rowError).forEach((err) => {
          const fieldErr = err as FieldError | undefined;
          if (fieldErr?.message && typeof fieldErr.message === "string") {
            messagesSet.add(fieldErr.message);
          }
        });
      });
    }

    const messages = Array.from(messagesSet);
    setErrorMessage(messages.length > 0 ? messages : "");
  }, [form.formState.errors]);

  //更新API
  const handleUpdate = async () => {
    if (!token) return;

    const valid = await form.trigger();
    if (!valid) {
      // toast({
      //   title: "入力エラー",
      //   description: "入力内容を確認してください",
      //   type: "error",
      //   duration: 3000,
      // });
      return;
    }

    const rows = form.getValues("rows");

    // 選択されていて、かつ変更がある行のみ抽出
    const updatedRows = Object.entries(selectedRows)
      .filter(([userId, isSelected]) => isSelected && userId !== loginUserId)
      .map(([userId]) => {
        const row = rows.find((r) => r.user_id === userId);
        const originalRow = state.searchResults.find((r) => r.user_id === userId);
        if (!row || !originalRow) return null;

        // user_id と org_id は必須
        if (!row.user_id || !row.org_id) return null;

        const hasDiff =
          row.user_name !== originalRow.user_name ||
          row.email_address !== originalRow.email_address ||
          row.user_role !== originalRow.user_role ||
          row.user_status !== originalRow.user_status;

        if (!hasDiff) return null;

        return {
          user_id: row.user_id,
          user_name_before: originalRow.user_name,
          user_name_after: row.user_name,
          email_before: originalRow.email_address,
          email_after: row.email_address,
          role_before: originalRow.user_role,
          role_after: row.user_role,
          status_before: originalRow.user_status,
          status_after: row.user_status,
        };
      })
      .filter((r): r is NonNullable<typeof r> => r !== null);

    if (updatedRows.length === 0) {
      // toast({
      //   title: "変更なし",
      //   description: Messages.master.msus01.no_update_target_rows,
      //   type: "info",
      //   duration: 3000,
      // });
      return;
    }

    setRowsToConfirm(updatedRows);
    setConfirmUpdateOpen(true);
  };

  const handleDownloadCsv = async () => {
    try {
      if (!token) return;

      // CSVダウンロード
      const blob = await postData(
        "/api/mst_user/csv/download",
        {}, // ← body は空でOK
        {
          Accept: "text/csv",
          Authorization: `Bearer ${token}`,
        },
      );

      if (!(blob instanceof Blob)) {
        setErrorMessage(Messages.master.msus01.csv_download_failed);
        return;
      }

      // ファイル名生成
      const now = new Date();
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, "0");
      const dd = String(now.getDate()).padStart(2, "0");
      const hh = String(now.getHours()).padStart(2, "0");
      const mi = String(now.getMinutes()).padStart(2, "0");

      const fileName = `m_user_${yyyy}${mm}${dd}_${hh}${mi}.csv`;

      // ダウンロード処理
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      a.click();
      window.URL.revokeObjectURL(url);
      toast({
        title: "ダウンロード成功",
        // description: Messages.help.dounload_success,
        type: "success",
        duration: 3000,
      });
    } catch (e) {
      console.error(e);
      setErrorMessage(Messages.master.msus01.csv_download_error);
    }
  };

  const tableRows = isEditing ? form.getValues("rows") : state.searchResults;

  const cleanedRows = useMemo(() => {
    if (!tableRows || tableRows.length === 0) return [];
    return tableRows.filter((row) => Object.values(row ?? {}).some((v) => v !== undefined && v !== ""));
  }, [tableRows]);

  const visibleRows = useMemo(() => cleanedRows, [cleanedRows]);

  const allChecked = useMemo(() => {
    if (!isEditing) {
      const selectable = visibleRows.filter((row) => row.user_status === "0" && row.user_id !== loginUserId);
      return selectable.length > 0 && selectable.every((row) => Boolean(selectedRows[row.user_id]));
    }

    // 編集モード
    return visibleRows.filter((row) => row.user_id !== loginUserId).every((row) => Boolean(selectedRows[row.user_id]));
  }, [visibleRows, selectedRows, isEditing, loginUserId]);

  const columns = useMemo(() => {
    return userInfoColumns(
      selectedRows,
      setSelectedRows,
      statusOptions,
      userRoleOptions,
      isEditing,
      control,
      loginUserId,
      isBank,
      filteredStatusOptions,
      updateChangedCount,
      visibleRows,
      allChecked,
    );
  }, [
    selectedRows,
    statusOptions,
    userRoleOptions,
    isEditing,
    control,
    loginUserId,
    isBank,
    filteredStatusOptions,
    updateChangedCount,
    allChecked, // ヘッダの見た目に関わる
    visibleRows, // テーブル表示対象
  ]);

  return (
    <MasterLayout
      breadcrumbItems={breadcrumbItems}
      isEditing={isEditing}
      showUpdateButton={true}
      updateButtonText={`更新（${changedCount}ユーザー）`}
      updateButtonDisabled={!Object.values(selectedRows).some(Boolean)}
      showCancelButton={true}
      onUpdateClick={handleUpdate}
      onCancelClick={async () => {
        setIsEditing(false);
        setErrorMessage("");
        setSelectedRows({});
      }}
    >
      {/* <div className='p-3'> */}
      <div className="space-y-4 mb-10">
        {errorMessage && (
          <div
            ref={errorTopRef as React.RefObject<HTMLDivElement>}
            className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden scroll-mt-[300px]"
          >
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
                <div className="text-[#d92d20] text-[14px] font-normal leading-[21px] text-left whitespace-nowrap">
                  {errorMessage}
                </div>
              )}
            </div>
          </div>
        )}
        {/* ▼検索条件 */}
        <div className="space-y-4">
          <div className="flex justify-end">
            {!isEditing && (
              <div className="flex gap-2">
                <Button variant="primary" size="default" onClick={() => navigate("/master/msus02")}>
                  {/* <PlusIcon className="h-5 w-5" /> */}
                  新規登録
                </Button>

                <Button
                  variant="primary"
                  size="default"
                  onClick={() => {
                    if (setIsEditing) setIsEditing(true);
                    setSelectedRows({});
                  }}
                >
                  編集
                </Button>
              </div>
            )}
          </div>

          <SearchForm
            fields={searchFields}
            values={state.searchCondition}
            onValueChange={updateSearchCondition}
            onSearch={handleSearch}
            onReset={handleReset}
          />
        </div>
      </div>

      {/* ▼確認・編集対象企業の選択 */}
      <Command>
        {isLoading ? (
          // ローディング中
          <div className="p-4 flex justify-center items-center text-gray-500 text-sm">
            <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin mr-2"></div>
            読み込み中...
          </div>
        ) : (
          <>
            <SectionTitle>
              <div className="flex justify-end w-full items-center">
                <div className="flex gap-2">
                  {isEditing && (
                    <Button
                      variant="primary"
                      size="default"
                      disabled={!Object.values(selectedRows).some(Boolean)}
                      onClick={() => setOpen(true)}
                    >
                      ステータス一括変更
                    </Button>
                  )}
                  {!isEditing && (
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={handleDownloadCsv}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          handleDownloadCsv();
                        }
                      }}
                      className="textlink_button"
                    >
                      全ユーザー情報一覧ダウンロード(CSV)
                    </div>
                  )}
                </div>
              </div>
            </SectionTitle>

            <CommandList>
              <PageableTable
                columns={columns}
                data={visibleRows}
                totalCount={visibleRows.length}
                pageCount={Math.ceil(visibleRows.length / 50)}
                initialPageSize={50}
                rowKeyResolver={(row) => row.user_id ?? crypto.randomUUID()}
                onPageChange={() => {
                  if (isEditing) {
                    setSelectedRows({});
                  }
                }}
              />
            </CommandList>
          </>
        )}
        {!isEditing && !isBank && (
          <Button
            variant="error"
            size="default"
            onClick={() => setLogOutOpen(true)}
            disabled={!Object.values(selectedRows).some((v) => v)}
          >
            強制ログアウト
          </Button>
        )}
      </Command>

      <div className="z-201 mt-2">
        <Modal
          title={<h1 className="-mb-10">ステータス一括変更</h1>}
          description=""
          isOpen={open}
          onClose={() => {
            setOpen(false);
            setStatusError("");
          }}
          className="w-[400px] h-[210px]"
        >
          <div className="mb-4">変更後のステータス</div>
          <div className="mb-6">
            <Select
              value={selectedStatus}
              onValueChange={(value) => {
                setSelectedStatus(value);
                setStatusError(""); // 選択されたらエラー消す
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="選択してください" />
              </SelectTrigger>
              <SelectContent className="z-[400] bg-white" side="bottom" sideOffset={4}>
                {filteredStatusOptions.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {statusError && <p className="text-red-500 text-sm mt-1">{statusError}</p>}
          </div>
          <div className="flex w-full items-center justify-end">
            <Button
              variant="second"
              size="second"
              onClick={async () => {
                if (!selectedStatus) {
                  setStatusError(Messages.master.msus01.user_status_unsekected);
                  return;
                }
                const rows = form.getValues("rows");
                const newRows = rows.map((row) => {
                  const isSelected = selectedRows[row.user_id];
                  if (isSelected && row.user_id !== loginUserId) {
                    return {
                      ...row,
                      user_status: selectedStatus,
                    };
                  }

                  return row;
                });
                form.setValue("rows", newRows, {
                  shouldDirty: true,
                  shouldTouch: true,
                  shouldValidate: false,
                });
                await form.trigger("rows");
                updateChangedCount();
                setOpen(false);
              }}
            >
              変更
            </Button>
          </div>
        </Modal>
      </div>
      <div>
        <AlertModal
          isOpen={logOutOpen}
          onClose={() => setLogOutOpen(false)}
          onConfirm={() => handleLogOut()}
          loading={false}
          title="強制ログアウトの確認"
          description={`選択した${Object.values(selectedRows).filter(Boolean).length
            }ユーザーを強制ログアウトさせます。よろしいですか?`}
          cancelText="いいえ"
          continueText="はい"
        />
      </div>
      <div>
        <Modal
          title="ユーザー情報更新内容の確認"
          description={`選択した${changedCount}ユーザーの情報を以下のとおり更新します。よろしいですか？`}
          isOpen={confirmUpdateOpen}
          onClose={() => setConfirmUpdateOpen(false)}
          className="w-[700px] h-[500px]"
        >
          <div className="overflow-auto max-h-[350px]">
            <PageableTable
              columns={userInfoConfirmColumns(userRoleOptions, statusOptions)}
              data={rowsToConfirm}
              totalCount={rowsToConfirm.length}
              pageCount={Math.ceil(rowsToConfirm.length / 50)}
              initialPageSize={10}
              rowKeyResolver={(row) => row.user_id}
            />
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <Button variant="third" onClick={() => setConfirmUpdateOpen(false)}>
              キャンセル
            </Button>
            <Button
              variant="primary"
              size="default"
              onClick={async () => {
                try {
                  const res = await postData(
                    "/api/mst_user/upd",
                    {
                      users: rowsToConfirm.map((r) => ({
                        user_id: r.user_id,
                        org_id: state.searchResults.find((o) => o.user_id === r.user_id)!.org_id,
                        user_name: r.user_name_after,
                        email_address: r.email_after,
                        user_role: r.role_after,
                        user_status: r.status_after,
                      })),
                    },
                    { Authorization: `Bearer ${token}` },
                  );

                  if (res?.status === "error" || (typeof res?.status === "number" && res.status >= 400)) {
                    throw res;
                  }

                  toast({
                    title: "更新完了",
                    // description: `${rowsToConfirm.length}件のユーザー情報を更新しました。`,
                    // type: "success",
                    duration: 3000,
                  });

                  setSelectedRows({});
                  handleSearch();
                } catch (err: any) {
                  console.error(err);

                  if (err?.status === 401) {
                    setErrorMessage(Messages.master.msus01.session_expired);
                  } else {
                    setErrorMessage(err?.data?.message || err?.message || Messages.master.msus01.user_update_failed);
                  }
                } finally {
                  setConfirmUpdateOpen(false);
                }
              }}
            >
              更新
            </Button>
          </div>
        </Modal>
      </div>
    </MasterLayout>
  );
};

export default UserManagement;
