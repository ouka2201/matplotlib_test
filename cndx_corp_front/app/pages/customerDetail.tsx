import { Label } from "@radix-ui/react-label";
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from 'react-router-dom';
import BreadCrumb from "~/components/common/breadcrumb";
import Footer from "~/components/common/footer";
import { AlertModal } from "~/components/modal/alert-modal";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "~/components/ui/accordion";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger } from "~/components/ui/select";
import { Toggle } from "~/components/ui/toggle";
import { postData } from "~/lib/fetch";
import "~/styles/screen/master/mscs01.css";
import { Building, CustomerCompany } from "~/types/screen/master/mscs/mscsType";

// 1. sessionStorage から文字列データを取得
// const prefecture = sessionStorage.getItem("m_prefecture");
// let prefecture_namelist: string[] = [];
// if (prefecture) {
//   // 2. JSON.parse で配列に変換
//   const prefectureList = JSON.parse(prefecture);

//   // 3. 名称（pref_nm）だけのリストに変換
//   prefecture_namelist = prefectureList.map((p: { pref_nm: string }) => p.pref_nm);

// }

const agreement_category_list = [
  { id: "00", name: "地銀アライアンス（EP・REP）" },
  { id: "01", name: "可視化アライアンス（アスエネ）" },
  { id: "02", name: "可視化アライアンス（ゼロボード）" },
  { id: "03", name: "可視化アライアンス（ブースト）" },
  { id: "04", name: "可視化アライアンス（JFS）" },
  { id: "99", name: "同意未取得" }
];

// IDを指定して対応するnameを取得
const getCategoryNameById = (id: string) => {
  const category = agreement_category_list.find((item) => item.id === id);
  return category ? category.name : "不明なID";
};

// type User = {
//   name: string;
//   email: string;
//   // 必要に応じて追加
// };

export default function CustomerDetailForm() {
  const [prefecture_namelist, set_prefecture_namelist] = useState<string[]>([]);
  // const [user, setUser] = useState<User | null>(null);

  const location = useLocation();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const data = sessionStorage.getItem("m_prefecture");
      setIsEditing(location.state?.mode === "edit");
      if (isNewRef) {
        setIsEditing(true);

      }
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
  }, [location.state?.mode]);

  const navigate = useNavigate();

  // 入口判定ロジック
  const isNewRegistration = location.pathname.includes('/master/mscs02');
  const [initialData] = useState(location.state?.customerData);

  // 状態管理
  const [isEditing, setIsEditing] = useState(location.state?.mode === "edit");
  const isNewRef = useRef(location.state?.mode === "new");
  const initialCustomerData = useMemo(() => {
    if (isNewRegistration) {
      return {
        company_name: "",
        company_name_kana: "",
        corporate_number: "",
        company_address_prefecture: "",
        company_address_city: ""
      };
    }
    return initialData || {
      company_name: "",
      company_name_kana: "",
      corporate_number: "",
      company_address_prefecture: "",
      company_address_city: ""
    };
  }, [isNewRegistration, initialData]);

  // 保存用
  const [customer, setCustomer] = useState<CustomerCompany>(initialCustomerData);

  // 入力用
  const handleCompanyChange = (field: keyof CustomerCompany, value: string) => {
    setCustomer(prev => ({ ...prev, [field]: value }));
  };

  const [officeInfoList, setOfficeInfoList] = useState<OfficeInfo[]>(() => [
    {
      agreement_category: "03",
      building_name: "",
      building_address_prefecture: "",
      building_address_city: "",
      ep_customer_number: "",
      supply_point_number: ""
    }
  ]);
  // const [consent] = useState({
  //   route1: "経路A",
  //   route2: "経路B",
  // });

  const [offices, setOffices] = useState<Building[]>([]);

  useEffect(() => {
    if (customer.office_info_list) {
      setOffices([...customer.office_info_list]);
    }
  }, [customer.office_info_list]);

  // 入力変更ハンドラー
  const handleOfficeChange = (index: number, field: string, value: string) => {
    setOffices((prev) => {
      const updatedOffices = [...prev];
      updatedOffices[index] = {
        ...updatedOffices[index],
        [field]: value,
      };
      return updatedOffices;
    });
  };

  const [fieldErrors, setFieldErrors] = useState<Record<string, boolean>>({});
  const [showConfirmationDialog, setShowConfirmationDialog] = useState(false);

  // 建物ID生成
  const generateBuildingId = (index: number) => {
    return `${customer.corporate_number}001${(index + 1).toString().padStart(3, '0')}`;
  };

  // 検証ロジック
  const validateForm = () => {
    const newErrors: Record<string, boolean> = {};

    if (!customer.company_name.trim()) newErrors.company_name = true;
    if (!/^\d{13}/.test(customer.corporate_number)) newErrors.corporate_number = true;
    if (!customer.company_address_prefecture) newErrors.company_address_prefecture = true;
    if (!customer.company_address_city.trim()) newErrors.company_address_city = true;

    officeInfoList.forEach((office, index) => {
      const prefix = `office_${index}_`;
      if (!office.agreement_category) newErrors[prefix + 'agreement'] = true;
      if (!office.building_name.trim()) newErrors[prefix + 'name'] = true;
      if (!office.ep_customer_number && !office.supply_point_number) newErrors[prefix + 'numbers'] = true;
    });

    setFieldErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 送信処理
  const handleSubmit = async () => {
    // if (!validateForm()) return;
    setShowConfirmationDialog(true);
  };

  const handleConfirmSubmit = async () => {

    const requestData = {
      user_id: sessionStorage.getItem("email"),
      company_name: customer.company_name,
      company_name_kana: customer.company_name_kana,
      corporate_number: customer.corporate_number,
      company_address_prefecture: customer.company_address_prefecture,
      company_address_city: customer.company_address_city,
      usage_type: "1",
      office_info_list: offices.map((office, index) => ({
        org_id: "組織ID",
        agreement_category: office.agreement_category,
        building_name: office.building_name,
        building_address_prefecture: office.building_address_prefecture,
        building_address_city: office.building_address_city,
        ep_customer_number: office.ep_customer_number,
        supply_point_number: office.supply_point_number,
        building_id: generateBuildingId(index)
      }))
    };

    try {
      // const API_BASE = "http://192.168.1.17:5000";
      const result = await postData("/api/mst_manage/corpration/info", requestData);

      if (result) {

        setShowConfirmationDialog(false);
        navigate("/master/mscs01", {
          state: {
            customerData: requestData,
            mode: "refer"
          }
        });
      }
    } catch (error) {
      setShowConfirmationDialog(false);
      navigate("/master/mscs01", {
        state: {
          customerData: requestData,
          mode: "refer"
        }
      }
        // setShowConfirmationDialog(false);
        // console.error("登録エラー:", error);
      )
    }
  };

  const ErrorMessage = ({ children }: { children: React.ReactNode }) => (
    <div style={{
      color: '#dc3545',
      fontSize: '0.85rem',
      marginTop: '4px',
      position: 'relative'
    }}>
      <div className="error-tooltip">
        {children}
      </div>
    </div>
  );

  // 拠点追加
  const addOffice = () => {
    setCustomer((prevCustomer) => ({
      ...prevCustomer,
      office_info_list: [
        ...(prevCustomer.office_info_list || []), // 安全に配列を展開
        {
          agreement_category: "00",
          building_name: "",
          building_address_prefecture: "",
          building_address_city: "",
          ep_customer_number: "",
          supply_point_number: "",
          building_id: `TEMP_${Date.now()}`,
        },
      ],
    }) as CustomerCompany); // 型アサーションでCustomerCompanyを明示
    setOffices(customer.office_info_list?.filter((office) => !office.delete_flg) || []);
  };

  const deleteOffice = (index: number) => {
    setCustomer((prevCustomer) => {
      const updatedList = prevCustomer.office_info_list?.map((building, i) => {
        if (i === index) {
          // building_idが存在するならdeleteFlgをtrueに
          if (building.building_id) {
            return { ...building, deleteFlg: true };
          }
        }
        return building;
      }).filter((building) => !building.delete_flg); // deleteFlgがtrueの場合は非表示

      return {
        ...prevCustomer,
        office_info_list: updatedList,
      };
    });

    setOffices(customer.office_info_list?.filter((office) => !office.delete_flg) || []);
  };


  // スタイルヘルパー
  const getInputStyle = (isEditing: boolean, hasError: boolean) => {
    return [
      "input-base",                  // 基本スタイル（必ず適用）
      isEditing ? "input-editable" : "", // 編集モード時
      hasError ? "input-error" : ""       // エラースタイル
    ].join(" ");
  };

  // 丸付き数字の変換
  const getCircledNumber = (num: number): string => {
    if (num < 1 || num > 20) return String(num);
    return String.fromCharCode(0x245f + num);
  };

  // 拠点情報変更処理
  const handleOfficeChange_old = (
    index: number,
    field: keyof OfficeInfo,
    value: string
  ) => {
    const newList = [...officeInfoList];
    newList[index] = {
      ...newList[index],
      [field]: value
    };
    setOfficeInfoList(newList);

    // エラー状態をリセット
    const errorKeys = [
      `office_${index}_agreement`,
      `office_${index}_name`,
      `office_${index}_address`,
      `office_${index}_numbers`
    ];
    setFieldErrors(prev => {
      const newErrors = { ...prev };
      errorKeys.forEach(key => delete newErrors[key]);
      return newErrors;
    });
  };

  // エラーテキストコンポーネント
  const ErrorText: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div style={{
      color: '#dc3545',
      fontSize: '0.85rem',
      marginTop: '4px',
      display: 'flex',
      alignItems: 'center',
      gap: '4px'
    }}>
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="#dc3545"
      >
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
      </svg>
      {children}
    </div>
  );

  const breadcrumbItems = [
    { title: "お客さま企業マスタ", link: "/master/mscs01" },
    { title: customer.company_name, link: "" }, // TODO historyから取得させる
  ];

  return (
    <div className="base-container">
      <div className="fixed pt-0 w-full top-16 flex items-end justify-between">
        {/* パンくずリスト */}
        <BreadCrumb items={breadcrumbItems} />
        {/* <div className="breadcrumbStyle">
            <Link to="/master/mscs01" style={{ textDecoration: 'none', color: '#0068b7' }}>
              {paths[0]}
            </Link>
            <span> ＞ </span>
            <span>{paths[1]}</span>
          </div> */}

        {/* 操作ボタン */}
        {/* {!isNewRef && ( */}
        <Button
          onClick={() => setIsEditing(!isEditing)}
          variant="secondary" // 例: アウトラインスタイル
          className="" // 必要に応じてカスタムクラス
        >
          {isEditing ? "編集取消" : "編集"}
        </Button>
        {/* )} */}
        <Toggle
          pressed={isEditing}
          onPressedChange={(pressed) => setIsEditing(pressed)}
          className="mb-2"
        >
          {isEditing ? "編集モード" : "閲覧モード"}
        </Toggle>
      </div>

      {isEditing && (
        <Button
          onClick={handleSubmit}
          variant="default" // 例: アウトラインスタイル
          className="submit-button" // 必要に応じてカスタムクラス
        >
          {"保存"}
        </Button>
      )}

      {/* 基礎情報 */}
      <Accordion
        type="multiple"
        // collapsible
        className="pl-3"
        defaultValue={["item-1", "item-3"]}
      >
        <AccordionItem value="item-1">
          <AccordionTrigger>
            <div className="flex items-center gap-2 text-2xl">
              {/* <ChevronRight className="accordion-icon transition-transform duration-200 data-[state=open]:rotate-90"/> */}
              基本情報
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <Card className="border-4">
              <CardHeader>
                <CardTitle />
                <CardDescription />
              </CardHeader>

              <CardContent className="flex items-center gap-6">
                <div className="grid gap-4">
                  {/* <div className="row-span-4 text-lg font-bold flex items-center">お客さま情報</div> */}
                  <div className="flex items-center gap-2">
                    <Label className="whitespace-nowrap min-w-[200px] text-left">お客さま名</Label>
                    {isEditing ? (
                      <Input
                        type="text"
                        value={customer.company_name}
                        autoComplete="name"
                        // placeholder="Please enter the name you want to search for"
                        className={getInputStyle(isEditing, !!fieldErrors.company_name)}
                        onChange={(e) => handleCompanyChange('company_name', e.target.value)}
                      />
                    ) :
                      (
                        <Label>
                          {customer.company_name}
                        </Label>
                      )}

                  </div>
                  <div className="flex items-center gap-2">
                    <Label className="whitespace-nowrap min-w-[200px] text-left">お客さま名(ふりがな)</Label>
                    {isEditing ? (
                      <Input
                        type="text"
                        value={customer.company_name_kana}
                        readOnly={!isEditing}
                        autoComplete="name"
                        // placeholder="Please enter the name you want to search for"
                        name="name"
                        className={getInputStyle(isEditing, !!fieldErrors.company_name_kana)}
                        onChange={(e) => handleCompanyChange('company_name_kana', e.target.value)}
                      />
                    ) :
                      (
                        <Label>
                          {customer.company_name}
                        </Label>
                      )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Label className="whitespace-nowrap min-w-[200px] text-left">法人番号</Label>
                    {isEditing ? (
                      <Input
                        type="text"
                        value={customer.corporate_number}
                        // placeholder="Please enter the name you want to search for"
                        readOnly={!isEditing}
                        autoComplete="name"
                        name="name"
                        className={getInputStyle(isEditing, !!fieldErrors.corporate_number)}
                        onChange={(e) => handleCompanyChange('corporate_number', e.target.value)}
                      />
                    ) :
                      (
                        <Label>
                          {customer.company_name}
                        </Label>
                      )}
                  </div>
                  <div className="flex items-center">
                    <Label className="whitespace-nowrap min-w-[200px] text-left">所在地</Label>
                    {isEditing ? (
                      <>
                        <Select
                          value={customer.company_address_prefecture}
                          onValueChange={(value) => handleCompanyChange("company_address_prefecture", value)}
                        // disabled={!isEditing && !isNewRegistration}
                        >
                          <SelectTrigger
                            className={getInputStyle(isEditing, false) + (!isEditing && !isNewRegistration ? " pointer-events-none opacity-50" : "")}
                          // className={getInputStyle(isEditing, !!fieldErrors.company_address_prefecture)}
                          >
                            {customer.company_address_prefecture || "都道府県を選択"}
                          </SelectTrigger>
                          <SelectContent>
                            {prefecture_namelist.map((p) => (
                              <SelectItem key={p} value={p}>
                                {p}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>

                        <Input
                          type="text"
                          value={customer.company_address_city}
                          readOnly={!isEditing && !isNewRegistration}
                          placeholder="※必須・フリー記述  市区町村以降を入力"
                          name="name"
                          autoComplete="name"
                          className={getInputStyle(isEditing, !!fieldErrors.company_address_city)}
                          onChange={(e) => handleCompanyChange('company_address_city', e.target.value)}
                        />
                      </>
                    ) :
                      (
                        <>
                          <Label>
                            {customer.company_address_prefecture}
                          </Label>
                          <Label>
                            {customer.company_address_city}
                          </Label>
                        </>
                      )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* <Card className="max-w-lg p-4">
                <CardContent className="grid gap-4">
                  <div className="flex items-center gap-2">
                    <Label className="min-w-[100px]">開始日</Label>
                    <div className="flex flex-col">
                      <Calendar
                        selected={startDate}
                        onSelect={(date) => setStartDate(date)}
                        className="w-full"
                      />
                      {startDate && (
                        <p className="mt-1 text-xs text-gray-500">
                          {format(startDate, "yyyy/MM/dd")}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Label className="min-w-[100px]">終了日</Label>
                    <div className="flex flex-col">
                      <Calendar
                        selected={endDate}
                        onSelect={(date) => setEndDate(date)}
                        className="w-full"
                        minDate={startDate || undefined} // 開始日より後しか選べない
                      />
                      {endDate && (
                        <p className="mt-1 text-xs text-gray-500">
                          {format(endDate, "yyyy/MM/dd")}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card> */}

          </AccordionContent>
        </AccordionItem>

        {/* 同意取得情報 */}
        {!isNewRef && (
          <AccordionItem value="item-2">
            <AccordionTrigger>
              <div className="flex items-center gap-2 text-2xl">
                同意取得情報
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <Card className="border-4">
                <CardHeader>
                  <CardTitle />
                  <CardDescription />
                </CardHeader>

                <CardContent className="grid gap-6">
                  <div className="flex flex-col gap-2">
                    {offices?.map((office, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <Label className="whitespace-nowrap min-w-[200px] text-left">同意書取得経路{getCircledNumber(index + 1)}</Label>
                        {isEditing ? (
                          <Input
                            type="text"
                            className="baseInputStyle"
                            name="name"
                            readOnly={!isEditing}
                            value={getCategoryNameById(office.agreement_category)}
                          />
                        ) :
                          (
                            <Label>
                              {customer.company_name}
                            </Label>
                          )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </AccordionContent>
          </AccordionItem>
        )}

        <AccordionItem value="item-3">
          <AccordionTrigger>
            <div className="flex items-center gap-2 text-2xl">
              拠点情報
            </div>
          </AccordionTrigger>

          {!isEditing && (
            <Button
              onClick={() => navigate('/master/msbd01')}
              variant="default"
              className="bg-blue-400"
            >
              拠点マスタ管理
            </Button>
          )}
          <AccordionContent>
            {offices?.map((office, index) => (
              <Card className="border-4" key={`office-${index}`}>
                <CardHeader className="flex flex-row mr-2 justify-between w-full">
                  <CardTitle className="text-lg">拠点{getCircledNumber(index + 1)}情報</CardTitle>
                  <Button
                    onClick={() => deleteOffice(index)}
                    variant="default"
                    className="bg-red-400 "
                  >
                    削除
                  </Button>
                  <CardDescription />
                </CardHeader>

                <CardContent className="grid gap-6">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <Label className="whitespace-nowrap min-w-[200px] text-left">同意書取得経路{getCircledNumber(index + 1)}</Label>
                      {isEditing ? (
                        <Select
                          value={office.agreement_category}
                          onValueChange={(value) => handleOfficeChange(index, 'agreement_category', value)}
                        // disabled={!isEditing && !isNewRegistration}
                        >
                          <SelectTrigger
                            className={getInputStyle(isEditing, false) + (!isEditing && !isNewRegistration ? " pointer-events-none opacity-50" : "")}
                          // className={getInputStyle(isEditing, !!fieldErrors.agreement_category)}
                          >
                            {getCategoryNameById(office.agreement_category) || "同意書経路を選択"}
                          </SelectTrigger>
                          <SelectContent>
                            {agreement_category_list.map((option) => (
                              <SelectItem key={option.id} value={option.id}>
                                {option.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) :
                        (
                          <Label>
                            {office.agreement_category}
                          </Label>
                        )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Label className="whitespace-nowrap min-w-[200px] text-left">拠点名</Label>
                      {isEditing ? (
                        <Input
                          type="text"
                          readOnly={!isEditing}
                          autoComplete="name"
                          value={office.building_name}
                          onChange={e => handleOfficeChange(index, 'building_name', e.target.value)}
                          className={getInputStyle(isEditing, !!fieldErrors[`office_${index}_name`])}
                        />
                      ) :
                        (
                          <Label>
                            {office.building_name}
                          </Label>
                        )}
                      {fieldErrors[`office_${index}_name`] && (
                        <ErrorText>※必須・フリー記述</ErrorText>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Label className="whitespace-nowrap min-w-[200px] text-left">所在地</Label>
                      {isEditing ? (
                        <>
                          <Select
                            value={office.building_address_prefecture}
                            onValueChange={(value) => handleOfficeChange(index, "building_address_prefecture", value)}
                          >
                            <SelectTrigger
                              className={getInputStyle(isEditing, false) + (!isEditing && !isNewRegistration ? " pointer-events-none opacity-50" : "")}

                            // className={getInputStyle(isEditing, !!fieldErrors.building_address_prefecture)}
                            >
                              {office.building_address_prefecture || "都道府県を選択"}
                            </SelectTrigger>
                            <SelectContent>
                              {prefecture_namelist.map((p) => (
                                <SelectItem key={p} value={p}>
                                  {p}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Input
                            type="text"
                            value={office.building_address_city}
                            readOnly={!isEditing && !isNewRef}
                            placeholder="市区町村以降を入力"
                            autoComplete="name"
                            name="name"
                            className={getInputStyle(isEditing, !!fieldErrors.building_address_city)}
                            onChange={(e) => handleOfficeChange(index, 'building_address_city', e.target.value)}
                          />
                        </>
                      ) :
                        (
                          <>
                            <Label>
                              {office.building_address_prefecture}
                            </Label>
                            <Label>
                              {office.building_address_city}
                            </Label>
                          </>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Label className="whitespace-nowrap min-w-[200px] text-left">EP番号</Label>
                      {isEditing ? (
                        <Input
                          type="text"
                          value={office.ep_customer_number}
                          autoComplete="name"
                          onChange={e => handleOfficeChange(index, 'ep_customer_number', e.target.value)}
                          readOnly={!isEditing}
                          className={getInputStyle(isEditing, !!fieldErrors[`office_${index}_name`])}
                        />
                      ) :
                        (
                          <Label>
                            {office.ep_customer_number}
                          </Label>
                        )}
                      {fieldErrors[`office_${index}_name`] && (
                        <ErrorText>※必須・フリー記述</ErrorText>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Label className="whitespace-nowrap min-w-[200px] text-left">供給地点特定番号</Label>
                      {isEditing ? (
                        <Input
                          type="text"
                          value={office.supply_point_number}
                          autoComplete="name"
                          readOnly={!isEditing}
                          onChange={(e) => handleOfficeChange(index, "supply_point_number", e.target.value)}
                          className={getInputStyle(isEditing, !!fieldErrors[`office_${index}_name`])}
                        />
                      ) :
                        (
                          <Label>
                            {office.supply_point_number}
                          </Label>
                        )}
                      {fieldErrors[`office_${index}_name`] && (
                        <ErrorText>※必須・フリー記述</ErrorText>
                      )}
                    </div>

                    {/* <div className="flex items-center gap-2">
                      <Label className="whitespace-nowrap min-w-[200px] text-left">建物ID</Label> */}
                    {/* {isEditing ? ( */}
                    {/* <Input
                          type="text"
                          value={office.building_id}
                          readOnly ={!isEditing}
                          className="baseInputStyle bg-[#e9ecef] cursor-not-allowed"
                        /> */}
                    {/* ) : (
                        <div className="p-2 border rounded-md">{office.building_id}</div>
                      )} */}
                    {/* {fieldErrors[`office_${index}_name`] && (
                        <ErrorText>※必須・フリー記述</ErrorText>
                      )}
                    </div> */}
                  </div>
                </CardContent>
              </Card>
            ))}
          </AccordionContent>
          {isEditing && (
            <button
              onClick={addOffice}
              style={{
                padding: '10px 20px',
                backgroundColor: '#17a2b8',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
              </svg>
              拠点追加
            </button>
          )}
        </AccordionItem>
      </Accordion>
      <Footer
        buttons={[
          { text: "登 録", isLoading: isLoading, variant: "default", className: "mr-2", onClick: form.handleSubmit(onSubmit) },
        ]}
      />

      {/* {showConfirmationDialog && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 2000
          }}>
            <div style={{
              backgroundColor: 'white',
              padding: '2rem',
              borderRadius: '8px',
              minWidth: '400px',
              textAlign: 'center'
            }}>
              <p style={{ marginBottom: '2rem' }}>この内容で登録してよろしいでしょうか？</p>
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                <button
                  onClick={handleConfirmSubmit}
                  style={{
                    padding: '8px 24px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  はい
                </button>
                <button
                  onClick={() => setShowConfirmationDialog(false)}
                  style={{
                    padding: '8px 24px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  いいえ
                </button>
              </div>
            </div>
          </div>
        )} */}

      <AlertModal
        isOpen={showConfirmationDialog}
        onClose={() => setShowConfirmationDialog(false)}
        onConfirm={() => handleConfirmSubmit()}
        loading={false}
        title="確認"
        description="この内容で登録を実行してもよいですか？"
        cancelText="いいえ"
        continueText="はい"
      />
    </div>
  );
}