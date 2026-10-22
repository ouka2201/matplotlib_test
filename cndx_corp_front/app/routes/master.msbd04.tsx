import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { BreadCrumbType } from "~/components/common/breadcrumb";
import MasterFormField from "~/components/common/master-form-field";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import MasterLayout from "~/components/layout/master-layout";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Form } from "~/components/ui/form";
import { toast } from "~/components/ui/use-toast";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { Messages } from "~/constants/messages/message";
import { generateCompanyAddress } from "~/hooks/useAutoCompanyAddress";
import { msbdSchema } from "~/lib/validations/msbd";
import { Icon, Text } from "../components/import";
import { getData, postData } from "../lib/fetch";

// 1. 表示専用フィールド型を定義
type DisplayFields = {
  building_address?: string;
  agreement_category_label?: string;
};

type Formnames = z.infer<typeof msbdSchema>;
interface PrefectureOption {
  id: string;
  name: string;
}

type BuildingInfoLocationState = {
  customerData?: any;
  fromScreen?: "ebrc05" | "msbd01";
  returnPath?: string;
  returnState?: any;
  buildingName?: string;
};

const BuildingInfoPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as BuildingInfoLocationState) || {};
  const customerData = state.customerData;
  const fromScreen = state.fromScreen;
  const returnPath = state.returnPath;
  const returnState = state.returnState;
  const buildingNameFromState = state.buildingName;
  // const breadcrumbItems = [
  //   { title: "拠点マスタ管理", link: "/master/msbd01", state: { customerData }, },
  //   { title: "拠点情報", link: "" },
  // ];

  const [prefectureOptions, setPrefectureOptions] = useState<PrefectureOption[]>([]);
  // const { session, clearSession } = useSession();
  const [token] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      return sessionData ? JSON.parse(sessionData).token : null;
    }
    return null;
  });
  const [isEditMode, setIsEditMode] = useState(false);
  const canEdit = fromScreen !== "ebrc05";
  // エラーメッセージ
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const formDataRef = useRef<Formnames | null>(null);
  const form = useForm<Formnames & DisplayFields>({
    resolver: zodResolver(msbdSchema),
    defaultValues: {
      org_id: "",
      corporate_number: "",
      agreement_category: "",
      building_id: "",
      location_identifier_name: "",
      building_address_prefecture: "",
      building_address_city: "",
      gross_floor_area: "",
      industry_class_detail_code: "",
      industry_class_detail_name: "",
      benchmark_denom: "",
      benchmark_val: "",
      group1: "",
      group2: "",
      group3: "",
      group4: "",
      group5: "",
      building_address: "",
      agreement_category_label: "",
    },
  });
  const watchedBuildingName = form.watch("location_identifier_name");

  const breadcrumbItems: BreadCrumbType[] = useMemo(() => {
    if (fromScreen === "ebrc05") {
      return [
        {
          title: "レポート作成・管理",
          link: "/",
        },
        {
          title: customerData?.company_name || "お客さま名",
          link: returnPath || "/energy-building/ebrc05",
          state: returnState || { customerData },
        },
        {
          title: watchedBuildingName || buildingNameFromState || "拠点名",
          link: "",
        },
      ];
    }

    return [
      {
        title: "拠点マスタ管理",
        link: "/master/msbd01",
        state: { customerData },
      },
      {
        title: "拠点情報",
        link: "",
      },
    ];
  }, [fromScreen, customerData, returnPath, returnState, watchedBuildingName, buildingNameFromState]);
  // 都道府県マスタの取得
  useEffect(() => {
    let isCancelled = false;

    const fetchMaster = async () => {
      if (!token) return;
      const masterEntries = [
        { name: "prefecture", params: {} as Record<string, string> }
      ];
      try {
        const data = await getMasterDataForCondition(masterEntries, token);
        if (!isCancelled) {
          setPrefectureOptions(data["prefecture"] ?? []);
        }
      } catch (err) {
        if (!isCancelled) {
          console.error(Messages.VALIDATION.data.fetch_master_error, err);
          setErrorMessage(err instanceof Error ? err.message : Messages.VALIDATION.api.fetch_error);
        }
      }
    };

    fetchMaster();

    return () => {
      isCancelled = true;
    };
  }, [token]);

  const [groupOptionsMap, setGroupOptionsMap] = useState<{
    [key: string]: { id: string; name: string }[];
  }>({
    グループ１: [],
    グループ２: [],
    グループ３: [],
    グループ４: [],
    グループ５: [],
  });

  useEffect(() => {
    const fetchBuildingInfo = async () => {
      const session = sessionStorage.getItem("selectedBuildingData");
      if (!session) return;
      const parsed = JSON.parse(session);
      // 建物情報照会API
      const params = {
        corporate_number: parsed?.corporate_number ?? "",
        agreement_code: parsed.agreement_code ?? "",
        org_id: parsed.org_id ?? "",
        building_id: parsed.building_id,
      };

      const query = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, v as ""])).toString();

      const requestUrl = `${API_ENDPOINTS.BUILDING.BUILDING_INFO_DETAIL}${query ? `?${query}` : ""}`;

      try {
        const data = await getData(requestUrl, {
          Authorization: `Bearer ${token}`,
        });
        if (!data) {
          setErrorMessage("拠点情報の取得に失敗しました。");
          return;
        }

        const building = data?.result?.buildingBasicInfo ?? {};
        const groupSettingInfo = data?.result?.groupSettingInfoItem ?? [];

        // === プルダウン用 options 作成 ===
        const optionMap: { [key: string]: { id: string; name: string }[] } = {
          グループ１: [],
          グループ２: [],
          グループ３: [],
          グループ４: [],
          グループ５: [],
        };
        // groupSettingInfo.forEach((item: any, index: number) => {
        //   const groupLabel = `グループ${toZenkakuNumber((index + 1).toString())}`;
        //   optionMap[groupLabel] = (item.group_options ?? [])
        //     .filter((opt: string) => typeof opt === "string" && opt.trim() !== "")
        //     .map((opt: string, i: number) => ({ id: String(i + 1), name: opt })); // ← index+1 を id にする
        // });
        groupSettingInfo.forEach((item: any) => {
          const groupLabel = `グループ${toZenkakuNumber(item.group_id)}`;
          const options = (item.group_options ?? [])
            .filter((opt: string) => typeof opt === "string" && opt.trim() !== "")
            .map((opt: string, i: number) => ({ id: String(i + 1), name: opt }));
          optionMap[groupLabel] = [
            { id: "0", name: "" },
            ...options
          ];
        });


        setGroupOptionsMap(optionMap);
        // === フォーム初期値を設定 ===
        form.reset({
          org_id: building.org_id || "",
          corporate_number: building.corporate_number || "",
          agreement_category: building.agreement_category || "",
          agreement_category_label: building.agreement_name || "",
          building_id: building.building_id || "",
          location_identifier_name: building.location_identifier_name || "",
          building_address_prefecture: building.building_address_prefecture || "",
          building_address_city: building.building_address_city || "",
          building_address: building.building_address || "",
          gross_floor_area: building.gross_floor_area?.toString() ?? "",
          industry_class_detail_code: building.industry_class_detail_code || "",
          industry_class_detail_name: building.industry_class_detail_name || "",
          benchmark_denom: building.benchmark_denom || "",
          benchmark_val: building.benchmark_val?.toString() ?? "",
          group1: building.group1 ? (optionMap["グループ１"].find(opt => opt.name === building.group1)?.id ?? "") : "",
          group2: building.group2 ? (optionMap["グループ２"].find(opt => opt.name === building.group2)?.id ?? "") : "",
          group3: building.group3 ? (optionMap["グループ３"].find(opt => opt.name === building.group3)?.id ?? "") : "",
          group4: building.group4 ? (optionMap["グループ４"].find(opt => opt.name === building.group4)?.id ?? "") : "",
          group5: building.group5 ? (optionMap["グループ５"].find(opt => opt.name === building.group5)?.id ?? "") : "",
        });

      } catch (error: any) {
        // setErrorMessage(error instanceof Error ? error.message : Messages.VALIDATION.api.fetch_error);
        setErrorMessage(error.data?.message);
        return null;
      } finally {
        // setIsDataLoading(false);
      }
    };

    fetchBuildingInfo();
  }, [form, token]);

  const onSubmit = async (data?: Formnames & DisplayFields) => {
    if (!data) return;
    generateCompanyAddress(form, prefectureOptions, "building_address_prefecture",
      "building_address_city", "building_address"); // 会社住所自動生成
    // 画面専用のフィールドは除外
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { building_address, agreement_category_label, ...rest } = data;

    // group1～group5 を数値化して payload に入れる
    // "0" (未選択) を空文字列に変換
    const payload = {
      ...rest,
      group1: rest.group1 === "0" ? "" : (rest.group1 || ""),
      group2: rest.group2 === "0" ? "" : (rest.group2 || ""),
      group3: rest.group3 === "0" ? "" : (rest.group3 || ""),
      group4: rest.group4 === "0" ? "" : (rest.group4 || ""),
      group5: rest.group5 === "0" ? "" : (rest.group5 || ""),
    };
    formDataRef.current = payload;
    mutation.mutate(payload);
  };

  const mutation = useMutation({
    mutationFn: (payload: Formnames) => {
      const url = "/api/building/info";
      return postData(url, payload, {
        Authorization: `Bearer ${token}`,
      });
    },
    onSuccess: () => {
      setIsEditMode(false);
      setErrorMessage("");
      navigate("/master/msbd04", { state: { customerData } });
      toast({ title: "更新完了", duration: 2000, });
    },
    onError: (error: any) => {
      // setErrorMessage(error instanceof Error ? error.message : "データの送信に失敗しました。");
      setErrorMessage(error.data?.message);
      // toast({ description: error.message, variant: "destructive" });
    },
  });

  /**
 * 半角数字を全角数字に変換する関数
 */
  const toZenkakuNumber = (str: string): string => {
    return str.replace(/[0-9]/g, (s) =>
      String.fromCharCode(s.charCodeAt(0) + 0xfee0)
    );
  };


  return (
    <MasterLayout
      breadcrumbItems={breadcrumbItems}
      showRegisterButton={isEditMode}
      showCancelButton={isEditMode}
      processClick={() => form.handleSubmit(onSubmit)()}
      onCancelClick={async () => {
        form.reset();
        setErrorMessage("");
        setIsEditMode(false);
      }}
      footerType="default"
    >
      {errorMessage && (
        <div className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden mt-5 ml-4">
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
      <FormProvider {...form}>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-6 pb-24">

            {/* 基本情報 */}
            <Card className="mb-6">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg font-bold">基本情報</CardTitle>
                {canEdit && !isEditMode && (<Button
                  type="button"
                  variant="primary"
                  onClick={() => setIsEditMode(true)}
                >
                  拠点情報編集
                </Button>
                )}
              </CardHeader>

              <CardContent className="grid pl-20 pr-20">
                <MasterFormField
                  name="agreement_category_label"
                  label="可視化事業者"
                  control={form.control}
                  isEditing={isEditMode}
                  disabled
                  className="w-2/3"
                />
                <MasterFormField
                  name="building_id"
                  label="拠点ID"
                  control={form.control}
                  isEditing={isEditMode}
                  disabled
                  className="w-2/3"
                />
                <MasterFormField
                  name="location_identifier_name"
                  label="拠点名"
                  control={form.control}
                  isEditing={isEditMode}
                  required
                  className="w-2/3"
                />
                <div className={`flex items-center gap-1`}>
                  {isEditMode ? (
                    <>
                      <MasterFormField
                        control={form.control}
                        name="building_address_prefecture"
                        label="拠点所在地（都道府県）"
                        options={prefectureOptions}
                        triggerValidation={(name) => form.trigger(name)}
                        isEditing={isEditMode}
                        required
                        className="w-1/3"
                      />
                      <MasterFormField
                        control={form.control}
                        name="building_address_city"
                        label="拠点所在地（市区町村以降）"
                        triggerValidation={(name) => form.trigger(name)}
                        isEditing={isEditMode}
                        required
                        className="w-1/3"
                      />
                    </>
                  ) : (
                    <MasterFormField
                      key="building_address_prefecture"
                      control={form.control}
                      name="building_address"
                      label="所在地"
                      isEditing={isEditMode}
                      className="w-2/3"
                    />
                  )}
                </div>
                <MasterFormField
                  name="gross_floor_area"
                  label="延床面積"
                  control={form.control}
                  isEditing={isEditMode}
                  // required
                  className="w-2/3"
                />

              </CardContent>

              {/* 日本産業分類 */}
              <CardHeader><CardTitle className="text-lg font-bold">日本産業分類</CardTitle></CardHeader>
              <CardContent className="grid pl-20 pr-20">
                <MasterFormField
                  name="industry_class_detail_code"
                  label="細分類番号"
                  control={form.control}
                  isEditing={isEditMode}
                  className="w-2/3"
                />
                <MasterFormField
                  name="industry_class_detail_name"
                  label="細分類"
                  control={form.control}
                  isEditing={isEditMode}
                  className="w-2/3"
                />
              </CardContent>

              {/* ベンチマーク */}
              <CardHeader><CardTitle className="text-lg font-bold">原単位分母</CardTitle></CardHeader>
              <CardContent className="grid pl-20 pr-20">
                <MasterFormField
                  name="benchmark_denom"
                  label="原単位分母"
                  control={form.control}
                  isEditing={isEditMode}
                  className="w-2/3"
                />
                <MasterFormField
                  name="benchmark_val"
                  label="原単位分母数値"
                  control={form.control}
                  isEditing={isEditMode}
                  className="w-2/3"
                />
              </CardContent>

              {/* グループ情報 */}
              <CardHeader><CardTitle className="text-lg font-bold">グループ</CardTitle></CardHeader>
              <CardContent className="grid pl-20 pr-20">
                <MasterFormField
                  control={form.control}
                  name="group1"
                  label="グループ１"
                  options={groupOptionsMap["グループ１"]}
                  disabled={groupOptionsMap["グループ１"].length === 0}
                  isEditing={isEditMode}
                  className="w-2/3"
                />

                <MasterFormField
                  control={form.control}
                  name="group2"
                  label="グループ２"
                  options={groupOptionsMap["グループ２"]}
                  disabled={groupOptionsMap["グループ２"].length === 0}
                  isEditing={isEditMode}
                  className="w-2/3"
                />
                <MasterFormField
                  control={form.control}
                  name="group3"
                  label="グループ３"
                  options={groupOptionsMap["グループ３"]}
                  disabled={groupOptionsMap["グループ３"].length === 0}
                  isEditing={isEditMode}
                  className="w-2/3"
                />
                <MasterFormField
                  control={form.control}
                  name="group4"
                  label="グループ４"
                  options={groupOptionsMap["グループ４"]}
                  disabled={groupOptionsMap["グループ４"].length === 0}
                  isEditing={isEditMode}
                  className="w-2/3"
                />
                <MasterFormField
                  control={form.control}
                  name="group5"
                  label="グループ５"
                  options={groupOptionsMap["グループ５"]}
                  disabled={groupOptionsMap["グループ５"].length === 0}
                  isEditing={isEditMode}
                  className="w-2/3"
                />
              </CardContent>
            </Card>

          </form>
        </Form>
      </FormProvider>
    </MasterLayout>
  );
};

export default BuildingInfoPage;
