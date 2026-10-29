import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import MasterFormField from "~/components/common/master-form-field";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import MasterLayout from "~/components/layout/master-layout";
import { useSession } from "~/components/layout/session-provider";
import SearchOrganization from "~/components/screen/master/mscs03/SearchAgreementOrg";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "~/components/ui/accordion";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "~/components/ui/dialog";
import { Form } from "~/components/ui/form";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { Messages } from "~/constants/messages/message";
import { generateCompanyAddress } from "~/hooks/useAutoCompanyAddress";
import { useRoleFlags } from "~/hooks/useRoleFlags";
import { useScrollToError } from "~/hooks/useScrollToError";
import { getData, postData } from "~/lib/fetch";
import { getCircledNumber } from "~/lib/utils";
import { mscsSchema } from "~/lib/validations/mscs";
import "~/styles/screen/master/mscs01.css";
import { CdNmOption, mscsInputs } from "~/types/screen/master/mscs/mscsType";
import { Icon, Text } from "../components/import";
import { saveSuccessToast } from "../components/ui/use-toast";

export default function CustomerDetailForm() {
  const location = useLocation();
  const displayMode = location.state?.mode;
  const navigate = useNavigate();

  // 状態管理
  const [isLoading, setIsLoading] = useState(false);
  const { session } = useSession();
  // EP管理者フラグ
  const { isEpAdmin } = useRoleFlags();

  const isNewMode = displayMode === "new";
  const [isEditing, setIsEditing] = useState(isNewMode);
  const [newOfficeIndex, setNewOfficeIndex] = useState<number | null>(null);
  const [token, setToken] = useState<string | null>(session?.token ?? null);
  const [userId, setUserId] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>();
  const [prefectureList, setPrefectureList] = useState<CdNmOption[]>();
  const [aggreeCategoryList, setAggreeCategoryList] = useState<CdNmOption[]>();
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);
  const [openAgreementOrgDialogIndex, setOpenAgreementOrgDialogIndex] = useState<number | null>(null);
  const isNewRef = useRef(displayMode === "new").current;
  // const formDataRef = useRef<CustomerCompany | null>(null);
  const customerData = location.state?.customerData;
  const [initialFormData, setInitialFormData] = useState<z.infer<typeof mscsSchema> | null>(null);

  // フォーム管理
  const form = useForm<mscsInputs>({
    resolver: zodResolver(mscsSchema),
    defaultValues: {
      company_name: "",
      company_name_kana: "",
      corporate_number: customerData?.corporate_number ?? "",
      company_address_prefecture: "",
      company_address_city: "",
      company_address: "",
      office_info_list: [],
    },
  });

  // useFieldArrayで拠点情報を管理
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "office_info_list",
  });

  // session情報セット
  useEffect(() => {
    const sessionData = sessionStorage.getItem("session");
    if (sessionData) {
      const sessionObj = JSON.parse(sessionData);
      setToken(sessionObj?.token ?? null);
      setUserId(sessionObj?.email ?? null);
      setOrgId(sessionObj?.authorityInfo?.org_id ?? null);
    }
  }, []);

  // 同意書取得経路情報
  useEffect(() => {
    let isCancelled = false;

    const fetchMaster = async () => {
      if (!token) return;
      const masterEntries = [
        {
          name: "consent-route",
          params: {
            agreement_category__startswith: "",
          },
        },
        { name: "prefecture", params: {} as Record<string, string> },
      ];
      try {
        const data = await getMasterDataForCondition(masterEntries, token);
        if (!isCancelled) {
          const sorted_route = data["consent-route"].slice().sort((a: any, b: any) => {
            if (a.id === "00" && b.id !== "00") return 1;
            if (a.id !== "00" && b.id === "00") return -1;
            return 0;
          });
          setAggreeCategoryList(sorted_route ?? []);
          setPrefectureList(data["prefecture"] ?? []);
        }
      } catch (err: any) {
        if (!isCancelled) {
          console.error(Messages.VALIDATION.data.fetch_master_error, err);
          // setErrorMessage(err instanceof Error ? err.message : Messages.VALIDATION.api.fetch_error);
          setErrorMessage(err.data?.message);
        }
      }
    };

    fetchMaster();

    return () => {
      isCancelled = true;
    };
  }, [token]);

  // API でデータ取得してフォームに反映
  useEffect(() => {
    const fetchData = async () => {
      if (!customerData?.corporate_number || !token) return;
      const base = API_ENDPOINTS.CUSTOMER_MASTER.MASTER_LIST;
      const url = `${base}?corporate_number=${encodeURIComponent(customerData?.corporate_number)}`;

      try {
        const res = await getData(url, {
          Authorization: `Bearer ${token}`,
        });

        const list = res?.result;

        if (Array.isArray(list) && list.length > 0) {
          const customer = list[0]; // API が配列返すなら先頭を利用
          const initialValues = {
            ...customer,
            office_info_list: (customer.office_info_list ?? []).map((o: any) => ({
              ...o,
              location_identifier_name: o.location_identifier_name ?? "",
              building_address_prefecture: o.building_address_prefecture ?? "",
              building_address_city: o.building_address_city ?? "",
              supply_point_number: o.supply_point_number ?? "",
              agreement_category: o.agreement_category ?? "",
              agreement_org: o.agreement_org ?? "",
              ep_office_code: o.ep_office_code ?? "",
              ep_customer_number: o.ep_customer_number ?? "",
              isFromApi: true,
            })),
          };
          // フォームに最新データをセット
          form.reset(initialValues);
          setInitialFormData(initialValues);
        }
      } catch (err: any) {
        console.error("企業データ取得失敗:", err);
        setErrorMessage(err.data?.message);
      }
    };

    fetchData();
  }, [customerData, token, form, prefectureList]);

  // 拠点追加
  const addOffice = () => {
    const nextIndex = (form.getValues("office_info_list") ?? []).length;
    setNewOfficeIndex(nextIndex);
    append({
      agreement_category: "",
      agreement_org: "",
      // building_name: "",
      location_identifier_name: "",
      building_address_prefecture: "",
      building_address_city: "",
      ep_office_code: "",
      ep_customer_number: "",
      supply_point_number: "",
      building_id: "",
      isFromApi: false,
    });
  };

  // 拠点削除
  const deleteOffice = (index: number) => {
    // remove(index);
    const currentValues = form.getValues("office_info_list") ?? [];
    const newValues = currentValues.filter((_, i) => i !== index);
    form.setValue("office_info_list", newValues);
    if (newOfficeIndex !== null) {
      if (index === newOfficeIndex) setNewOfficeIndex(null);
      else if (index < newOfficeIndex) setNewOfficeIndex(newOfficeIndex - 1);
    }
  };
  const mutation = useMutation({
    mutationFn: (data: mscsInputs) => {
      return postData(API_ENDPOINTS.CUSTOMER_MASTER.MASTER_REGIST, data, {
        Authorization: `Bearer ${token}`,
      });
    },
    onSuccess: () => {
      setIsEditing(false);
      navigate("/master/mscs03", {
        state: {
          // customerData: formDataRef.current, // 送信データそのまま
          customerData: { ...form.getValues(), corporate_number: customerData?.corporate_number ?? "" }, // 最新フォームデータ
        },
      });
      saveSuccessToast();
    },
    onError: (error: any) => {
      setErrorMessage(error.data?.message);
      // toast({
      //   description: error.message,
      //   variant: "destructive",
      // });
    },
  });
  // 登録処理
  const handleConfirmSubmit = async () => {
    setIsLoading(true);
    setErrorMessage("");
    form.clearErrors();

    // バリデーションをトリガー
    const isValid = await form.trigger();
    if (!isValid) {
      // setErrorMessage(Messages.VALIDATION.form.error);
      setIsLoading(false);
      return;
    }
    generateCompanyAddress(form, prefectureList); // 会社住所自動生成
    const values = form.getValues();
    // const sanitizeOptionalField = (value?: string | null) => {
    //   if (typeof value !== "string") return undefined;
    //   const trimmed = value.trim();
    //   return trimmed === "" ? undefined : trimmed;
    // };

    const requestData = {
      user_id: userId,
      company_name: values.company_name,
      company_name_kana: values.company_name_kana,
      corporate_number: values.corporate_number,
      company_address_prefecture: values.company_address_prefecture,
      company_address_city: values.company_address_city,
      company_address: values.company_address,
      usage_type: "1",
      office_info_list: (values.office_info_list ?? []).map((office, index) => {
        const { ep_office_code, ep_customer_number, ...restOffice } = office;
        const sanitizedOffice = {
          org_id: orgId,
          ...restOffice,
          ep_office_code: ep_office_code ? ep_office_code : null,
          ep_customer_number: ep_customer_number ? ep_customer_number : null,
          // building_id: generateBuildingId(index),
        };
        return sanitizedOffice;
      }),
    };

    mutation.mutate(requestData);
    setIsLoading(false);
  };

  //同意書取得経路変更時の同意書取得組織の入力クリア
  useEffect(() => {
    fields.forEach((field, index) => {
      const subscription = form.watch((value, { name }) => {
        if (name === `office_info_list.${index}.agreement_category`) {
          form.setValue(`office_info_list.${index}.agreement_org`, "");
          form.setValue(`office_info_list.${index}.org_name`, "");
        }
      });

      return () => {
        subscription.unsubscribe?.();
      };
    });
  }, [fields, form]);

  // パンくず定義
  const breadcrumbItems = [
    { title: "お客さまマスタ登録・管理", link: "/master/mscs01" },
    { title: customerData?.company_name ?? "", link: "" },
  ];

  return (
    <MasterLayout
      breadcrumbItems={breadcrumbItems}
      showRegisterButton={isEditing}
      showCancelButton={isEditing}
      processClick={handleConfirmSubmit}
      registerConfirmDescription={"この入力内容で登録します。よろしいですか？\n・供給地点特定番号を入力した場合、内容が正しいか確認してください。\n・供給地点特定番号が異なる場合、別のお客さまの電力30分値が紐づく可能性があります。"}
      registerConfirmClassName="w-[600px] h-auto max-w-[calc(100vw-2rem)] whitespace-pre-line"
      onCancelClick={() => {
        setIsEditing(false);
        if (initialFormData) {
          form.reset(initialFormData);
        }
        form.clearErrors();
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
        <form className="grid gap-4 relative" noValidate onSubmit={(e) => e.preventDefault()}>
          {isEpAdmin && !isNewMode && !isEditing && (
            <Button
              variant="primary"
              size="third"
              onClick={() => {
                if (!isEditing) {
                  setIsEditing(true);
                  setNewOfficeIndex(null);
                }
              }}
              disabled={isEditing}
              className="absolute right-0"
              type="button"
            >
              編集
            </Button>
          )}
          <Accordion type="multiple" className="pl-3" defaultValue={["item-1", "item-2", "item-3"]}>
            {/* 基本情報セクション */}
            <AccordionItem value="item-1">
              <AccordionTrigger className="flex-row-reverse justify-end gap-2">
                <h3 className="text-lg font-bold pt-5">お客さま基本情報</h3>
              </AccordionTrigger>
              <AccordionContent>
                <Card>
                  <CardHeader>
                    <CardTitle>お客さま基本情報</CardTitle>
                  </CardHeader>
                  <CardContent className="grid pl-20 pr-20">
                    <MasterFormField
                      control={form.control}
                      name="company_name"
                      label="お客さま名"
                      required={isEditing}
                      placeholder="会社名"
                      triggerValidation={(name) => form.trigger(name)}
                      isEditing={isEditing}
                      disabled={!isEditing}
                      className="w-2/3"
                    />
                    <MasterFormField
                      control={form.control}
                      name="company_name_kana"
                      label="お客さま名（フリガナ）"
                      required={isEditing}
                      placeholder="ふりがな"
                      triggerValidation={(name) => form.trigger(name)}
                      isEditing={isEditing}
                      disabled={!isEditing}
                      className="w-2/3"
                    />
                    <MasterFormField
                      control={form.control}
                      name="corporate_number"
                      label="法人番号"
                      required={isEditing}
                      placeholder="13桁数字"
                      type="text"
                      triggerValidation={(name) => form.trigger(name)}
                      isEditing={isEditing}
                      disabled={true} // 法人番号は編集不可
                      className="w-2/3"
                    />
                    <div className={`flex items-center gap-1`}>
                      {isEditing ? (
                        <>
                          <MasterFormField
                            control={form.control}
                            name="company_address_prefecture"
                            label="本社所在地（都道府県）"
                            required={isEditing}
                            options={prefectureList}
                            triggerValidation={(name) => form.trigger(name)}
                            isEditing={isEditing}
                            className="w-1/3"
                          />
                          <MasterFormField
                            control={form.control}
                            name="company_address_city"
                            label="本社所在地（市区町村以降）"
                            required={isEditing}
                            triggerValidation={(name) => form.trigger(name)}
                            isEditing={isEditing}
                            className="w-1/3"
                          />
                        </>
                      ) : (
                        <MasterFormField
                          key={form.watch("company_address_prefecture")}
                          control={form.control}
                          name="company_address"
                          label="本社所在地"
                          triggerValidation={(name) => form.trigger(name)}
                          isEditing={isEditing}
                          className="w-2/3"
                        />
                      )}
                    </div>
                  </CardContent>
                </Card>
              </AccordionContent>
            </AccordionItem>

            {/* 同意書取得経路セクション*/}
            {!isNewRef && fields.length > 0 && (
              <AccordionItem value="item-2">
                <AccordionTrigger className="flex-row-reverse justify-end gap-2">
                  <h3 className="text-lg font-bold">同意書取得経路</h3>
                </AccordionTrigger>
                <AccordionContent>
                  <Card>
                    <CardHeader>
                      <CardTitle>同意書取得経路</CardTitle>
                      <p className="text-sm text-gray-500 mt-2">
                        同じ同意書取得経路が複数の拠点で選択されている場合、経路名は一度だけ表示されます。
                      </p>
                    </CardHeader>
                    <CardContent className="grid gap-4">
                      {(() => {
                        // 同意書取得経路の重複排除＆序號付与ロジック
                        const getUniqueAgreementCategories = () => {
                          if (!fields.length || !aggreeCategoryList) return [];

                          const categoryMap = new Map();
                          let order = 1;

                          // 修正: インデックスを使用して実際の値を取得
                          fields.forEach((_, index) => {
                            const code = form.getValues(`office_info_list.${index}.agreement_category`);
                            if (code && !categoryMap.has(code)) {
                              categoryMap.set(code, order++);
                            }
                          });

                          return Array.from(categoryMap.entries()).map(([code, order]) => {
                            const category = aggreeCategoryList.find((item) => item.id === code);
                            return {
                              name: category ? category.name : `不明なコード: ${code}`,
                              order,
                            };
                          });
                        };

                        const categories = getUniqueAgreementCategories();

                        if (categories.length === 0) {
                          return <div className="text-sm py-4 text-gray-500">同意書取得経路が選択されていません。</div>;
                        }

                        return categories.map((category) => (
                          <div key={category.order} className="flex items-start gap-4 p-3 border-b">
                            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-green-50">
                              <span className="font-medium text-black-500">{category.order}</span>
                            </div>
                            <div className="flex-1">
                              <p className="font-medium text-gray-700 mb-1">
                                同意書取得経路{getCircledNumber(category.order)}
                              </p>
                              <p className="text-gray-900 font-medium">{category.name}</p>
                            </div>
                          </div>
                        ));
                      })()}
                    </CardContent>
                  </Card>
                </AccordionContent>
              </AccordionItem>
            )}

            {/* 建物・拠点情報セクション */}
            <AccordionItem value="item-3">
              <AccordionTrigger className="flex-row-reverse justify-end gap-2">
                <h3 className="text-lg font-bold">拠点情報</h3>
              </AccordionTrigger>

              {!isEditing && (
                <div className="mt-2 mb-2">
                  <Button
                    variant="primary"
                    size="third"
                    onClick={() => navigate("/master/msbd01", { state: { customerData: customerData } })}
                    disabled={isEditing}
                    // className="absolute right-0"
                    type="button"
                  >
                    拠点マスタ管理
                  </Button>
                </div>
              )}

              <AccordionContent className="pb-8">
                {fields.map((field, index) => (
                  <Card key={field.id}>
                    <CardHeader className="flex flex-row justify-between items-end w-full">
                      <CardTitle className="text-lg">拠点{getCircledNumber(index + 1)}</CardTitle>
                      <div className="flex">
                        {isEditing && (
                          <Button
                            onClick={() => deleteOffice(index)}
                            variant="lineerror"
                            size="lineerror"
                            className="w-20"
                            type="button"
                          >
                            削除
                          </Button>
                        )}
                      </div>
                    </CardHeader>

                    <CardContent className="grid pl-20 pr-20">
                      <MasterFormField
                        control={form.control}
                        // name={`office_info_list.${index}.building_name`}
                        name={`office_info_list.${index}.location_identifier_name`}
                        label="拠点名"
                        required={isEditing}
                        placeholder="xx拠点"
                        triggerValidation={(name) => form.trigger(name)}
                        isEditing={isEditing}
                        disabled={!isEditing}
                        className="w-2/3"
                      />
                      <div className={`flex items-center gap-1`}>
                        {isEditing ? (
                          <>
                            <MasterFormField
                              control={form.control}
                              name={`office_info_list.${index}.building_address_prefecture`}
                              label="拠点所在地（都道府県）"
                              required={isEditing}
                              options={prefectureList}
                              triggerValidation={(name) => form.trigger(name)}
                              isEditing={isEditing}
                              className="w-1/3"
                            />
                            <MasterFormField
                              control={form.control}
                              name={`office_info_list.${index}.building_address_city`}
                              required={isEditing}
                              label="拠点所在地（市区町村以降）"
                              placeholder="xx市xx区"
                              triggerValidation={(name) => form.trigger(name)}
                              isEditing={isEditing}
                              className="w-1/3"
                            />
                          </>
                        ) : (
                          <MasterFormField
                            key={form.watch(`office_info_list.${index}.building_address_prefecture`)}
                            control={form.control}
                            name={`office_info_list.${index}.building_address_prefecture`}
                            label="拠点所在地"
                            isEditing={isEditing}
                            className="w-2/3"
                            renderCustom={(field) => {
                              const prefectureName =
                                (prefectureList ?? []).find((opt) => opt.id === field.value)?.name ?? field.value;
                              const cityName = form.watch(`office_info_list.${index}.building_address_city`) ?? "";

                              return <span>{prefectureName + cityName}</span>;
                            }}
                          />
                        )}
                      </div>
                      <MasterFormField
                        control={form.control}
                        name={`office_info_list.${index}.ep_office_code`}
                        label="事業所コード"
                        // required={isEditing}
                        placeholder="半角数字3桁"
                        triggerValidation={(name) => form.trigger(name)}
                        isEditing={isEditing}
                        disabled={!isEditing}
                        className="w-2/3"
                      />
                      <MasterFormField
                        control={form.control}
                        name={`office_info_list.${index}.ep_customer_number`}
                        label="お客さま番号"
                        // required={isEditing}
                        placeholder="半角数字13桁"
                        triggerValidation={(name) => form.trigger(name)}
                        isEditing={isEditing}
                        disabled={!isEditing}
                        className="w-2/3"
                      />
                      <MasterFormField
                        control={form.control}
                        name={`office_info_list.${index}.supply_point_number`}
                        label="供給地点特定番号"
                        // required={isEditing}
                        placeholder="半角数字22桁"
                        triggerValidation={(name) => form.trigger(name)}
                        isEditing={isEditing}
                        disabled={!isEditing}
                        className="w-2/3"
                      />
                      <MasterFormField
                        control={form.control}
                        name={`office_info_list.${index}.agreement_category`}
                        label={`同意書取得経路${getCircledNumber(index + 1)}`}
                        required={isEditing}
                        options={aggreeCategoryList}
                        triggerValidation={(name) => form.trigger(name)}
                        isEditing={isEditing}
                        disabled={form.getValues(`office_info_list.${index}.isFromApi`) === true}
                        className="w-2/3"
                      />
                      <MasterFormField
                        name={`office_info_list.${index}.agreement_org`}
                        control={form.control}
                        label="同意書取得組織"
                        required={isEditing}
                        isEditing={isEditing}
                        className="w-2/3"
                        renderCustom={(field) => {
                          const agreementOrg = form.watch(`office_info_list.${index}.agreement_org`);
                          const orgName = form.watch(`office_info_list.${index}.org_name`);
                          const displayOrgName = agreementOrg === "dummy" ? "同意書未取得" : orgName ?? "";
                          const agreementCategory = form.watch(`office_info_list.${index}.agreement_category`);
                          const hasError = !!form.formState.errors?.office_info_list?.[index]?.agreement_org;

                          // 編集中かつagreementCategoryがある場合のみ活性
                          const isActive = isEditing && !!agreementCategory;
                          if (!isEditing) {
                            return <span className="block leading-[24px]">{displayOrgName}</span>;
                          }

                          return (
                            <div
                              className="flex items-center rounded-md gap-2 w-full min-h-[33px]"
                              tabIndex={-1}
                              onBlur={() => {
                                field.onBlur();
                                form.trigger(`office_info_list.${index}.agreement_org`);
                              }}
                            >
                              <div
                                className={clsx(
                                  "flex-1 flex items-center gap-3 rounded-md px-3 py-2 min-h-[33px]",
                                  isEditing
                                    ? isActive
                                      ? hasError
                                        ? "input-text-error"
                                        : "border border-[#98A2B3] shadow-[0px_1px_2px_rgba(16,24,40,0.05)]"
                                      : "border-none bg-gray-50 text-gray-400 shadow-none pl-1"
                                    : "border-none bg-transparent shadow-none pl-1",
                                )}
                              >
                                <span>{displayOrgName}</span>
                              </div>

                              {/* ボタン表示 */}
                              {isActive && (
                                <button
                                  type="button"
                                  onClick={() => setOpenAgreementOrgDialogIndex(index)}
                                  className="border w-20 h-10 rounded flex items-center justify-center whitespace-nowrap text-teal-600 border-teal-600 cursor-pointer"
                                >
                                  選択
                                </button>
                              )}
                            </div>
                          );
                        }}
                      />

                      <div className="w-[400px]">
                        <Dialog
                          open={openAgreementOrgDialogIndex === index}
                          onOpenChange={(open) => !open && setOpenAgreementOrgDialogIndex(null)}
                        >
                          <DialogTrigger hidden />
                          <DialogContent className=" w-[40%] h-[530px] flex flex-col justify-start">
                            <DialogTitle className="h-8">同意書取得組織の選択</DialogTitle>
                            <DialogDescription hidden />
                            <SearchOrganization
                              agreementCategory={form.getValues(`office_info_list.${index}.agreement_category`)}
                              onSelect={(org) => {
                                form.setValue(`office_info_list.${index}.agreement_org`, org.id, {
                                  shouldValidate: true,
                                });
                                form.setValue(`office_info_list.${index}.org_name`, org.name);
                                setOpenAgreementOrgDialogIndex(null);
                              }}
                            />
                          </DialogContent>
                        </Dialog>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </AccordionContent>

              {isEditing && (
                <div className="mb-24 mt-8">
                  <Button onClick={addOffice} variant="third" type="button">
                    拠点追加
                  </Button>
                </div>
              )}
            </AccordionItem>
          </Accordion>
        </form>
      </Form>
    </MasterLayout>
  );
}
