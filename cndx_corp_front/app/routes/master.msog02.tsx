import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import React, { useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import ErrorHint from "~/components/common/error-hint";
import MasterFormField from "~/components/common/master-form-field";
import MasterLayout from "~/components/layout/master-layout";
import { Form } from "~/components/ui";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { useScrollToError } from "~/hooks/useScrollToError";
import { msogSchema } from "~/lib/validations/msog_schema";
import { saveSuccessToast } from "../components/ui/use-toast";
import { getData, postData } from "../lib/fetch";

type PermissionValue = "×" | "〇" | "制限付";
interface ScreenPermissions {
  manager: PermissionValue;
  general: PermissionValue;
}
// パンくず定義
const breadcrumbItems = [
  { title: "利用組織マスタ登録・管理", link: "/master/msog01" },
  { title: "新規登録", link: "" },
];

const OrganizationRegistration: React.FC = () => {
  const navigate = useNavigate();
  // 全データを保持
  const [orgData, setOrgData] = useState<any[]>([]);
  // 組織種別
  const [orgType, setOrgType] = useState("");
  // エラーメッセージ
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);

  // 画面一覧と権限
  const [screens, setScreens] = useState<string[]>([]);
  const [permissions, setPermissions] = useState<Record<string, ScreenPermissions>>({});
  const [token, setToken] = useState<string | null>(null);

  type msogInputs = z.infer<typeof msogSchema> & { user_id?: string };
  const formDataRef = useRef<msogInputs | null>(null);
  const form = useForm<msogInputs>({
    resolver: zodResolver(msogSchema),
    defaultValues: {
      org_type: "",
      org_type_code: "",
      business_type: "",
      org_id: "",
      org_name: "",
      company_name: "",
      company_code: "",
      bank_code: "",
      branch_name: "",
      branch_code: "",
    },
  });

  const selectOrgTypeCode = useWatch({
    control: form.control,
    name: "org_type_code",
  });

  // APIから取得したデータを深くパースする関数
  // 文字列が JSON 形式であれば、JSON.parse を繰り返す
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function deepParse(raw: unknown): any {
    let v = raw;
    // 文字列が JSON 形式であれば、JSON.parse を繰り返す
    // ただし、無限ループを避けるために、文字列でない場合は break
    while (typeof v === "string") {
      try {
        v = JSON.parse(v);
      } catch {
        break;
      }
    }
    return v;
  }

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
      }
    }
  }, []);

  // 初期表示: 全組織＋画面名を1回のAPIで取得
  useEffect(() => {
    const init = async () => {
      try {
        // 組織情報を取得
        const url = `${API_ENDPOINTS.CORP_ORG.API_CORP_ORG_INFO_DETAIL}`;
        const raw = await getData(url, {});
        const parsed = deepParse(raw);
        let arr = parsed;
        if (Array.isArray(parsed)) {
          arr = parsed[0]?.detail_auth_list ?? parsed;
        } else if (parsed && typeof parsed === "object" && "detail_auth_list" in parsed) {
          arr = (parsed as any).detail_auth_list;
        }
        const data = Array.isArray(arr) ? arr : [arr];
        setOrgData(data);

        // orgType プルダウンの選択肢として org_id と org_name を保持
        // 画面一覧は authorities 内の screen_name をユニークに抽出
        const allScreens = new Set<string>();
        data.forEach((org) => {
          org.authorities.forEach((auth: any) => allScreens.add(auth.screen_name));
        });
        // Set から配列に変換
        const scrArr = Array.from(allScreens);
        setScreens(scrArr);

        // 初期権限をすべて×で設定
        const initPerms: Record<string, ScreenPermissions> = {};
        scrArr.forEach((name) => {
          initPerms[name] = { manager: "×", general: "×" };
        });
        setPermissions(initPerms);
      } catch (e) {
        console.error(e);
        setErrorMessage(e instanceof Error ? e.message : "データの取得に失敗しました。");
      }
    };
    init();
  }, []);

  // 組織種別選択時: orgData から該当エントリをフィルタし、表示名と権限を更新
  useEffect(() => {
    if (selectOrgTypeCode === "") return;
    const selected = orgData.find((org) => org.org_type_code === selectOrgTypeCode);
    if (!selected) return;
    setOrgType(selected.org_type ?? "");

    // 全画面を×で下準備
    const perms: Record<string, ScreenPermissions> = {};
    screens.forEach((name) => {
      perms[name] = { manager: "×", general: "×" };
    });

    // 選択orgの authorities で置き換え
    selected.authorities.forEach((auth: any) => {
      const key = auth.user_role === "1" ? "general" : "manager";
      const val: PermissionValue = auth.authority_code === "0" ? "〇" : auth.authority_code === "1" ? "制限付" : "×";
      perms[auth.screen_name][key] = val;
    });
    setPermissions(perms);
  }, [form, orgData, screens, selectOrgTypeCode]);

  const watchedCompanyCode = form.watch("company_code");
  const watchedBankCode = form.watch("bank_code");
  const watchedBranchCode = form.watch("branch_code");
  const watchedCompanyName = form.watch("company_name");
  const watchedBranchName = form.watch("branch_name");

  useEffect(() => {
    let newOrgId = form.getValues("org_id");
    let newOrgName = form.getValues("company_name");
    // 組織種別に応じて組織IDと組織名を設定
    if (selectOrgTypeCode === "01") {
      newOrgId = "TEP";
      form.setValue("business_type", "EP");
    } else if (selectOrgTypeCode === "02" || selectOrgTypeCode === "03") {
      newOrgId = "BNK" + watchedBankCode + watchedBranchCode;
      newOrgName = watchedCompanyName + " " + watchedBranchName;
      form.setValue("business_type", "金融機関");
    } else if (selectOrgTypeCode === "04") {
      newOrgId = "REP" + watchedCompanyCode;
      form.setValue("business_type", "REP");
    } else if (selectOrgTypeCode === "05") {
      newOrgId = "TCS";
      form.setValue("business_type", "TCS");
    } else if (selectOrgTypeCode === "07") {
      newOrgId = "SYS";
      form.setValue("business_type", "システム管理者");
    } else {
      newOrgId = watchedCompanyCode ?? "";
      form.setValue("business_type", "可視化事業者");
    }
    // 組織IDと組織名を更新
    form.setValue("org_id", newOrgId);
    form.setValue("org_name", newOrgName);
  }, [
    form,
    selectOrgTypeCode,
    watchedCompanyCode,
    watchedBankCode,
    watchedBranchCode,
    watchedCompanyName,
    watchedBranchName,
  ]);

  const handleRegister = async (data?: msogInputs) => {
    if (data) {
      formDataRef.current = {
        ...data,
        org_type: orgType,
        org_type_code: selectOrgTypeCode,
      };
    }
    if (formDataRef.current) {
      mutation.mutate(formDataRef.current);
    }
  };

  const mutation = useMutation({
    mutationFn: (payload: msogInputs) => {
      const url = API_ENDPOINTS.CORP_ORG.API_CORP_ORG_INFO_REGIST;
      return postData(url, payload, {
        Authorization: `Bearer ${token}`,
      });
    },
    onSuccess: () => {
      navigate("/master/msog01");
      saveSuccessToast();
    },
    onError: (error) => {
      setErrorMessage(error.message);
      // toast({
      //   description: error.message,
      //   variant: "destructive",
      // });
    },
  });

  const uniqueOrgTypesMap = new Map();
  orgData.forEach((org) => {
    if (!uniqueOrgTypesMap.has(org.org_type_code)) {
      uniqueOrgTypesMap.set(org.org_type_code, {
        id: org.org_type_code,
        name: org.org_type,
      });
    }
  });

  const uniqueOrgTypes = Array.from(uniqueOrgTypesMap.values())
    .sort((a, b) => a.name.localeCompare(b.name));

  const watchedOrgType = form.watch("org_type_code");

  useEffect(() => {
    if (!watchedOrgType) return;

    // 組織種別が変更された場合、関連フィールドをリセット
    form.setValue("company_name", "");
    form.setValue("company_code", "");
    form.setValue("bank_code", "");
    form.setValue("branch_name", "");
    form.setValue("branch_code", "");
    form.clearErrors();

    // orgTypeCode を更新
    const matched = orgData.find((d) => d.org_type_code === watchedOrgType);
    if (matched) {
      form.setValue("org_type_code", matched.org_type_code ?? "");
      form.setValue("org_type", matched.org_type ?? "");
    } else {
      form.setValue("org_type_code", "");
    }
  }, [form, orgData, watchedOrgType]);
  const isBank = selectOrgTypeCode === "02" || selectOrgTypeCode === "03";

  return (
    <>
      <MasterLayout
        breadcrumbItems={breadcrumbItems}
        showRegisterButton={true}
        showCancelButton={true}
        processClick={() => form.handleSubmit(handleRegister)()}
        onCancelClick={() => navigate("/master/msog01")}
        footerType="default"
      >
        <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />
        <div ref={errorTopRef as React.RefObject<HTMLDivElement>} className="w-4/5 mt-5 ml-4 scroll-mt-[300px]">
          <ErrorHint message={errorMessage} className="w-full" bodyClassName="py-4" />
        </div>
        <Form {...form}>
          <form className="grid gap-4" onSubmit={form.handleSubmit(handleRegister)}>
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="pl-10">基本情報</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col pl-20 pr-20">
                <MasterFormField
                  control={form.control}
                  name="org_name"
                  label="組織名"
                  placeholder=""
                  triggerValidation={(name) => form.trigger(name)}
                  isEditing={true}
                  disabled={true}
                  className="w-1/3"
                />

                <MasterFormField
                  control={form.control}
                  name="org_type_code"
                  label="組織種別"
                  required
                  options={uniqueOrgTypes}
                  triggerValidation={(name) => form.trigger(name)}
                  isEditing={true}
                  className="w-1/3"
                />

                <MasterFormField
                  control={form.control}
                  name="org_id"
                  label="組織ID"
                  placeholder=""
                  triggerValidation={(name) => form.trigger(name)}
                  isEditing={true}
                  disabled={true}
                  className="w-1/3"
                />

                <MasterFormField
                  control={form.control}
                  name="company_name"
                  label="企業名"
                  required
                  placeholder="東京電力エナジーパートナー株式会社"
                  triggerValidation={(name) => form.trigger(name)}
                  isEditing={true}
                  className="w-1/3"
                />
                <MasterFormField
                  control={form.control}
                  name="company_code"
                  label="企業コード"
                  required={!isBank}
                  placeholder={!isBank ? "半角英字・大文字・3文字" : ""}
                  type="text"
                  triggerValidation={(name) => form.trigger(name)}
                  isEditing={true}
                  disabled={isBank}
                  className={"w-1/3"}
                />

                <MasterFormField
                  control={form.control}
                  name="bank_code"
                  label="銀行コード"
                  required={isBank}
                  placeholder={isBank ? "半角数字4桁" : ""}
                  type="text"
                  triggerValidation={(name) => form.trigger(name)}
                  isEditing={true}
                  disabled={!isBank}
                  className={"w-1/3"}
                />
                <MasterFormField
                  control={form.control}
                  name="branch_name"
                  label="支店名"
                  required={isBank}
                  placeholder={isBank ? "xx支店" : ""}
                  type="text"
                  triggerValidation={(name) => form.trigger(name)}
                  isEditing={true}
                  disabled={!isBank}
                  className={"w-1/3"}
                />
                <MasterFormField
                  control={form.control}
                  name="branch_code"
                  label="支店コード"
                  required={isBank}
                  placeholder={isBank ? "半角数字3桁" : ""}
                  type="text"
                  triggerValidation={(name) => form.trigger(name)}
                  isEditing={true}
                  disabled={!isBank}
                  className={"w-1/3"}
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
    </>
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

export default OrganizationRegistration;
