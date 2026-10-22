import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { LoadingSpinner } from "~/components/common/loadingSpinner";
import MasterFormField from "~/components/common/master-form-field";
import { Icon, Text } from "~/components/import";
import { postMasterUserDataForCondition } from "~/components/layout/master-fetcher";
import MasterLayout from "~/components/layout/master-layout";
import SearchDepartment from "~/components/screen/master/msus02/SearchDepartment";
import { Accordion, AccordionContent, AccordionItem } from "~/components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger
} from "~/components/ui/dialog";
import { Form } from "~/components/ui/form";
import { useToast } from "~/components/ui/use-toast";
import { Messages } from "~/constants/messages/message";
import { useScrollToError } from "~/hooks/useScrollToError";
import { postData } from "~/lib/fetch";

/* ----------------------------------------------------
 * 1. Zod Schema（画面用）
 * -------------------------------------------------- */
const userSchema = z
  .object({
    org_id: z.string().min(1, Messages.validation.required("企業名")),
    company_name: z.string().min(1, Messages.validation.required("企業名")),

    branch_code: z.string().optional(),
    branch_name: z.string().optional(),

    user_name: z
      .string()
      .min(1, Messages.validation.required("氏名"))
      .max(50, Messages.validation.maxLength("氏名", 50)),

    email_address: z
      .string()
      .min(1, Messages.validation.required("メールアドレス"))
      .max(100, Messages.validation.maxLength("メールアドレス", 100))
      .email(Messages.validation.invalidField()),

    user_role: z.string().min(1, Messages.validation.required("権限")),
  })
  .refine(
    (data) => {
      // 銀行(BNK)系企業以外 → OK
      if (!data.org_id.startsWith("BNK")) return true;

      // 銀行の時だけ支店必須
      return data.branch_code !== "" && data.branch_name !== "";
    },
    {
      message: Messages.validation.required("支店名"),
      path: ["branch_code"], // エラーメッセージ表示位置
    },
  );

type UserInputs = z.infer<typeof userSchema>;

/* ----------------------------------------------------
 * 2. 登録用データ（API送信用）
 * -------------------------------------------------- */
type UserInfo = UserInputs;

/* ----------------------------------------------------
 * 3. パンくず
 * -------------------------------------------------- */
const breadcrumbItems = [
  { title: "ユーザー登録・管理", link: "/master/msus01" },
  { title: "新規登録", link: "" },
];

/* ----------------------------------------------------
 * 4. メインコンポーネント
 * -------------------------------------------------- */
export default function UserBasicRegist() {
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);
  const [branchList, setBranchList] = useState<{ id: string; name: string; orgTypeCode: string }[]>([]);
  const [companyOptions, setCompanyOptions] = useState<{ id: string; name: string; orgTypeCode: string }[]>([]);
  const [roleOptions, setRoleOptions] = useState<{ id: string; name: string }[]>([]);
  const [allRoleOptions, setAllRoleOptions] = useState<{ id: string; name: string }[]>([]);

  const [showDeptModal, setShowDeptModal] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [companyOrgTypeCode, setCompanyOrgTypeCode] = useState<string | null>(null);
  const [branchOrgTypeCode, setBranchOrgTypeCode] = useState<string | null>(null);

  const formDataRef = useRef<UserInfo | null>(null);
  const navigate = useNavigate();
  const { saveSuccessToast } = useToast();

  const form = useForm<UserInputs>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      org_id: "",
      company_name: "",
      branch_code: "",
      branch_name: "",
      user_name: "",
      email_address: "",
      user_role: "",
    },
  });

  // トークン取得処理（セッションストレージから取得）
  useEffect(() => {
    const sessionData = sessionStorage.getItem("session");
    if (!sessionData) return;

    try {
      const session = JSON.parse(sessionData);
      setToken(session.token);
    } catch (e) {
      console.error("Error parsing session data:", e);
    }
  }, []);

  /* ----------------------------------------------------
   * 初期：企業、権限取得
   * -------------------------------------------------- */
  useEffect(() => {
    if (!token) return;

    let isCancelled = false;

    const loadMaster = async () => {
      try {
        const data = await postMasterUserDataForCondition(
          [
            { name: "company_name", params: {} },
            { name: "user_role", params: {} },
          ],
          token,
        );

        if (isCancelled) return;

        setCompanyOptions(
          (data["company_name"]?.result ?? [])
            .slice() // 元配列を壊さない
            .sort((a: any, b: any) =>
              a.company_name.localeCompare(b.company_name)
            )
            .map((item: any) => ({
              id: item.org_id,
              name: item.company_name,
              orgTypeCode: item.org_type_code,
            }))
        );

        const roles = (data["user_role"]?.result ?? []).map((item: any) => ({
          id: item.code,
          name: item.jp_code_name,
        }));

        setAllRoleOptions(roles);
        setRoleOptions(roles);
      } catch (err) {
        console.error("マスタ取得エラー:", err);
      }
    };

    loadMaster();
    return () => {
      isCancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!companyOrgTypeCode || allRoleOptions.length === 0) return;

    // 06 / 07 → 管理者のみ
    if (companyOrgTypeCode === "06" || companyOrgTypeCode === "07") {
      setRoleOptions(allRoleOptions.filter((r) => r.id === "0"));
      form.setValue("user_role", "0");
      return;
    }

    // 02 → 支店選択前は全権限（0,1,9）を表示
    if (companyOrgTypeCode === "02") {
      // まだ支店を選んでない場合
      if (!branchOrgTypeCode) {
        setRoleOptions(allRoleOptions.filter((r) => r.id === "0" || r.id === "1" || r.id === "9"));
        // user_role はユーザーに選ばせるので、ここでは変更しない（勝手に9にしない）
        return;
      }

      // 支店が本店（02）なら 9 のみ
      if (branchOrgTypeCode === "02") {
        setRoleOptions(allRoleOptions.filter((r) => r.id === "9"));
        form.setValue("user_role", "9");
        return;
      }

      // 支店が本店以外 → 0,1 のみ
      setRoleOptions(allRoleOptions.filter((r) => r.id === "0" || r.id === "1"));

      // すでに 9 が選ばれていたら不正なのでクリア
      if (form.getValues("user_role") === "9") {
        form.setValue("user_role", "");
      }
      return;
    }

    // その他企業 → 0,1
    setRoleOptions(allRoleOptions.filter((r) => r.id === "0" || r.id === "1"));
  }, [companyOrgTypeCode, branchOrgTypeCode, allRoleOptions]);

  /* ----------------------------------------------------
   * 支店名取得 API
   * -------------------------------------------------- */
  const fetchDepartments = async (orgId: string, branchName: string = "") => {
    if (!token) return;

    try {
      const body = {
        org_id: orgId,
        branch_name: branchName,
      };

      const res = await postData("/api/mst_user/search/branch_name", body, {
        Authorization: `Bearer ${token}`,
      });

      setBranchList(
        res.result?.map((item: any) => ({
          id: item.branch_code,
          name: item.branch_name,
          orgTypeCode: item.org_type_code,
        })) ?? [],
      );
    } catch (err: any) {
      setErrorMessage(err.data?.message);
    }
  };

  /* ----------------------------------------------------
   * 企業選択時の処理（支店情報をクリアして再取得）
   * -------------------------------------------------- */
  const handleCompanyChange = (orgId: string) => {
    form.setValue("org_id", orgId);

    const company = companyOptions.find((c) => c.id === orgId);

    form.setValue("company_name", company?.name ?? "");
    setCompanyOrgTypeCode(company?.orgTypeCode ?? null);

    // クリア
    form.setValue("branch_code", "");
    form.setValue("branch_name", "");
    setBranchOrgTypeCode(null);
    form.clearErrors(["branch_code", "branch_name"]);

    setRoleOptions(allRoleOptions);
    form.setValue("user_role", "");

    // 銀行系企業(BNK〜)のみ支店取得
    if (orgId.startsWith("BNK")) {
      fetchDepartments(orgId);
    }
  };

  /* ----------------------------------------------------
   * 登録 API
   * -------------------------------------------------- */
  const mutation = useMutation({
    mutationFn: (data: UserInfo) => {
      return postData("/api/mst_user/insert", data, {
        Authorization: `Bearer ${token}`,
      });
    },
    onSuccess: () => {
      saveSuccessToast();

      navigate("/master/msus01", {
        state: { userData: formDataRef.current, mode: "new" },
      });
    },
    onError: (error: any) => {
      setErrorMessage(error.data?.message);
      setIsLoading(false);
    },
  });

  /* ----------------------------------------------------
   * 登録実行
   * -------------------------------------------------- */
  const submitData = (data: UserInputs) => {
    const request = {
      org_id: data.org_id,
      company_name: data.company_name,

      branch_code: data.branch_code,
      branch_name: data.branch_name,

      user_name: data.user_name,
      email_address: data.email_address,

      user_role: data.user_role,
    };

    formDataRef.current = request;

    setIsLoading(true);
    mutation.mutate(request);
  };

  const isBranchButtonActive = (companyId?: string) => {
    return !!companyId && companyId.startsWith("BNK");
  };

  /* ----------------------------------------------------
   * JSX
   * -------------------------------------------------- */
  return (
    <MasterLayout
      breadcrumbItems={breadcrumbItems}
      showRegisterButton={true}
      showCancelButton={true}
      processClick={() => form.handleSubmit(submitData)()}
      onCancelClick={() => navigate("/master/msus01")}
      footerType="default"
    >
      {/* ---------- エラー表示 ---------- */}
      <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />
      {errorMessage && (
        <div
          ref={errorTopRef as React.RefObject<HTMLDivElement>}
          className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden mt-5 ml-4 scroll-mt-[300px]"
        >
          <div className="flex items-center bg-red-500 px-4 py-2 gap-1">
            <Icon name="error-pink" />
            <Text content="エラーがあります" color="white" weight="bold" />
          </div>

          <div className="bg-[#fee4e2] border border-[#d92d20] px-4 py-6 text-[#d92d20] gap-6 flex flex-col">
            {Array.isArray(errorMessage) ? (
              <ul>
                {errorMessage.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            ) : (
              <div className="text-[14px]">{errorMessage}</div>
            )}
          </div>
        </div>
      )}

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <Form {...form}>
          <div className="pb-24">
            <form className="grid gap-4">
              <Accordion type="multiple" defaultValue={["item-1"]} className="pl-3">
                <AccordionItem value="item-1">
                  <AccordionContent>
                    <Card>
                      <CardHeader>
                        <CardTitle>ユーザー情報</CardTitle>
                      </CardHeader>

                      <CardContent className="flex flex-col gap-6">
                        {/* 企業名 */}
                        <MasterFormField
                          control={form.control}
                          name="org_id"
                          label="企業名"
                          required
                          options={companyOptions}
                          onValueChange={handleCompanyChange}
                          className="w-1/3"
                        />
                        {/* 支店名 */}
                        <MasterFormField
                          control={form.control}
                          name="branch_code"
                          label="支店名"
                          required={isBranchButtonActive(form.watch("org_id"))}
                          className="w-1/3"
                          renderCustom={() => {
                            const isActive = isBranchButtonActive(form.watch("org_id"));

                            return (
                              <div className="flex items-center gap-3 w-full">
                                {/* 表示用テキスト */}
                                <input
                                  id="departmentName"
                                  type="text"
                                  readOnly
                                  value={form.watch("branch_name")}
                                  placeholder="選択してください"
                                  className="border rounded px-3 py-2 bg-gray-50 flex-1"
                                />

                                {/* 選択ボタン */}
                                <button
                                  type="button"
                                  disabled={!isActive}
                                  onClick={() => {
                                    if (isActive) setShowDeptModal(true);
                                  }}
                                  className={`border px-3 h-10 rounded flex items-center justify-center min-w-[60px]
                                    ${isActive
                                      ? "text-teal-600 border-teal-600 cursor-pointer"
                                      : "text-gray-300 border-gray-300 cursor-not-allowed"
                                    }`}
                                >
                                  選択
                                </button>
                              </div>
                            );
                          }}
                        />

                        {/* 氏名 */}
                        <MasterFormField
                          control={form.control}
                          name="user_name"
                          label="氏名"
                          required
                          placeholder="東電 太郎"
                          className="w-1/3"
                        />

                        {/* メールアドレス */}
                        <MasterFormField
                          control={form.control}
                          name="email_address"
                          label="メールアドレス"
                          required
                          placeholder="xx@xx.jp"
                          className="w-1/3"
                        />

                        {/* 権限 */}
                        <MasterFormField
                          control={form.control}
                          name="user_role"
                          label="権限"
                          required
                          options={roleOptions}
                          className="w-1/3"
                        />
                      </CardContent>
                    </Card>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </form>
          </div>
        </Form>
      )}

      {/* ---------- 支店選択モーダル ---------- */}
      <div className="w-[400px]">
        <Dialog open={showDeptModal} onOpenChange={(open) => !open && setShowDeptModal(false)}>
          <DialogTrigger hidden />
          <DialogContent className="w-[40%] h-[560px] flex flex-col">
            {/* ヘッダー */}
            <DialogTitle className="flex-shrink-0 h-8">
              支店名の選択
            </DialogTitle>

            {/* コンテンツ */}
            <div className="flex-1 overflow-y-auto mt-4">
              <SearchDepartment
                departmentList={branchList}
                onSelect={(dept) => {
                  form.setValue("branch_name", dept.name);
                  form.setValue("branch_code", dept.id);
                  setBranchOrgTypeCode(dept.orgTypeCode);
                  setShowDeptModal(false);
                }}
              />
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </MasterLayout>
  );
}
