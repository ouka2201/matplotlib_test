import { zodResolver } from "@hookform/resolvers/zod";
// import { MetaFunction } from "@remix-run/node";
import { useSearchParams } from "@remix-run/react";
import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import ErrorHint from "~/components/common/error-hint";
import MasterFormField from "~/components/common/master-form-field";
import MasterLayout from "~/components/layout/master-layout";
import { SessionAuthorityInfo, useSession } from "~/components/layout/session-provider";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "~/components/ui/accordion";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Form } from "~/components/ui/form";
import { useToast } from "~/components/ui/use-toast";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { Messages } from "~/constants/messages/message";
import { useConsentRoutes } from "~/hooks/useConsentRoutes";
import { useScrollToError } from "~/hooks/useScrollToError";
import { getCircledNumber } from "~/lib/utils";
import { msmgSchema } from "~/lib/validations/msmg";
import { CdNmOption } from "~/types/screen/master/mscs/mscsType";
import { getData, postData } from "../lib/fetch";

interface ContactPersonListItem {
  user_id: string;
  org_id: string;
  org_name: string;
  user_name: string;
  agreement_category: string;
  consent_receipt_date: string;
  org_type_code: string;
  user_role: string;
  email_address?: string;
}

interface CompanyInfo {
  company_name: string;
  corporate_number: string;
  company_address: string;
}

const ContactPersonDetail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const corporateNumber = searchParams.get("corporate_number") ?? "";
  const [companyInfo, setCompanyInfo] = useState<CompanyInfo | null>(null);
  const [initialFormData, setInitialFormData] = useState<z.infer<typeof msmgSchema> | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [error, setError] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(error);
  const [aggreeCategoryList, setAggreeCategoryList] = useState<CdNmOption[]>([]);
  const { session } = useSession();
  const { saveSuccessToast } = useToast();
  const [authorityInfo, setAuthorityInfo] = useState<SessionAuthorityInfo | null>(session?.authorityInfo ?? null);
  const [token, setToken] = useState<string | null>(session?.token ?? null);
  const form = useForm<z.infer<typeof msmgSchema>>({
    resolver: zodResolver(msmgSchema),
    defaultValues: {
      company_name: "",
      corporate_number: "",
      company_address: "",
      contact_person_list: [],
    },
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
        setAuthorityInfo(JSON.parse(sessionData).authorityInfo);
      }
    }
  }, [session]);

  // 同意書取得経路取得
  const routes = useConsentRoutes(token, corporateNumber, authorityInfo?.org_id);

  useEffect(() => {
    setAggreeCategoryList(routes);
  }, [routes, setAggreeCategoryList]);

  // 担当者情報詳細取得
  useEffect(() => {
    if (!corporateNumber) {
      setError(Messages.VALIDATION.corporate_number.required);
      return;
    }

    (async () => {
      try {
        const url = `${API_ENDPOINTS.CONTACT_PERSON.API_CONTACT_PERSON_DETAIL}?corporate_number=${corporateNumber}`;
        const response: [CompanyInfo, ContactPersonListItem[]] = await getData(url, {
          Authorization: `Bearer ${token}`,
        });
        if (!response || response.length < 2) throw new Error(Messages.VALIDATION.api.error);

        sessionStorage.setItem("contactPersonDetail", JSON.stringify(response));
        const [companyData, contactPersons] = response;
        const formattedPersons = contactPersons.map((person) => ({
          ...person,
          consent_receipt_date: person.consent_receipt_date ?? "",
          org_type_code: person.org_type_code ?? "",
          user_role: person.user_role ?? "",
          email_address: person.email_address ?? "",
        }));

        setCompanyInfo(companyData);
        const initialValues = {
          ...companyData,
          contact_person_list: formattedPersons,
        };

        form.reset(initialValues);
        setInitialFormData(initialValues);
      } catch (err) {
        console.error(err);
        setError(Messages.VALIDATION.api.corp_search_error);
      }
    })();
  }, [corporateNumber, form, token]);

  // メールアドレス変更時のユーザー情報取得
  const fetchUserInfoByEmailAddress = async (email_address: string) => {
    try {
      const url = API_ENDPOINTS.CONTACT_PERSON.API_CONTACT_PERSON_ADD_USER_INQUIRY;
      const response = await postData(url, { email_address }, { Authorization: `Bearer ${token}` });
      return Array.isArray(response) ? response[0] : null;
    } catch {
      return null;
    }
  };

  const handleChangeEmailAddress = (index: number, email: string) => {
    const trimmed = email.trim();
    setError("");
    // 入力値反映（dirty/validate を付けて最新状態にする）
    form.setValue(`contact_person_list.${index}.email_address`, trimmed, {
      shouldDirty: true,
      // shouldValidate: true,
      shouldValidate: false,
    });

    // 入力し直し時に以前のエラーを消す
    form.clearErrors(`contact_person_list.${index}.email_address`);
    if (trimmed === "") {
      form.setValue(`contact_person_list.${index}.org_id`, "", { shouldDirty: true });
      form.setValue(`contact_person_list.${index}.user_id`, "", { shouldDirty: true });
      form.setValue(`contact_person_list.${index}.org_name`, "", { shouldDirty: true });
      form.setValue(`contact_person_list.${index}.user_name`, "", { shouldDirty: true });
      form.setValue(`contact_person_list.${index}.org_type_code`, "", { shouldDirty: true });
      form.setValue(`contact_person_list.${index}.user_role`, "", { shouldDirty: true });
      return;
    }
  };

  const handleBlurEmailAddress = async (index: number) => {
    const email = (form.getValues(`contact_person_list.${index}.email_address`) ?? "").trim();

    // 必須・形式チェック
    const ok = await form.trigger(`contact_person_list.${index}.email_address`);
    if (!ok || email === "") return;

    const info = await fetchUserInfoByEmailAddress(email);

    if (!info) {
      form.setValue(`contact_person_list.${index}.org_id`, "", { shouldDirty: true, shouldValidate: true });
      form.setValue(`contact_person_list.${index}.user_id`, "", { shouldDirty: true, shouldValidate: true });
      form.setValue(`contact_person_list.${index}.org_name`, "", { shouldDirty: true });
      form.setValue(`contact_person_list.${index}.user_name`, "", { shouldDirty: true });
      form.setValue(`contact_person_list.${index}.org_type_code`, "", { shouldDirty: true });
      form.setValue(`contact_person_list.${index}.user_role`, "", { shouldDirty: true });

      form.setError(`contact_person_list.${index}.email_address`, {
        type: "manual",
        message: "ユーザーが見つかりません。",
      });
      return;
    }

    // 見つかった場合
    form.clearErrors(`contact_person_list.${index}.email_address`);
    setError("");

    form.setValue(`contact_person_list.${index}.org_id`, info.org_id ?? "", { shouldDirty: true, shouldValidate: true });
    form.setValue(`contact_person_list.${index}.user_id`, info.user_id ?? "", { shouldDirty: true, shouldValidate: true });
    form.setValue(`contact_person_list.${index}.org_name`, info.org_name ?? "", { shouldDirty: true });
    form.setValue(`contact_person_list.${index}.user_name`, info.user_name ?? "", { shouldDirty: true });
    form.setValue(`contact_person_list.${index}.org_type_code`, info.org_type_code ?? "", { shouldDirty: true });
    form.setValue(`contact_person_list.${index}.user_role`, info.user_role ?? "", { shouldDirty: true });
  };

  // 担当者追加
  const handleAddContactPerson = () => {
    const contactPersonList = form.getValues("contact_person_list") || [];
    if (contactPersonList.length >= 10) return;
    form.setValue("contact_person_list", [
      ...contactPersonList,
      {
        user_id: "",
        email_address: "",
        org_name: "",
        user_name: "",
        agreement_category: "",
        consent_receipt_date: "",
        org_id: "",
        org_type_code: "",
        user_role: "",
      },
    ]);
  };

  // 担当者削除
  const handleDeleteContactPerson = (index: number) => {
    const currentValues = form.getValues("contact_person_list") ?? [];
    const newValues = currentValues.filter((_, i) => i !== index);
    form.setValue("contact_person_list", newValues, {
      shouldDirty: true,
      shouldValidate: false,
    });

    // 削除後に全体エラー表示を消したい場合
    setError("");
  };

  // 拠点マスタで同意書取得組織として登録されている銀行ユーザーかをチェック
  const validateAgreementOrgBankUser = async () => {

    // フォームから担当者リストを取得
    const list = form.getValues("contact_person_list") ?? [];

    // 地銀ユーザーのorg_idを抽出
    const bnkOrgIds = list
      .filter(item => item.org_id?.slice(0, 3) === "BNK")
      .map(item => item.org_id);

    if (bnkOrgIds.length > 0) {
      // リクエストパラメータを構築
      const requestParams = {
        corporate_number: corporateNumber,
        org_id: bnkOrgIds,
      };

      try {
        const result = await postData("/api/contact-person/agreementuserget", requestParams);
        // データが存在するか確認
        if (result && Array.isArray(result) && result.length > 0) {
          return { ok: true as const };
        } else {
          return {
            ok: false as const,
            message: "金融機関の営業担当は同意書取得組織として登録されている組織のユーザーのみ登録可能です。"
          };
        }
      } catch {
        return null;
      }
    }
    return { ok: true as const };
  };

  // 同意書取得経路ごとに、同一ユーザー（user_id）の重複登録を禁止
  const validateNoDuplicateAssigneePerRoute = () => {
    const list = form.getValues("contact_person_list") ?? [];

    // user_id と agreement_category の両方が存在するものだけを対象にする
    const normalized = list
      .map((p, idx) => ({
        idx,
        user_id: (p.user_id ?? "").trim(),
        agreement_category: (p.agreement_category ?? "").trim(),
      }))
      .filter((x) => x.user_id && x.agreement_category);

    const keyToIndexes = new Map<string, number[]>();

    for (const item of normalized) {
      const key = `${item.agreement_category}__${item.user_id}`;
      const arr = keyToIndexes.get(key) ?? [];
      arr.push(item.idx);
      keyToIndexes.set(key, arr);
    }

    // 重複があるかチェック
    for (const [, idxs] of keyToIndexes) {
      if (idxs.length >= 2) {
        return {
          ok: false as const,
          message: "同一の担当者を重複して登録することはできません。",
          duplicateIndexes: idxs,
        };
      }
    }

    return { ok: true as const };
  };

  const validateAllEmailsExist = async () => {
    const list = form.getValues("contact_person_list") ?? [];
    for (let i = 0; i < list.length; i++) {
      await handleBlurEmailAddress(i);
    }
  };

  const hasAnyEmailExistError = () => {
    const list = form.getValues("contact_person_list") ?? [];
    return list.some((_, i) => {
      const st = form.getFieldState(`contact_person_list.${i}.email_address`, form.formState);
      return !!st.error && st.error.message === "ユーザーが見つかりません。";
    });
  };

  const handleConfirmClick = async () => {
    setError("");
    // const isValid = await form.trigger();
    // if (!isValid) {
    //   setError(Messages.CONFIRM_ERROR_ITEMS);
    //   return;
    // }
    await form.trigger();
    await validateAllEmailsExist();
    const schemaInvalid = !form.formState.isValid;
    const emailInvalid = hasAnyEmailExistError();

    if (schemaInvalid || emailInvalid) {
      setError(Messages.CONFIRM_ERROR_ITEMS);
      return;
    }

    const dupCheck = validateNoDuplicateAssigneePerRoute();
    if (!dupCheck.ok) {
      setError(dupCheck.message);
      return;
    }

    const agreementCheck = await validateAgreementOrgBankUser();
    if (!agreementCheck?.ok) {
      setError(agreementCheck?.message ?? "");
      return;
    }

    handleConfirmRegister();
  };

  // 登録処理
  const handleConfirmRegister = form.handleSubmit(async (data) => {
    setError("");
    const stafflist = (data.contact_person_list ?? []).map((p) => ({
      user_id: p.user_id,
      agreement_category: p.agreement_category,
      consent_receipt_date: p.consent_receipt_date?.replace(/\//g, "-"),
      org_id: p.org_id,
    }));

    try {
      await postData(
        API_ENDPOINTS.CONTACT_PERSON.API_CONTACT_PERSON_UPDATE,
        {
          corporate_number: data.corporate_number,
          stafflist,
        },
        { Authorization: `Bearer ${token}` },
      );

      errorTopRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      const formattedConsentReceiptDate = data.contact_person_list?.map((person) => ({
        ...person,
        consent_receipt_date: person.consent_receipt_date ? person.consent_receipt_date.replace(/-/g, "/") : "",
      }));

      form.reset({
        ...data,
        contact_person_list: formattedConsentReceiptDate,
      });

      saveSuccessToast();
      setIsEditing(false);
    } catch (e) {
      console.error(e);
      setError(Messages.REGISTER_ERROR);
    }
  });

  const breadcrumbItems = [
    { title: "営業担当登録・管理", link: "/master/msmg01" },
    { title: companyInfo?.company_name ?? "", link: "" },
  ];

  return (
    <MasterLayout
      breadcrumbItems={breadcrumbItems}
      processClick={handleConfirmClick}
      isEditing={isEditing}
      showRegisterButton={isEditing}
      showCancelButton={isEditing}
      onCancelClick={() => {
        setIsEditing(false);
        if (initialFormData) {
          form.reset(initialFormData);
        }
        form.clearErrors();
        setError("");
      }}
      footerType="default"
    >
      <div className="grid gap-4">
        <div className="pl-3">
          <Accordion type="multiple" className="pl-3" defaultValue={["item-1", "item-2"]}>
            <AccordionItem value="item-1">
              <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />
              <div
                ref={errorTopRef as React.RefObject<HTMLDivElement>}
                className="flex items-start gap-4 w-4/5 mt-5 mb-5 flex-shrink-0 scroll-mt-[300px]"
              >
                <ErrorHint
                  // title="エラー内容の詳細"
                  message={error}
                  className="flex-1"
                  bodyClassName="py-4"
                />
              </div>
              <AccordionTrigger className="flex-row-reverse justify-end gap-2">
                <h3 className="text-lg font-bold">お客さま基本情報</h3>
              </AccordionTrigger>
              <AccordionContent>
                <Card>
                  <CardHeader>
                    <CardTitle>お客さま基本情報</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <MasterFormField
                      control={form.control}
                      name="company_name"
                      label="お客さま名"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                      className="w-2/3"
                    />
                    <MasterFormField
                      control={form.control}
                      name="corporate_number"
                      label="法人番号"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                      className="w-2/3"
                    />
                    <MasterFormField
                      control={form.control}
                      name="company_address"
                      label="本社所在地"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                      className="w-2/3"
                    />
                  </CardContent>
                </Card>
              </AccordionContent>
            </AccordionItem>

            <Form {...form}>
              <form className="grid gap-4 relative" onSubmit={(e) => e.preventDefault()} noValidate>
                {!isEditing && (
                  <Button
                    variant="primary"
                    size="third"
                    onClick={() => {
                      if (!isEditing) {
                        setIsEditing(true);
                      }
                    }}
                    disabled={isEditing}
                    className="absolute top-[12px] right-5"
                    type="button"
                  >
                    編集
                  </Button>
                )}
                <AccordionItem value="item-2">
                  <AccordionTrigger className="flex-row-reverse justify-end gap-2">
                    <h3 className="text-lg font-bold">営業担当</h3>
                  </AccordionTrigger>
                  <AccordionContent className="pb-20">
                    {form.watch("contact_person_list")?.map((_, index) => (
                      <Card key={index}>
                        <CardHeader className="flex flex-row justify-between items-end w-full">
                          <CardTitle>営業担当{getCircledNumber(index + 1)}</CardTitle>

                          {isEditing && (
                            <Button
                              onClick={() => handleDeleteContactPerson(index)}
                              variant="lineerror"
                              size="lineerror"
                              className="w-20"
                              type="button"
                            >
                              削除
                            </Button>
                          )}
                        </CardHeader>
                        <CardContent>
                          <MasterFormField
                            control={form.control}
                            // name={`contact_person_list.${index}.user_id`}
                            name={`contact_person_list.${index}.email_address`}
                            label="メールアドレス"
                            placeholder="xx@xx.jp"
                            required
                            triggerValidation={(name) => void form.trigger(name)}
                            isEditing={isEditing}
                            onChange={(
                              e: React.ChangeEvent<HTMLInputElement>,
                            ) => handleChangeEmailAddress(index, e.target.value)}
                            onBlur={() => void handleBlurEmailAddress(index)}
                            className={isEditing ? "w-1/3" : "w-full"}
                          />
                          <MasterFormField
                            control={form.control}
                            name={`contact_person_list.${index}.org_name`}
                            label="組織名"
                            isEditing={isEditing}
                            disabled
                            className={isEditing ? "w-1/3" : "w-full"}
                          />
                          <MasterFormField
                            control={form.control}
                            name={`contact_person_list.${index}.user_name`}
                            label="氏名"
                            isEditing={isEditing}
                            disabled
                            className={isEditing ? "w-1/3" : "w-full"}
                          />
                          <MasterFormField
                            control={form.control}
                            name={`contact_person_list.${index}.agreement_category`}
                            label="同意書取得経路"
                            required
                            type="select"
                            options={aggreeCategoryList}
                            triggerValidation={(name) => form.trigger(name)}
                            isEditing={isEditing}
                            className={isEditing ? "w-1/3" : "w-full"}
                          />
                          <MasterFormField
                            control={form.control}
                            name={`contact_person_list.${index}.consent_receipt_date`}
                            label="同意書受領日"
                            required={(() => {
                              const orgTypeCode = form.watch(`contact_person_list.${index}.org_type_code`);
                              const userRole = form.watch(`contact_person_list.${index}.user_role`);

                              // 本店・親組織管理者、支店・管理者、支店・一般の場合は入力必須
                              return (
                                (orgTypeCode === "02" && userRole === "9") ||
                                (orgTypeCode === "03" && (userRole === "0" || userRole === "1"))
                              );
                            })()}
                            type="calendar"
                            isEditing={isEditing}
                            allowFutureDates={false}
                            specifiedDate={{ after: new Date() }}
                            className={isEditing ? "w-1/3" : "w-full"}
                          />
                        </CardContent>
                      </Card>
                    ))}

                    <Button
                      variant="third"
                      // iconLeft={<Plus />}
                      className="mt-4"
                      disabled={!isEditing || (form.watch("contact_person_list")?.length ?? 0) >= 10}
                      onClick={handleAddContactPerson}
                    >
                      営業担当追加
                    </Button>
                  </AccordionContent>
                </AccordionItem>
              </form>
            </Form>
          </Accordion>
        </div>
      </div>
    </MasterLayout>
  );
};

export default ContactPersonDetail;
