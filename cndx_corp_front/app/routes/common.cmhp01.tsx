import React, { useEffect, useState } from "react";
import Icon from "~/components/icon";
import MasterLayout from "~/components/layout/master-layout";
import Text from "~/components/text";
import { Button } from "~/components/ui";
import { toast } from "~/components/ui/use-toast";
import { Messages } from "~/constants/messages/message";
import { useRoleFlags } from "~/hooks/useRoleFlags";
import { getData } from "~/lib/fetch";

type Availability = Record<string, boolean>;

const FullScreenSpinner = () => {
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-white/60">
      <div className="flex items-center gap-2 text-gray-500 text-sm">
        <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin" />
        処理中...
      </div>
    </div>
  );
};

const HelpPage: React.FC = () => {
  const [availability, setAvailability] = useState<Availability>({});
  const [isLoading, setIsLoading] = useState(true);
  const { isEpAdmin, isEpGeneral, isTcs, isRep, isBankUser } = useRoleFlags();
  const shouldShowEP = isEpAdmin || isEpGeneral;
  const shouldShowTCS = isEpAdmin || isTcs;
  const shouldShowREP = isEpAdmin || isRep;
  const shouldShowFinancial = isEpAdmin || isBankUser;
  const [isDownloading, setIsDownloading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");

  useEffect(() => {
    const fetchAvailability = async () => {
      try {
        const data = await getData("/api/help/availability"); // Record<string, boolean>型
        setAvailability(data);
      } catch (e) {
        console.error("ファイルのダウンロード可不可チェックで失敗しました", e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAvailability();
  }, []);

  const handleDownload = async (endpoint: string) => {
    // ダウンロード開始時にローディングスピナーを表示
    setIsDownloading(true);

    try {
      const response = await getData(`/api/help/${endpoint}`);

      // Responseオブジェクトでない場合はエラー
      if (!(response instanceof Response)) {
        console.error(Messages.help.invalid_dounload_response, response);
        throw new Error(Messages.help.invalid_dounload_response + typeof response);
      }

      // blob()を呼び出す前にヘッダーを読み取る
      const cd = response.headers.get("content-disposition");

      // Content-Dispositionヘッダーからファイル名を取得（APIから渡されたものをそのまま使用）
      let fileName: string | null = null;
      if (cd) {
        // filename*=UTF-8''形式を優先的にチェック（RFC 5987形式）
        const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(cd);
        if (utf8Match) {
          fileName = decodeURIComponent(utf8Match[1]);
        } else {
          // filename="..."形式をチェック（クォート付き）
          const quotedMatch = /filename="([^"]+)"/i.exec(cd);
          if (quotedMatch) {
            fileName = decodeURIComponent(quotedMatch[1]);
          } else {
            // filename=...形式をチェック（クォートなし）
            const unquotedMatch = /filename=([^;]+)/i.exec(cd);
            if (unquotedMatch) {
              fileName = decodeURIComponent(unquotedMatch[1].trim());
            }
          }
        }
      }

      // ファイル名が取得できない場合はエラー
      if (!fileName) {
        setErrorMessage(Messages.help.file_name_error);
        return;
      }

      // Responseオブジェクトからblobを取得
      const blob = await response.blob();

      // ダウンロード処理
      const urlObject = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = urlObject;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(urlObject);
      toast({
        title: "ダウンロード成功",
        // description: Messages.help.dounload_success,
        type: "success",
        duration: 3000,
      });
    } catch (error: any) {
      console.error(Messages.help.file_download_failed, error);
      const errorMessage = error?.data?.message || error?.message || Messages.help.file_download_failed;
      setErrorMessage(errorMessage);
    } finally {
      // 成功・失敗に関わらずローディングスピナーを非表示
      setIsDownloading(false);
    }
  };

  const isEnabled = (key: string) => availability[key] === true;

  return (
    <MasterLayout breadcrumbItems={[{ title: "マニュアル・同意書", link: "" }]}>
      {/* エラーメッセージ */}
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
              <div className="text-[#d92d20] text-[14px]">
                {errorMessage}
              </div>
            )}
          </div>
        </div>
      )}
      {isDownloading && <FullScreenSpinner />}
      {isLoading ? (
        <div className="p-4 flex justify-center items-center text-gray-500 text-sm">
          <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin mr-2"></div>
          読み込み中...
        </div>
      ) : (
        <div className="mt-5">
          <ul className="list-disc pl-6 space-y-5">
            {/* EP */}
            {shouldShowEP && (
              <li>
                {/* 東京電力エナジーパートナー株式会社 */}
                <div className="text-lg font-bold text-[#1d2939] leading-6 mb-2">
                  東京電力エナジーパートナー株式会社
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="second"
                    size="default"
                    disabled={!isEnabled("manual_EP") || isDownloading}
                    onClick={() => handleDownload("manual_EP")}
                  >
                    マニュアル
                  </Button>
                  <Button
                    variant="second"
                    size="default"
                    disabled={!isEnabled("consent_form_EP") || isDownloading}
                    onClick={() => handleDownload("consent_form_EP")}
                  >
                    データ提供同意書(ミドル)
                  </Button>
                </div>
              </li>
            )}

            {/* TCS */}
            {shouldShowTCS && (
              <li>
                {/* テプコカスタマーサービス株式会社 */}
                <div className="text-lg font-bold text-[#1d2939] leading-6 mb-2">
                  テプコカスタマーサービス株式会社
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="second"
                    size="default"
                    disabled={!isEnabled("manual_TCS") || isDownloading}
                    onClick={() => handleDownload("manual_TCS")}
                  >
                    マニュアル
                  </Button>
                </div>
              </li>
            )}

            {/* REP */}
            {shouldShowREP && (
              <li>
                {/* REP */}
                <div className="text-lg font-bold text-[#1d2939] leading-6 mb-2">
                  REP
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="second"
                    size="default"
                    disabled={!isEnabled("manual_REP") || isDownloading}
                    onClick={() => handleDownload("manual_REP")}
                  >
                    マニュアル
                  </Button>
                  <Button
                    variant="second"
                    size="default"
                    disabled={!isEnabled("consent_form_REP") || isDownloading}
                    onClick={() => handleDownload("consent_form_REP")}
                  >
                    データ提供同意書(ミドル)
                  </Button>
                </div>
              </li>
            )}

            {/* 金融機関 */}
            {shouldShowFinancial && (
              <li>
                {/* 金融機関 */}
                <div className="text-lg font-bold text-[#1d2939] leading-6 mb-2">
                  金融機関
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="second"
                    size="default"
                    disabled={!isEnabled("manual_financial") || isDownloading}
                    onClick={() => handleDownload("manual_financial")}
                  >
                    マニュアル
                  </Button>
                  <Button
                    variant="second"
                    size="default"
                    disabled={!isEnabled("consent_form_financial") || isDownloading}
                    onClick={() => handleDownload("consent_form_financial")}
                  >
                    データ提供同意書
                  </Button>
                </div>
              </li>
            )}
          </ul>
        </div>
      )}
    </MasterLayout>
  );
};

export default HelpPage;
