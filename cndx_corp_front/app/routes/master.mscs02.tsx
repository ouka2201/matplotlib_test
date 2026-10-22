import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { LoadingSpinner } from "~/components/common/loadingSpinner";
import MasterFormField from "~/components/common/master-form-field";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import MasterLayout from "~/components/layout/master-layout";
import { Accordion, AccordionContent, AccordionItem } from "~/components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Form } from "~/components/ui/form";
import { useToast } from "~/components/ui/use-toast";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { useScrollToError } from "~/hooks/useScrollToError";
import { postData } from "~/lib/fetch";
import { mscsSchema } from "~/lib/validations/mscs";
import { CdNmOption, CustomerCompany, mscsInputs } from "~/types/screen/master/mscs/mscsType";
import { Icon, Text } from "../components/import";

// パンくず情報
const breadcrumbItems = [
  { title: "お客さまマスタ登録・管理", link: "/master/mscs01" },
  { title: "新規登録", link: "" },
];

export default function CompanyBasicRegist() {
  // const { session, clearSession } = useSession();
  const [prefectureList, setPrefectureList] = useState<CdNmOption[]>();
  const [isLoading, setIsLoading] = useState(false);
  const [, setShowConfirm] = useState(false);
  const [token] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      return sessionData ? JSON.parse(sessionData).token : null;
    }
    return null;
  });
  // エラーメッセージ
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);

  // フォームデータを保持するためのrefを追加
  const formDataRef = useRef<CustomerCompany | null>(null);
  const { saveSuccessToast } = useToast();
  const navigate = useNavigate();

  // react-hook-form
  const form = useForm<mscsInputs>({
    resolver: zodResolver(mscsSchema),
    defaultValues: {
      company_name: "",
      company_name_kana: "",
      corporate_number: "",
      company_address_prefecture: "",
      company_address_city: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: mscsInputs) => {
      return postData(API_ENDPOINTS.CUSTOMER_MASTER.MASTER_REGIST, data);
    },
    onSuccess: () => {
      if (formDataRef) {
        setTimeout(() => {
          navigate("/master/mscs03", {
            state: {
              customerData: formDataRef.current, // 送信データそのまま
              mode: "refer",
            },
          });
        }, 100);
      }
      saveSuccessToast();
      setIsLoading(false);
    },
    onError: (error: any) => {
      // clearSession()
      // if (error instanceof Error) {
      //   setErrorMessage(error.message);
      // } else {
      //   setErrorMessage("データの送信に失敗しました。");
      // }
      // toast({
      //   description: error.message,
      //   variant: "destructive",
      // });
      setErrorMessage(error.data?.message);
      setIsLoading(false);
    },
  });

  const submitData = async (data?: mscsInputs) => {
    if (data) {
      formDataRef.current = {
        ...data,
        user_id: sessionStorage.getItem("email") ?? "",
        usage_type: "0",
        office_info_list: [
          {
            org_id: "",
            agreement_category: "",
            building_name: "",
            building_address_prefecture: "",
            ep_office_code: "",
            building_address_city: "",
            ep_customer_number: "",
            supply_point_number: "",
            building_id: "",
            building_address: "",
            agreement_org: "",
          },
        ],
      };
    }

    if (formDataRef.current) {
      setIsLoading(true);
      try {
        mutation.mutate(formDataRef.current);
      } finally {
        setIsLoading(false);
        setShowConfirm(false);
      }
    }
  };

  // 都道府県マスタの取得
  useEffect(() => {
    let isCancelled = false;

    const fetchMaster = async () => {
      if (!token) return;
      const masterEntries = [{ name: "prefecture", params: {} as Record<string, string> }];
      try {
        const data = await getMasterDataForCondition(masterEntries, token);
        if (!isCancelled) {
          setPrefectureList(data["prefecture"] ?? []);
        }
      } catch (err: any) {
        if (!isCancelled) {
          console.error("マスタ取得エラー", err);
          // setErrorMessage(err instanceof Error ? err.message : "データの取得に失敗しました。");
          setErrorMessage(err.data?.message);
        }
      }
    };

    fetchMaster();

    return () => {
      isCancelled = true;
    };
  }, [token]);

  return (
    <MasterLayout
      breadcrumbItems={breadcrumbItems}
      showRegisterButton={true}
      showCancelButton={true}
      processClick={() => form.handleSubmit(submitData)()}
      onCancelClick={async () => {
        form.reset();
        navigate("/master/mscs01", {
          state: {
            customerData: formDataRef.current, // 送信データそのまま
            mode: "new",
          },
        });
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
      <div>
        {isLoading ? (
          <LoadingSpinner />
        ) : (
          <div>
            <Form {...form}>
              <form className="grid gap-4" onSubmit={form.handleSubmit(submitData)}>
                <Accordion type="multiple" className="pl-3" defaultValue={["item-1", "item-2", "item-3"]}>
                  <AccordionItem value="item-1">
                    <AccordionContent>
                      <Card className="">
                        <CardHeader>
                          <CardTitle>お客さま基本情報</CardTitle>
                        </CardHeader>
                        <CardContent className="flex flex-col gap-6">
                          <MasterFormField
                            control={form.control}
                            name="company_name"
                            label="お客さま名"
                            required
                            placeholder="xx株式会社"
                            triggerValidation={(name) => form.trigger(name)}
                            className="w-1/3"
                          />

                          <MasterFormField
                            control={form.control}
                            name="company_name_kana"
                            label="お客さま名（フリガナ）"
                            required
                            placeholder="xxカブシキガイシャ"
                            triggerValidation={(name) => form.trigger(name)}
                            className="w-1/3"
                          />

                          <MasterFormField
                            control={form.control}
                            name="corporate_number"
                            label="法人番号"
                            required
                            placeholder="半角数字13桁"
                            type="text"
                            triggerValidation={(name) => form.trigger(name)}
                            className="w-1/3"
                          />

                          <div className="flex items-center gap-6">
                            <MasterFormField
                              control={form.control}
                              name="company_address_prefecture"
                              label="本社所在地（都道府県）"
                              required
                              // placeholder="都道府県"
                              options={prefectureList}
                              className="w-1/3"
                            // className="w-1/4"
                            />

                            <MasterFormField
                              control={form.control}
                              name="company_address_city"
                              label="本社所在地（市区町村以降）"
                              required
                              placeholder="xx市xx区…"
                              // className="w-5/6"
                              triggerValidation={(name) => form.trigger(name)}
                              className="w-1/3"
                            />
                          </div>
                        </CardContent>
                      </Card>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </form>
            </Form>
          </div>
        )}
      </div>
    </MasterLayout>
  );
}
