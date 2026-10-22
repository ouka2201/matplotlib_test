import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LoadingSpinner } from "~/components/common/loadingSpinner";
import { Icons } from "~/components/icons";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import { useConsentRoutes } from "~/hooks/useConsentRoutes";
import { useEbConsentSelection } from "~/hooks/useEbConsentSelection";
import { useRoleFlags } from "~/hooks/useRoleFlags";
import { postData } from "~/lib/fetch";
import ItemPair from "../components/itemPair";
import { SessionAuthorityInfo, useSession } from "../components/layout/session-provider";
import CustomDialog from "../components/modal/common-dialog";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger } from "../components/ui/select";
import { Messages } from "../constants/messages/message";
import { CdNmOption } from "../types/screen/master/mscs/mscsType";

interface CustomerCompanyList {
  company_name: string;
  company_name_kana: string;
  corporate_number: string;
}

interface UploadDataProps {
  data: CustomerCompanyList[];
  modalOpen: boolean;
  onOpenChange: (open: boolean) => void;
  uploadFileType: string;
  onUploadComplete?: () => void;
}

// type UploadResponse = {
//   status: number;
//   upload_flg: boolean;
//   error_message: string;
// };

type ModalType = "upload" | "confirm" | "complete";

const EXTENSION_LIST = [".xlsx", ".xlsm"];

const UploadData: React.FC<UploadDataProps> = ({ data, modalOpen, onOpenChange, uploadFileType, onUploadComplete }) => {
  const navigate = useNavigate();
  const [modalType, setModalType] = useState<ModalType>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [isFileReadyForUpload, setIsFileReadyForUpload] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fileErrorDetail, setFileErrorDetail] = useState<string[]>([]);
  const [aggreeCategoryList, setAggreeCategoryList] = useState<CdNmOption[]>();
  const [selectedAgreementRoute, setSelectedAgreementRoute] = useState<string>("");
  const [fileCompanyName, setFileCompanyName] = useState<string | null>(null);
  const [confirmMessage, setConfirmMessage] = useState<string | null>(null);
  const [uploadFlg, setUploadFlg] = useState(false);
  const [isUploadSuccess, setIsUploadSuccess] = useState(false);

  const [modalDescription, setModalDescription] = useState("");
  const [uploadExcelFile, setUploadExcelFile] = useState("");
  const [uploadType, setUploadType] = useState("");
  const [formDataState, setFormDataState] = useState<FormData | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [isAwaitingFileSelection, setIsAwaitingFileSelection] = useState(false);

  // TODO: 可視化事業者がログインした際はログインしたアカウントに紐づく会社名を表示するよう修正
  const companyName = data[0]?.company_name ?? "東京電力エナジーパートナー株式会社";
  const corporateNumber = data[0]?.corporate_number ?? "0000000000222";

  useEffect(() => {
    // 登録するファイルの種類によって、モーダル内の文言を変化させる
    // TODO: APIの呼び出しの実装
    const dataTypes = {
      energy: {
        type: "energy",
        description: "エネルギーデータアップロード",
        file: "",
      },
      hearing: {
        type: "hearing",
        description: "ヒアリングデータアップロード",
        file: "",
      },
      buildingMaster: {
        type: "buildingMaster",
        description: "拠点マスタファイルアップロード",
        file: "拠点マスタ",
        orgType: "1",
      },
    };
    const upload_type = dataTypes[uploadFileType as keyof typeof dataTypes];
    if (upload_type) {
      setUploadType(upload_type.type);
      setModalDescription(upload_type.description);
      setUploadExcelFile(upload_type.file);
    }
  }, [uploadFileType]);

  const { session, clearSession } = useSession();
  const [token, setToken] = useState<string | null>(session?.token ?? null);
  // const { isVis } = useAuthority(session);
  const { isVis } = useRoleFlags();
  const [authorityInfo, setAuthorityInfo] = useState<SessionAuthorityInfo | null>(session?.authorityInfo ?? null);
  const { agreementCategory } = useEbConsentSelection();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
        setAuthorityInfo(JSON.parse(sessionData).authorityInfo);
      }
    }
  }, [session]);

  useEffect(() => {
    if (!token || uploadType != "buildingMaster") return;
    let isCancelled = false;
    // const masterEntries = createMasterEntries(uploadType, isVis, authorityInfo);
    const masterEntries = createMasterEntries();
    const fetchMaster = async () => {
      try {
        const data = await getMasterDataForCondition(masterEntries, token);
        if (!isCancelled) {
          setAggreeCategoryList(data["consent-route"]);
        }
      } catch (err) {
        if (!isCancelled) {
          console.error(Messages.VALIDATION.data.fetch_master_error, err);
        }
      }
    };
    fetchMaster();

    return () => {
      isCancelled = true;
    };
  }, [token, uploadType, isVis, authorityInfo]);

  useEffect(() => {
    if (!modalOpen) return;
    if (!token) return;
    if (uploadType === "buildingMaster") return; // buildingMaster は従来通り

    // CommonLayout の選択が未確定なら空にして、アップロード不可にする
    setSelectedAgreementRoute(agreementCategory ?? "");
  }, [modalOpen, token, uploadType, agreementCategory]);

  // 同意書取得経路取得
  const routes = useConsentRoutes(token, corporateNumber, authorityInfo?.org_id);
  useEffect(() => {
    if (!token || uploadType == "buildingMaster") return;
    setAggreeCategoryList(routes);
    // let isCancelled = false;
    // const fetchMaster = async () => {
    //   try {
    //     const url = `/api/corp/basic-info?corporate_number=${corporateNumber}`;
    //     const response = await getData(url);
    //     let list = response.result_list as {
    //       agreement_category: string;
    //       agreement_name: string;
    //       org_id: string;
    //     }[];
    //     if (isVis) {
    //       list = list.filter((item) => item.org_id === authorityInfo?.org_id);
    //     }
    //     const uniqueOptions = Array.from(
    //       new Map(list.map((item) => [item.agreement_name, item])).values()
    //     );
    //     const options = uniqueOptions.map((item) => ({
    //       id: item.agreement_category,
    //       name: item.agreement_name,
    //     }));
    //     if (!isCancelled) {
    //       setAggreeCategoryList(options);
    //     }
    //   } catch (err) {
    //     if (!isCancelled) {
    //       console.error(Messages.VALIDATION.data.fetch_master_error, err);
    //     }
    //   }
    // };
    // fetchMaster();

    // return () => {
    //   isCancelled = true;
    // };
  }, [token, corporateNumber, isVis, authorityInfo?.org_id, routes, uploadType]);

  const createMasterEntries = () =>
  // type: string,
  // isVis: boolean,
  // authorityInfo: { org_id?: string } | null
  {
    const params: Record<string, string> = {
      agreement_category__startswith: "1",
    };

    // if (type === "energy" && isVis && authorityInfo?.org_id) {
    //   params.org_id = authorityInfo.org_id;
    // }

    return [
      {
        name: "consent-route",
        params,
      },
    ];
  };

  useEffect(() => {
    // if (aggreeCategoryList && aggreeCategoryList.length === 1 && isVis) {
    if (uploadType === "buildingMaster" && aggreeCategoryList && aggreeCategoryList.length === 1 && isVis) {
      setSelectedAgreementRoute(aggreeCategoryList[0].id);
    }
  }, [aggreeCategoryList, isVis, uploadType]);

  const resetModalState = () => {
    setModalType("upload");
    setFile(null);
    setFileName(null);
    setErrorMessage(null);
    setFileCompanyName(null);
    setConfirmMessage(null);
    setUploadFlg(false);
    setIsFileReadyForUpload(false);
    setIsAwaitingFileSelection(false);
    // aggreeCategoryList && aggreeCategoryList.length === 1 && isVis
    //   ? setSelectedAgreementRoute(aggreeCategoryList[0].id)
    //   : setSelectedAgreementRoute("");
    if (uploadType === "buildingMaster") {
      aggreeCategoryList && aggreeCategoryList.length === 1 && isVis
        ? setSelectedAgreementRoute(aggreeCategoryList[0].id)
        : setSelectedAgreementRoute("");
    } else {
      setSelectedAgreementRoute(agreementCategory ?? "");
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setIsAwaitingFileSelection(false);
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) {
      if (!file) {
        setErrorMessage(Messages.VALIDATION.file.unselected);
      }
      setFile(null);
      setFileName(null);
      localStorage.removeItem("fileName");
      setIsFileReadyForUpload(false);
      return;
    }

    const ext = selectedFile.name.slice(selectedFile.name.lastIndexOf("."));

    setFile(selectedFile);
    setFileName(selectedFile.name);
    localStorage.setItem("fileName", selectedFile.name);
    if (!EXTENSION_LIST.includes(ext)) {
      setIsFileReadyForUpload(false);
      return setErrorMessage(Messages.VALIDATION.file.invalid);
    }
    setIsFileReadyForUpload(true);
    setErrorMessage(null);
  };

  const triggerFileSelectDialog = () => {
    setIsAwaitingFileSelection(true);
    fileInputRef.current?.click();
  };

  useEffect(() => {
    const handleWindowFocus = () => {
      if (!isAwaitingFileSelection) return;
      setIsAwaitingFileSelection(false);
      const hasCurrentSelection = Boolean(fileInputRef.current?.files?.length);
      if (!hasCurrentSelection && !file) {
        setErrorMessage(Messages.VALIDATION.file.unselected);
      }
    };
    window.addEventListener("focus", handleWindowFocus);
    return () => {
      window.removeEventListener("focus", handleWindowFocus);
    };
  }, [isAwaitingFileSelection, file]);

  // const handleUpload = async () => {
  //   // TODO: APIから取得した情報を用いるように修正
  //   const mock: UploadResponse = {
  //     status: 200,
  //     upload_flg: true,
  //     error_message: "",
  //   };
  //   setUploadFlg(mock.upload_flg);
  //   setFileCompanyName(companyName);
  //   setConfirmMessage(
  //     mock.status === 200 && mock.upload_flg && !mock.error_message
  //       ? "こちらのデータを登録してもよろしいですか？"
  //       : "確認できないエラーが発生しました。管理者に連絡してください。"
  //   );
  //   setModalType("confirm");
  // };

  const handleUpload = async () => {
    setLoading(true);
    const formData = new FormData();
    file && formData.append("file", file); // fileオブジェクトをFormDataに追加

    if (file) {
      formData.append("company_name", companyName);
      formData.append("agreement_category", selectedAgreementRoute);
      formData.append("file_type", uploadType);
      formData.append("corporate_number", corporateNumber);
      formData.append("target_year", "2023"); /* TODO 画面選択値、どこから取得 */

      setFormDataState(formData);
      // FormDataに追加されたすべての項目をループして確認
      // formData.forEach((value, key) => {
      //   console.log(`${key}: ${value instanceof File ? value.name : value}`);
      // });

      const checkApiUrl = `/api/building/vis/file-check/${uploadFileType}`;
      try {
        const response = await postData(checkApiUrl, {}, { Authorization: `Bearer ${token}` }, formData);
        const responseStatus = response.status;

        if (responseStatus == 200) {
          const head = response.message?.charAt(0);
          const body = response.message?.slice(1); // ← 最初の1文字を除外

          if (head === "c") {
            setConfirmMessage(Messages.data_upload.company_name_mismatch);
            const lines = body.trim().split("\n");
            setFileErrorDetail([body.trim()]);
            setFileCompanyName(lines[0] ?? null);
          } else {
            setConfirmMessage(Messages.data_upload.confirm);
            setFileCompanyName(response.message ?? null);
          }

          setModalType("confirm");
          setUploadFlg(true);
        }
      } catch (error: unknown) {
        console.error(Messages.VALIDATION.api.error, error);
        if (error instanceof Error) {
          const head = error.message?.charAt(0);
          const body =
            head === "f" || head === "d" || head === "b" || head === "c"
              ? error.message?.slice(1) // ← 最初の1文字がf,d,b,cならば1文字目を除外
              : error.message;

          if (head === "f") {
            setConfirmMessage(Messages.data_upload.format_error);
            setUploadFlg(false);
          } else if (head === "d") {
            setConfirmMessage(Messages.data_upload.data_error);
            setUploadFlg(false);
          } else if (head === "b") {
            setConfirmMessage(Messages.data_upload.location_error);
            setUploadFlg(false);
          } else if (head === "c") {
            setConfirmMessage(Messages.data_upload.company_name_mismatch);
            const lines = body.trim().split("\n");
            setFileCompanyName(lines[0] ?? null);
            setUploadFlg(true);
          }

          const errorList = body
            .split("<br>")
            .map((item: string) => item.trim())
            .filter((item: string) => item.length > 0);

          setFileErrorDetail(errorList);
          // ここは1つの文字列（改行付き）として保存
          // setFileErrorDetail([body.trim()]);
          setModalType("confirm");
          // if (isErrorWithStatus(error)) {
          if (error.status === 401) {
            clearSession();
            sessionStorage.removeItem("session");
            return window.location.href = "/session-expired";
          }
        }
      } finally {
        setLoading(false);
      }
    }
  };

  const handleRegister = async () => {
    if (!uploadFlg) return;
    setLoading(true);
    if (!formDataState) return;

    const apiUrl = `/api/building/energy-info-vis/info/regist/${uploadFileType}`;
    try {
      await postData(apiUrl, {}, { Authorization: `Bearer ${token}` }, formDataState);
      setIsUploadSuccess(true);
      setConfirmMessage(Messages.data_upload.confirm);
      setModalType("complete");
    } catch (error: any) {
      setIsUploadSuccess(false);
      setModalType("complete");
      setConfirmMessage(error.data?.message);
    } finally {
      setLoading(false);
    }
  };

  const handleModalClose = (open: boolean) => {
    if (loading) return;

    if (!open) {
      resetModalState();
    }
    onOpenChange(open);
    // 登録成功でモーダルを閉じた時のみリフレッシュ
    if (!open && modalType === "complete" && isUploadSuccess && onUploadComplete) {
      onUploadComplete();
    }
  };

  const renderModalContent = () => {
    if (modalType === "upload") {
      return (
        <>
          <div>
            <label htmlFor="agreement-route" className="block text-sm font-medium text-gray-700 mb-1">
              同意書取得経路
            </label>
            {/* <Select
              value={selectedAgreementRoute}
              onValueChange={setSelectedAgreementRoute}
              disabled={isVis && aggreeCategoryList?.length === 1}
            >
              <SelectTrigger>
                {aggreeCategoryList?.find((option) => option.id === selectedAgreementRoute)?.name ||
                  Messages.common.pulldown_default}
              </SelectTrigger>
              <SelectContent className="z-[9999]">
                {aggreeCategoryList === undefined ? (
                  <div>{Messages.AGREEMENT_CATEGORY.none}</div>
                ) : (
                  aggreeCategoryList.map((option) => (
                    <SelectItem key={option.id} value={option.id}>
                      {option.name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select> */}
            {uploadType !== "buildingMaster" ? (
              <div className="px-3 py-2 w-full rounded-md border bg-gray-100 text-gray-700">
                {aggreeCategoryList?.find((o) => o.id === selectedAgreementRoute)?.name ||
                  (selectedAgreementRoute ? selectedAgreementRoute : "—")}
              </div>
            ) : (
              <Select
                value={selectedAgreementRoute}
                onValueChange={setSelectedAgreementRoute}
                disabled={isVis && aggreeCategoryList?.length === 1}
              >
                <SelectTrigger>
                  {aggreeCategoryList?.find((option) => option.id === selectedAgreementRoute)?.name ||
                    Messages.common.pulldown_default}
                </SelectTrigger>
                <SelectContent className="z-[9999]">
                  {aggreeCategoryList === undefined ? (
                    <div>{Messages.AGREEMENT_CATEGORY.none}</div>
                  ) : (
                    aggreeCategoryList.map((option) => (
                      <SelectItem key={option.id} value={option.id}>
                        {option.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            )}
          </div>
          <div className="w-[620px] mt-6">
            <label className="block text-sm font-medium text-gray-700 mb-1">{uploadExcelFile} ファイル選択</label>
            <div className="relative w-full pb-12">
              <ItemPair label="ファイル名" content={fileName || Messages.VALIDATION.file.unselected} />
              <Button
                variant="secondary"
                onClick={triggerFileSelectDialog}
                disabled={loading}
                className="absolute bottom-0 right-0"
              >
                ファイル選択
              </Button>
              {errorMessage && <div className="text-red-500">{errorMessage}</div>}
            </div>
            <div>
              <input
                type="file"
                accept=".xlsx,.xlsm"
                ref={fileInputRef}
                onChange={handleFileChange}
                style={{ display: "none" }}
                disabled={loading}
              />
            </div>
          </div>
        </>
      );
    }

    const agreementLabel =
      aggreeCategoryList?.find((item) => item.id === selectedAgreementRoute)?.name ||
      Messages.AGREEMENT_CATEGORY.unselected;

    if (modalType === "confirm") {
      return (
        <div className="w-[620px]">
          <p className={`mb-4 ${!uploadFlg ? "text-red-600" : ""}`}>{confirmMessage}</p>
          <ItemPair label="同意書取得経路" content={agreementLabel} />
          {uploadFlg && (
            <>
              <ItemPair label="ファイルのお客さま名" content={fileCompanyName} />
              <ItemPair label="画面のお客さま名" content={companyName} />
            </>
          )}
          <ItemPair label="ファイル名" content={fileName || Messages.VALIDATION.file.unselected} />
          {!uploadFlg && (
            <>
              <ItemPair
                label="エラー内容"
                content={
                  <ul
                    className="font-sans text-base14 text-gray-dark font-normal list-disc pl-4 max-h-20 overflow-y-auto"
                    style={{ textUnderlineOffset: "3px" }}
                  >
                    {fileErrorDetail.map((detail, idx) => (
                      <li key={idx} className="whitespace-pre-line">
                        {detail}
                      </li>
                    ))}
                  </ul>
                }
              />
            </>
          )}
        </div>
      );
    }
    return isUploadSuccess ? (
      <div className="w-[620px]">
        <p className="mb-4">{Messages.data_upload.register_success}</p>
        <ItemPair label="同意書取得経路" content={agreementLabel} />
        <ItemPair label="お客さま名" content={fileCompanyName} />
        <ItemPair label="ファイル名" content={fileName || Messages.VALIDATION.file.unselected} />
      </div>
    ) : (
      <div className="w-[620px]">
        {/* <p className="mb-4">{Messages.data_upload.register_error}</p> */}
        <p className="mb-4 text-red-600 font-semibold">{confirmMessage}</p>
      </div>
    );
  };

  const isUploadButtonDisabled = loading || !isFileReadyForUpload || !selectedAgreementRoute;

  const renderFooter = () => {
    if (modalType === "upload") {
      return (
        <>
          <Button variant="second" onClick={() => handleModalClose(false)} disabled={loading}>
            戻る
          </Button>
          <Button variant="primary" onClick={handleUpload} disabled={isUploadButtonDisabled}>
            {loading && <Icons.spinner className="mr-2 size-4 animate-spin" aria-hidden="true" />}
            アップロード
          </Button>
        </>
      );
    }

    if (modalType === "confirm") {
      return (
        <>
          <Button variant="second" onClick={() => setModalType("upload")} disabled={loading}>
            戻る
          </Button>
          <Button
            variant="primary"
            onClick={handleRegister}
            disabled={loading || !uploadFlg}
          >
            登録する
          </Button>
        </>
      );
    }

    return (
      <>
        <Button variant="second" onClick={() => handleModalClose(false)}>
          OK
        </Button>
      </>
    );
  };

  return (
    <>
      <CustomDialog
        title={`お客さま名：${companyName}`}
        description={modalDescription}
        open={modalOpen}
        size="xl"
        className="w-fit h-fit"
        onOpenChange={handleModalClose}
        footer={renderFooter()}
      >
        <div className="relative">
          {renderModalContent()}

          {loading && (
            <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-50 rounded-lg h-">
              <LoadingSpinner height="" />
            </div>
          )}
        </div>
      </CustomDialog>
    </>
  );
};

export default UploadData;
