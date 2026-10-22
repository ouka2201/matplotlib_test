import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import React, { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import MasterFormField from "~/components/common/master-form-field";
import MasterLayout from "~/components/layout/master-layout";
import { Form } from "~/components/ui";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { useScrollToError } from "~/hooks/useScrollToError";
import { msogSchema } from "~/lib/validations/msog_schema";
import { Icon, Text } from "../components/import";
import { toast } from "../components/ui/use-toast";
import { getData, postData } from "../lib/fetch";

type PermissionValue = "×" | "〇" | "制限付";
interface ScreenPermissions {
  manager: PermissionValue;
  general: PermissionValue;
}

interface OrganizationData {
  org_id?: string;
  org_name?: string;
  org_type?: string;
  org_type_code?: string;
  business_type?: string;
  agreement_code?: string;
  agreement_name?: string;
  company_name?: string;
  company_code?: string;
  bank_code?: string;
  branch_name?: string;
  branch_code?: string;
  authorities: Array<{
    screen_name: string;
    user_role: string;
    authority_code: string;
    authority_id: string;
  }>;
}
interface LocationState {
  customerData: {
    org_id: string;
    org_name: string;
  };
}

// string化された JSON をオブジェクトに戻すユーティリティ
function deepParse(raw: unknown): any {
  let v = raw;
  while (typeof v === "string") {
    try {
      v = JSON.parse(v);
    } catch {
      break;
    }
  }
  return v;
}

const OrganizationEdit: React.FC = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [token, setToken] = useState<string | null>(null);
  const { customerData } = (state || {}) as LocationState;
  const orgIdFromNav = customerData?.org_id ?? ""; // 前画面から受け取る

  const [orgData, setOrgData] = useState<OrganizationData | null>(null);
  const [screens, setScreens] = useState<string[]>([]);
  const [isEditMode, setIsEditMode] = useState(false);
  // エラーメッセージ
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);
  const [permissions, setPermissions] = useState<Record<string, ScreenPermissions>>({});

  type msogInputs = z.infer<typeof msogSchema>;
  const formDataRef = useRef<msogInputs | null>(null);
  const form = useForm<msogInputs>({
    resolver: zodResolver(msogSchema),
    defaultValues: {
      org_type: orgData?.org_type || "",
      org_id: orgData?.org_id || "",
      org_name: orgData?.org_name || "",
      company_name: orgData?.company_name || "",
      company_code: orgData?.company_code || "",
      bank_code: orgData?.bank_code || "",
      branch_name: orgData?.branch_name || "",
      branch_code: orgData?.branch_code || "",
    },
  });

  const orgTypeCode = form.getValues("org_type_code");
  const watchedCompanyName = form.watch("company_name");
  const watchedBranchName = form.watch("branch_name");

  // 新規と同じ型定義
  const breadcrumbItems = [
    { title: "利用組織マスタ登録・管理", link: "/master/msog01" },
    { title: customerData?.org_name ?? "", link: "" },
  ];

  useEffect(() => {
    (async () => {
      try {
        if (!orgIdFromNav) return;
        const query = new URLSearchParams({ org_id: orgIdFromNav }).toString();
        const url = `${API_ENDPOINTS.CORP_ORG.API_CORP_ORG_INFO_DETAIL}?${query}`;
        const raw = await getData(url, {});
        const parsed = deepParse(raw);
        // API 直下が配列なのでそのまま扱う
        let arr = parsed;
        if (Array.isArray(parsed)) {
          arr = parsed[0]?.detail_auth_list ?? parsed;
        } else if (parsed && typeof parsed === "object" && "detail_auth_list" in parsed) {
          arr = (parsed as any).detail_auth_list;
        }
        const org = Array.isArray(arr) ? arr : [arr];
        const data = org[0] as OrganizationData;
        // 組織情報を取得
        setOrgData(data);
        form.reset({
          org_type_code: data.org_type_code || "",
          business_type: data.business_type || "",
          org_type: data.org_type || "",
          org_id: data.org_id || "",
          org_name: data.org_name || "",
          company_name: data.company_name || "",
          company_code: data.company_code || "",
          bank_code: data.bank_code || "",
          branch_name: data.branch_name || "",
          branch_code: data.branch_code || "",
        });

        // 画面一覧抽出
        const uniqueScreens = Array.from(new Set(data.authorities.map((a) => a.screen_name)));
        setScreens(uniqueScreens);
        const perms: Record<string, ScreenPermissions> = {};
        uniqueScreens.forEach((name) => {
          perms[name] = { manager: "×", general: "×" };
        });
        data.authorities.forEach((auth: any) => {
          const key = auth.user_role === "1" ? "general" : "manager";
          const val: PermissionValue =
            auth.authority_code === "0" ? "〇" : auth.authority_code === "1" ? "制限付" : "×";
          perms[auth.screen_name][key] = val;
        });
        setPermissions(perms);
      } catch (e) {
        console.error(e);
        setErrorMessage(e instanceof Error ? e.message : "データの取得に失敗しました。");
      }
    })();
  }, [form, orgIdFromNav]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
      }
    }
  }, []);

  useEffect(() => {
    let newOrgName = form.getValues("company_name");
    if (orgTypeCode === "02" || orgTypeCode === "03") {
      newOrgName = watchedCompanyName + " " + watchedBranchName;
    }
    form.setValue("org_name", newOrgName);
  }, [form, orgTypeCode, watchedCompanyName, watchedBranchName]);

  const handleUpdate = async (data?: msogInputs) => {
    if (data) {
      formDataRef.current = {
        ...data,
      };
    }
    if (formDataRef.current) {
      mutation.mutate(formDataRef.current);
    }
  };

  const mutation = useMutation({
    mutationFn: (payload: msogInputs) => {
      const url = API_ENDPOINTS.CORP_ORG.API_CORP_ORG_INFO_UPDATE;
      return postData(url, payload, {
        Authorization: `Bearer ${token}`,
      });
    },
    onSuccess: () => {
      setIsEditMode(false);
      navigate("/master/msog04");
      toast({title: "更新完了", duration: 2000,});
    },
    onError: (error) => {
      setErrorMessage(error.message);
      // toast({ description: error.message, variant: "destructive" });
    },
  });

  const isBank = orgTypeCode === "02" || orgTypeCode === "03";

  return (
    <MasterLayout
      breadcrumbItems={breadcrumbItems}
      showRegisterButton={isEditMode}
      showCancelButton={isEditMode}
      processClick={() => form.handleSubmit(handleUpdate)()}
      onCancelClick={async () => {
        form.reset();
        setIsEditMode(false);
        setErrorMessage("");
      }}
      footerType="default"
    >
      <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />

      {errorMessage && (
        <div
          ref={errorTopRef as React.RefObject<HTMLDivElement>}
          className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden mt-5 ml-4 scroll-mt-[300px]"
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
      <Form {...form}>
        <form className="grid relative" onSubmit={form.handleSubmit(handleUpdate)}>
          <Card className="mb-8">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg font-bold pl-10">基本情報</CardTitle>
              {!isEditMode && (
                <Button type="button" variant="primary" size="sm" className="mr-16" onClick={() => setIsEditMode(true)}>
                  編集
                </Button>
              )}
            </CardHeader>
            <CardContent className="flex flex-col pl-20 pr-20">
              <MasterFormField
                control={form.control}
                name="org_name"
                label="組織名"
                disabled={true}
                isEditing={true}
                className="w-1/3"
              />
              <MasterFormField
                control={form.control}
                name="org_type"
                label="組織種別"
                options={[]}
                isEditing={true}
                disabled={true}
                className="w-1/3"
              />
              <MasterFormField
                control={form.control}
                name="org_id"
                label="組織ID"
                disabled={true}
                isEditing={true}
                className="w-1/3"
              />
              <MasterFormField
                control={form.control}
                name="company_name"
                label="企業名"
                required={isEditMode}
                isEditing={true}
                disabled={!isEditMode}
                className="w-1/3"
              />
              <MasterFormField
                control={form.control}
                name="company_code"
                label="企業コード"
                disabled={true}
                isEditing={true}
                className="w-1/3"
              />
              <MasterFormField
                control={form.control}
                name="bank_code"
                label="銀行コード"
                disabled={true}
                isEditing={true}
                className="w-1/3"
              />
              <MasterFormField
                control={form.control}
                name="branch_name"
                label="支店名"
                required={isBank && isEditMode}
                disabled={!isEditMode || !isBank}
                isEditing={true}
                className="w-1/3"
              />
              <MasterFormField
                control={form.control}
                name="branch_code"
                label="支店コード"
                disabled={true}
                isEditing={true}
                className="w-1/3"
              />
            </CardContent>
            <div className="mx-20 mb-16">
              <Table className="border rounded">
                <TableHeader className="bg-gray-100">
                  <TableRow>
                    <TableHead className="">権限付与画面</TableHead>
                    <TableHead className="">管理者</TableHead>
                    <TableHead className="">一般</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {screens.map((screen) => (
                    <TableRow key={screen}>
                      <TableCell className="">{screen}</TableCell>
                      <TableCell className="">
                        <PermissionBadge value={permissions[screen]?.manager || "×"} />
                      </TableCell>
                      <TableCell className="">
                        <PermissionBadge value={permissions[screen]?.general || "×"} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        </form>
      </Form>
    </MasterLayout>
  );
};
const PermissionBadge: React.FC<{ value: PermissionValue }> = ({ value }) => {
  const styleMap: Record<string, React.CSSProperties> = {
    "×": { background: "#ffe3e3", color: "#c92a2a" },
    〇: { background: "#ebfbee", color: "#2b8a3e" },
    制限付: { background: "#fff3bf", color: "#e67700" },
  };
  return <div style={{ ...styles.badge, ...styleMap[value] }}>{value}</div>;
};

// スタイル定義
const styles: Record<string, React.CSSProperties> = {
  permissionTable: {
    border: "1px solid #dee2e6",
    borderRadius: "4px",
    overflow: "hidden",
  },
  tableHeader: {
    display: "grid",
    gridTemplateColumns: "2fr 1fr 1fr",
    padding: "1rem",
    backgroundColor: "#e9ecef",
    fontWeight: 600,
    color: "#495057",
    textAlign: "center",
  },
  tableRow: {
    display: "grid",
    gridTemplateColumns: "2fr 1fr 1fr",
    padding: "1rem",
    backgroundColor: "#fff",
    borderBottom: "1px solid #dee2e6",
    textAlign: "center",
  },
  badge: {
    display: "inline-block",
    padding: "0.25rem 0.75rem",
    borderRadius: "12px",
    fontSize: "0.875rem",
    fontWeight: 500,
    textAlign: "center",
    minWidth: "80px",
  },
};

export default OrganizationEdit;
