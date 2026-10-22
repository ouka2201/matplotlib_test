import React, { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { Icons } from "~/components/icons";
import { Input } from "~/components/ui/input";
import { postData } from "~/lib/fetch";
import { CustomerCompany } from "~/types/screen/master/mscs/mscsType";
import { Button } from "../components/ui/button";
import { Messages } from "../constants/messages/message";
import "../styles/customLogin.css";
// import { PasswordInput } from "~/components/password-input";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Asterisk } from "lucide-react";
import { z } from "zod";
import BreadCrumb from "~/components/common/breadcrumb";
import { AlertModal } from "~/components/modal/alert-modal";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "~/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger } from "~/components/ui/select";
import { useToast } from "~/components/ui/use-toast";
import { mscsSchema } from "~/lib/validations/mscs";

type Inputs = z.infer<typeof mscsSchema>;

const CustomLogin: React.FC = () => {

  const [prefecture_namelist, set_prefecture_namelist] = useState<string[]>([]);
  const { saveSuccessToast } = useToast();
  
  // フォームデータを保持するためのrefを追加
  const formDataRef = useRef<CustomerCompany | null>(null);

  // react-hook-form
  const form = useForm<Inputs>({
    resolver: zodResolver(mscsSchema),
    defaultValues: {
      // user_id: "",
      company_name: "",
      company_name_kana: "",
      corporate_number: "",
      company_address_prefecture: "",
      company_address_city: "",
      // building_list: [],
      // usage_type:""
    },
  });

  const mutation = useMutation({
    mutationFn: (data: Inputs) => {
      return postData("/api/mst_manage/corpration/info", data);
    },
    onSuccess: () => {
      if (formDataRef) {
        setTimeout(() => {
          navigate("/master/mscs03", {
            state: {
              customerData: formDataRef.current, // 送信データそのまま
              mode: "new",
            },
          });
        }, 100);
      }
      saveSuccessToast();
    },
    onError: (error) => {
      toast({
        description: error.message,
        variant: "destructive",
      });
    },
  });

  async function submitData() {
    if (formDataRef.current) {
      formDataRef.current = {
        ...formDataRef.current,
        user_id: sessionStorage.getItem("email") ?? "",
        usage_type: "0",
        office_info_list: [{
          org_id: "組織ID", 
          agreement_category: "00",
          building_name: "",
          building_address_prefecture: "",
          building_address_city: "",
          ep_customer_number: "",
          supply_point_number: "",
          building_id: ""
        }]
      };
      mutation.mutate(formDataRef.current);
      setShowConfirm(false);
    }
  }

  useEffect(() => {
    if (typeof window !== "undefined") {
      // セッションから都道府県取得
      const data = sessionStorage.getItem("m_prefecture");
      if (data) {
        try {
          const list = JSON.parse(data);
          const names = list.map((p: { pref_nm: string }) => p.pref_nm);
          set_prefecture_namelist(names);
        } catch (err) {
          console.error("JSON parse error:", err);
        }
      }
      // const loadUser = async () => {
      //   const userData = await localforage.getItem("m_user");
      //   setUser(userData as User);
      // };
      // loadUser();
    }
  }, []);
  // useEffect(() => {
  //   const handlePopState = (event: PopStateEvent) => {
  //     // ブラウザの「戻る」操作を無効化する（たとえば、pushState の再実行や確認ダイアログの表示など
  //     alert("このページではブラウザの「戻る」は無効です。");
  //     window.history.pushState(null, "", window.location.href); // 現在のページを再度 push する
  //   };
  
  //   // 初期の push
  //   window.history.pushState(null, "", window.location.href);
  //   window.addEventListener("popstate", handlePopState);
  
  //   return () => {
  //     window.removeEventListener("popstate", handlePopState);
  //   };
  // }, []);
  
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [customer, setCustomer] = useState<CustomerCompany>({
    user_id: "",
    company_name: "",
    company_name_kana: "",
    corporate_number: "",
    company_address_prefecture: "",
    company_address_city: "",
    consentInfo: undefined,
    building_list: [],
    usage_type:""
  });
  const [buildingsErrors, setBuildingsErrors] = useState<BuildingErrors[]>([]);

  const validateBuildingInfo = (
    b: CustomerCompany
  ): { valid: boolean; errors: BuildingErrors } => {
    const errors: BuildingErrors = {};
    if (!b.company_name) errors.company_name = Messages.validation.required("お客さま名");
    if (!b.company_name_kana) errors.fulikana = Messages.validation.required("ふりかな");
    if (!b.corporate_number) {
      errors.corpNm = Messages.validation.required("法人番号");
    } else if (!/^[0-9]{13}$/.test(b.corporate_number)) {
      errors.corpNm = "法人番号は半角数字13桁で入力してください";
    }
    if (!b.company_address_prefecture) errors.addressInput = "選択ください";
    if (!b.company_address_city) errors.address = Messages.validation.required("所在地");

    const valid = Object.keys(errors).length === 0;
    return { valid, errors };
  };

  const [defaultErrors, setDefaultErrors] = useState<BuildingErrors>({});
  // const [customer, setDefaultBuilding] = useState<CustomerCompany>({
  //   id: 1,
  //   company_name: "",
  //   fulikana: "",
  //   corpNm: "",
  //   address: "",
  //   addressInput: "",
  // });
  const handleAllBuildingSubmit = () => {
    const basicInfoValidation = validateBuildingInfo(customer);

    // エラーがある項目を赤枠で表示
    setDefaultErrors(basicInfoValidation.errors);

    const allValid = basicInfoValidation.valid;

    if (!allValid) {
      alert("入力漏れがあります。データを登録できません");
      return;
    }
    // すべてのバリデーションを通過した場合、確認ダイアログを表示
    setShowConfirm(true);
  };

  const [showConfirm, setShowConfirm] = useState(false); // 確認ダイアログの表示有無を管理するステート

  
  const onSubmit = (data: Inputs) => {
    // フォームデータをrefに保存
    formDataRef.current = data;
    setShowConfirm(true);
  };

  const breadcrumbItems = [
    { title: "お客さま企業マスタ", link: "/master/mscs01" },
    { title: "新規登録", link:""}
  ];

  // ポップアップを閉じる
  const closePopup = () => setShowConfirm(false);

  return (
    <div>
      <BreadCrumb items={breadcrumbItems} />
      <div className="content-body mr-10">
      {errorMessage && (
        <div className="errorBox" style={{ width: "30%" }}>
          <div className="errorBoxLabel">
            {/* <Icon name="error-pink" /> */}
            {/* <Text content="エラー項目の詳細" color="white" weight="bold" /> */}
          </div>
          <div className="content-error-detail">
            {Array.isArray(errorMessage) ? (
              <ul>
                {errorMessage.map((message, index) => (
                  <li key={index}>{message}</li>
                ))}
              </ul>
            ) : (
              <div className="content-error-detail-text-main">
                {errorMessage}
              </div>
            )}
          </div>
        </div>
      )}
        <h3 className="section-title">▼基本情報</h3>
        <Form {...form}>
          <form className="grid gap-4" onSubmit={form.handleSubmit(onSubmit)}>
            <FormField
              control={form.control}
              name="company_name"
              render={({ field }) => (
                <FormItem className="flex items-center gap-2">
                  <FormLabel className={form.formState.errors.company_name ? "text-black" : "min-w-[150px] text-left"}>
                    お客さま名
                  </FormLabel>
                  <Asterisk className="h-4 w-4 text-red-500" />
                  <span className="inline-block p-2 bg-red-600 text-white rounded-md text-xs w-12">
                    必須
                  </span>
                  <FormControl className="flex-auto">
                    <Input type="text" placeholder="" autoComplete="name" required {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="company_name_kana"
              render={({ field }) => (
                <FormItem className="flex items-center gap-2">
                  <FormLabel className="min-w-[150px] text-left">お客さま名（ふりがな）</FormLabel>
                  <Asterisk className="h-4 w-4 text-red-500" />
                  <span className="inline-block p-2 bg-red-600 text-white rounded-md text-xs w-12">
                    必須
                  </span>
                  <FormControl className="flex-auto">
                    <Input type="text" placeholder="" autoComplete="name" required {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="corporate_number"
              render={({ field }) => (
                <FormItem className="flex items-center gap-2">
                  <FormLabel className="min-w-[150px] text-left">法人番号</FormLabel>
                  <Asterisk className="h-4 w-4 text-red-500" />
                  <span className="inline-block p-2 bg-red-600 text-white rounded-md text-xs w-12">
                    必須
                  </span>
                  <FormControl className="flex-auto">
                    <Input type="text" placeholder="13桁数字" autoComplete="name" required {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex items-center gap-4">
              <FormField
                control={form.control}
                name="company_address_prefecture"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-2 w-full">
                    <FormLabel className="min-w-[150px] text-left">所在地</FormLabel>
                    <Asterisk className="h-4 w-4 text-red-500" />
                    <span className="inline-block p-2 bg-red-600 text-white rounded-md text-xs w-12">
                      必須
                    </span>
                    <FormControl className="flex-1">
                      <Select value={field.value || ""} onValueChange={(value) => field.onChange(value)}>
                        <SelectTrigger>{field.value || "都道府県を選択"}</SelectTrigger>
                        <SelectContent>
                          {prefecture_namelist.map((p) => (
                            <SelectItem key={p} value={p}>
                              {p}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="company_address_city"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-2 w-full">
                    <FormControl className="flex-1">
                      <Input type="text" placeholder="市区町村" autoComplete="name" required {...field} />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>


            <Button type="submit" disabled={mutation.isPending} className="mt-4 bg-green-400 mr-10 text-xl hover:bg-green-300">
              <>
              {mutation.isPending ? (
                <Icons.spinner className="mr-2 size-4 animate-spin" aria-hidden="true" />
              ) : null}
              </>
              登  録
            </Button>
            <Button variant="secondary" onClick={() => navigate("/master/mscs01")} className="bg-gray-400 hover:bg-gray-300 mr-10 text-xl">
              <>
              {mutation.isPending ? (
                <Icons.spinner className="mr-2 size-4 animate-spin" aria-hidden="true" />
              ) : null}
              </>
              戻  る
            </Button>
          </form>
        </Form>
        
        <AlertModal
          isOpen={showConfirm}
          onClose={() => closePopup()}
          onConfirm={() => submitData()} 
          loading ={false}
          title="確認"
          description="この内容で登録を実行してもよいですか？"
          cancelText="いいえ"
          continueText="はい"
        />
         
      </div>
    </div>
  );
};

export default CustomLogin;
