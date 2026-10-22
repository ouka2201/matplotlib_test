import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import ErrorHint from "~/components/common/error-hint";
import { LoadingSpinner } from "~/components/common/loadingSpinner";
import MasterFormField from "~/components/common/master-form-field";
import SectionTitle from "~/components/common/section-title";
import MasterLayout from "~/components/layout/master-layout";
import { AlertModal } from "~/components/modal/alert-modal";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Form } from "~/components/ui/form";
import { PageableTable } from "~/components/ui/pageable-table";
import { TableCell, TableRow } from "~/components/ui/table";
import { useToast } from "~/components/ui/use-toast";
import { Messages } from "~/constants/messages/message";
import { useScrollToError } from "~/hooks/useScrollToError";
import { getData, postData } from "../lib/fetch";

interface CustomerInfo {
  customerName: string; // お客さま名
  corpNumber: string; // 法人番号
  address: string; // 所在地
  orgId: string; //組織ID
}

interface BuildingInfo {
  building_id: string;
  route: string; // 同意取得経路名
  code: string; // 同意取得経路
  officeName: string; // 拠点名
  officeAddress: string; // 拠点所在地
  epCustomerCode: string; // EP事業者コード
  epCustomerNumber: string; // EPお客さま番号
  supplyNumber: string; // 供給地点特定番号
}

type UploadRecord = {
  filename: string;
  startMonth: string; // yyyy/mm
  endMonth: string; // yyyy/mm
  fileUpdateDate: string; // yyyy/mm/dd
  source: string;
};

export default function CustomerMasterForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const navigationState = (location.state as { agreement_category?: string; org_id?: string } | null) ?? null;
  const form = useForm();
  const [showUploadTable, setShowUploadTable] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  const errorTopRef = useScrollToError(errorMessage);
  const { saveSuccessToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [customerInfo, setCustomerInfo] = useState<CustomerInfo>({
    customerName: "",
    corpNumber: "",
    address: "",
    orgId: "",
  });

  const [buildingInfo, setBuildingInfo] = useState<BuildingInfo>({
    building_id: "",
    route: "", // 同意取得経路名
    code: "", // 同意取得経路
    officeName: "", //建物・拠点名
    officeAddress: "", //建物所在地(都道府県)
    epCustomerCode: "", //EP事業者コード
    epCustomerNumber: "", //EPお客さま番号
    supplyNumber: "", //供給地点特定番号
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadRecords, setUploadRecords] = useState<UploadRecord[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [token] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      return sessionData ? JSON.parse(sessionData).token : null;
    }
    return null;
  });

  // 修正: モーダル状態の型を明示的に定義
  const [confirmModalState, setConfirmModalState] = useState<{
    isOpen: boolean;
    onConfirm: (() => Promise<void>) | null;
  }>({
    isOpen: false,
    onConfirm: null,
  });

  // sessionStorageからデータを読み込む
  useEffect(() => {
    const raw = sessionStorage.getItem("selectedCorporateItem");

    if (raw) {
      try {
        const item = JSON.parse(raw);
        // setUserId(item.user_id ?? "");

        console.log("選択された企業データ:", item);

        // お客さま情報を設定する
        setCustomerInfo({
          customerName: item.company_name ?? "",
          corpNumber: item.corporate_number ?? "",
          orgId: item.org_id ?? "",
          address: `${item.company_address_prefecture ?? ""}${item.company_address_city ?? ""}`,
        });

        // ビルド情報を設定する
        setBuildingInfo({
          building_id: item.building_id ?? "",
          route: item.agreementCategoryName ?? "",
          code: item.agreementCategory ?? "",
          officeName: item.building_name ?? "",
          officeAddress: `${item.building_address_prefecture ?? ""}${item.building_address_city ?? ""}`,
          epCustomerCode: item.ep_office_code ?? "",
          epCustomerNumber: item.ep_customer_number ?? "",
          supplyNumber: item.supply_point_number ?? "",
        });

        // フォームを更新する
        form.reset({
          customerName: item.company_name ?? "",
          corpNumber: item.corporate_number ?? "",
          address: `${item.company_address_prefecture ?? ""}${item.company_address_city ?? ""}`,
          route: item.agreementCategoryName ?? "",
          officeName: item.building_name ?? "",
          officeAddress: `${item.building_address_prefecture ?? ""}${item.building_address_city ?? ""}`,
          epCustomerCode: item.ep_office_code ?? "",
          epCustomerNumber: item.ep_customer_number ?? "",
          supplyNumber: item.supply_point_number ?? "",
        });

        // アップロード履歴を取得する
        if (item.corporate_number && item.building_id) {
          fetchUploadStatus(item.corporate_number, item.building_id, item.agreementCategory);
        }
      } catch (err) {
        console.error(Messages.energy_building.ebmv01.session_error, err);
      }
    }

    // 初期化済みとする
    setIsInitialized(true);
  }, []);

  // ページ更新時に初期状態へリセットする
  useEffect(() => {
    if (!isInitialized) return;

    // beforeunloadイベントを監視する
    const handleBeforeUnload = () => {
      // ページを更新する前にsessionStorageをクリアする
      sessionStorage.removeItem("selectedCorporateItem");
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      // コンポーネントのアンマウント時にbeforeunloadイベントリスナーを解除し、sessionStorageをクリアする
      sessionStorage.removeItem("selectedCorporateItem");
    };
  }, [isInitialized]);

  const fetchUploadStatus = async (corpNumber: string, buildingId: string, agr: string) => {
    try {
      const url = `/api/building/per_30min_data?corp_number=${corpNumber}&building_id=${buildingId}&agreement_category=${agr}`;
      const res = await getData(url);
      console.log(res);

      const uploadHistory = res.result?.upload_history || [];

      const formatFileUpdateDate = (dateStr: string | number): string => {
        const str = String(dateStr);
        if (str.length !== 8) return "--/--/--";
        return `${str.slice(0, 4)}/${str.slice(4, 6)}/${str.slice(6, 8)}`;
      };

      const formatUpdatedAt = (dateStr: string | number): string => {
        const str = String(dateStr);
        if (!str) return "--/--/-- --:--:--";
        const normalized = str.replace("T", " ").replace("Z", "");
        if (normalized.length < 19) return "--/--/-- --:--:--";
        return normalized.slice(0, 19).replace(/-/g, "/");
      };

      const uploadRecords: UploadRecord[] = uploadHistory
        .map((item) => ({
          filename: "※登録済み情報※",
          startMonth: formatFileUpdateDate(item.period_from),
          endMonth: formatFileUpdateDate(item.period_to),
          fileUpdateDate: formatUpdatedAt(item.file_update_date),
          source: "manual",
        }))
        .sort((a: UploadRecord, b: UploadRecord) => {
          const timeA = new Date(a.startMonth).getTime();
          const timeB = new Date(b.startMonth).getTime();
          return timeB - timeA;
        });

      setUploadRecords(uploadRecords);
      setShowUploadTable(true);
    } catch (error) {
      console.error(Messages.VALIDATION.api.fetch_error, error);
    }
  };

  const isCSVFile = (file: File) => {
    return (
      file &&
      file.name.toLowerCase().endsWith(".csv") &&
      (file.type === "text/csv" || file.type === "application/vnd.ms-excel")
    );
  };

  // チェック部分
  const handleRegister = async () => {
    if (loading) return;
    if (!selectedFile) {
      setErrorMessage(Messages.energy_building.ebmv01.file_unselected);
      return;
    }

    if (!isCSVFile(selectedFile)) {
      setErrorMessage(Messages.energy_building.ebmv01.file_type_error);
      return;
    }

    setConfirmModalState({
      isOpen: true,
      onConfirm: executeRegistration,
    });
  };

  // 実際の登録処理
  const executeRegistration = async () => {
    try {
      if (!selectedFile) {
        setErrorMessage(Messages.energy_building.ebmv01.file_unselected);
        return;
      }

      const corpNumber = customerInfo.corpNumber;
      const buildingId = buildingInfo.building_id;
      const epCustomerCode = buildingInfo.epCustomerCode;
      const epCustomerNumber = buildingInfo.epCustomerNumber;
      const customerName = customerInfo.customerName;
      const officeName = buildingInfo.officeName;
      const userId = sessionStorage.getItem("user_id")!;
      const file_name = selectedFile.name;
      const supplyNumber = buildingInfo.supplyNumber;
      const org = customerInfo.orgId || navigationState?.org_id || "";
      const agr = buildingInfo.code || navigationState?.agreement_category || "";

      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(Messages.energy_building.ebmv01.file_loading_failed);
        if (selectedFile) {
          reader.readAsDataURL(selectedFile);
        }
      });

      const payload = {
        file_name,
        file_data: base64.split(",")[1], // Base64のデータ部分のみを抽出
        corp_number: corpNumber,
        building_id: buildingId,
        ep_office_code: epCustomerCode,
        ep_customer_number: epCustomerNumber,
        corp_name: customerName,
        building_name: officeName,
        user_id: userId,
        supply_point_number: supplyNumber,
        org_id: org,
        agreement_category: agr,
      };

      const response = await postData(`/api/file/per-30m-data`, payload, {
        Authorization: `Bearer ${token}`,
      });

      if (!response.ok) {
        const errorData = await response.json();
        setErrorMessage(errorData.message || Messages.REGISTER_FAILED);
      } else {
        setErrorMessage("");
      }

      // アップロード後に最新の状態を取得
      await fetchUploadStatus(corpNumber, buildingId, agr);

      // setAlertState({
      //   isOpen: true,
      //   title: "アップロード完了",
      //   description: Messages.REGISTER_SUCCESS,
      // });
      saveSuccessToast({
        //description: Messages.REGISTER_SUCCESS,
      });

      setSelectedFile(null);
      form.setValue("filename", "");
    } catch (error: unknown) {
      setErrorMessage(Messages.SYSTEM_ERROR);

      if (error instanceof Error) {
        setErrorMessage(error.message || errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedFile) {
      form.setValue("filename", selectedFile.name);
    }
  }, [selectedFile, form]);

  //パンくず
  const breadcrumbItems = [{ title: "30分値登録", link: "" }];

  const columns: ColumnDef<UploadRecord>[] = [
    {
      accessorKey: "startMonth",
      header: "開始年月日",
      cell: ({ row }) => <p className="text-left">{row.getValue("startMonth")}</p>,
    },
    {
      accessorKey: "endMonth",
      header: "終了年月日",
    },
    {
      accessorKey: "fileUpdateDate",
      header: "登録・更新日時",
    },
  ];

  return (
    <MasterLayout breadcrumbItems={breadcrumbItems}>
      <div ref={errorTopRef as React.RefObject<HTMLDivElement>} />
      <div ref={errorTopRef as React.RefObject<HTMLDivElement>} className="w-4/5 mt-5 scroll-mt-[300px]">
        <ErrorHint
          // title="エラー内容の詳細"
          message={errorMessage}
          bodyClassName="py-4"
        />
      </div>
      {/* <div className="page-container"> */}
      <div className="relative">
        <Form {...form}>
          {/* ▼お客さま企業・拠点の選択セクション */}
          <div className="mb-8">
            <SectionTitle>▼お客さま基本情報・拠点情報</SectionTitle>
            <div className="mb-6">
              <Button
                variant="second"
                // size="second"
                onClick={() => {
                  sessionStorage.setItem("from", "ebmv01");
                  navigate("/energy-building/ebmv02");
                }}
              >
                選択
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* お客さま情報カード */}
              <Card className="bg-gray-50 h-[240px]">
                <CardHeader>
                  <CardTitle className="text-[16px]">お客さま基本情報</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="">
                    <MasterFormField
                      control={form.control}
                      name="customerName"
                      label="お客さま名"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                    <MasterFormField
                      control={form.control}
                      name="corpNumber"
                      label="法人番号"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                    <MasterFormField
                      control={form.control}
                      name="address"
                      label="本社所在地"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* 拠点情報カード */}
              <Card className="bg-gray-50">
                <CardHeader>
                  <CardTitle className="text-[16px]">拠点情報</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="">
                    <MasterFormField
                      control={form.control}
                      name="officeName"
                      label="拠点名"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                    <MasterFormField
                      control={form.control}
                      name="officeAddress"
                      label="拠点所在地"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                    <MasterFormField
                      control={form.control}
                      name="epCustomerCode"
                      label="事業所コード"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                    <MasterFormField
                      control={form.control}
                      name="epCustomerNumber"
                      label="お客さま番号"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                    <MasterFormField
                      control={form.control}
                      name="supplyNumber"
                      label="供給地点特定番号"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* 同意書取得経路カード */}
              <Card className="bg-gray-50 md:col-start-2">
                <CardHeader>
                  <CardTitle className="text-[16px]">同意書取得経路情報</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="">
                    <MasterFormField
                      control={form.control}
                      name="route"
                      label="同意書取得経路"
                      placeholder="※手動入力不可※"
                      isEditing={false}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* ▼30分値アップロードセクション */}
          <div className="mb-8">
            <SectionTitle>▼電力30分値登録（CSVアップロード）</SectionTitle>
            <div className="bg-gray-50 p-6 rounded-lg">
              <div className="flex flex-col md:flex-row md:items-center gap-4 mb-6">
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    setSelectedFile(file || null);
                    e.target.value = "";
                  }}
                  accept=".csv"
                />

                <Button
                  variant="second"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={!buildingInfo.building_id || loading}
                >
                  選択
                </Button>

                <Button variant="primary" onClick={handleRegister} disabled={!buildingInfo.building_id || !selectedFile || loading}>
                  登録
                </Button>
              </div>

              <MasterFormField
                control={form.control}
                name="filename"
                label="ファイル名"
                placeholder="※手動入力不可※"
                isEditing={false}
                readOnly={true}
              />
            </div>
          </div>

          {/* ▼30分値登録状況セクション */}
          {showUploadTable && (
            <div>
              <SectionTitle>▼電力30分値登録状況</SectionTitle>
              <PageableTable
                columns={columns}
                data={uploadRecords}
                totalCount={uploadRecords.length}
                pageCount={Math.ceil(uploadRecords.length / 10)}
                pageSizeOptions={[5, 10, 20, 50]}
                renderRow={(record, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <p className="text-left">{record.startMonth}</p>
                    </TableCell>
                    <TableCell>{record.endMonth}</TableCell>
                    <TableCell>{record.fileUpdateDate}</TableCell>
                  </TableRow>
                )}
              />
            </div>
          )}
        </Form>
        {loading && (
          <div className="fixed inset-0 bg-white/60 flex items-center justify-center z-[9999]">
            <LoadingSpinner height="" />
          </div>
        )}
      </div>

      <AlertModal
        isOpen={confirmModalState.isOpen}
        onClose={() => {
          if (loading) return;
          setConfirmModalState({ ...confirmModalState, isOpen: false });
        }}
        onConfirm={async () => {
          if (loading) return;
          setLoading(true);
          if (confirmModalState.onConfirm) {
            await confirmModalState.onConfirm();
          }
          setLoading(false);
          setConfirmModalState({ ...confirmModalState, isOpen: false });
        }}
        title="登録の確認"
        description="電力30分値を登録します。よろしいですか？"
        cancelText="いいえ"
        continueText="はい"
        className="w-[400px] h-[180px]"
      />
    </MasterLayout>
  );
}
