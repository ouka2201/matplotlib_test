import { VariantProps } from "class-variance-authority";
import { ReactNode, useState } from "react";
import { useNavigate } from "react-router-dom";
import BreadCrumb, { BreadCrumbType } from "~/components/common/breadcrumb";
import Footer from "~/components/common/footer";
import { buttonVariants } from "~/components/ui/button";
import { AlertModal } from "../modal/alert-modal";

type FooterType = "default" | "confirmation";

interface ButtonInfo {
  text: string;
  isLoading?: boolean;
  variant?: VariantProps<typeof buttonVariants>["variant"];
  size?: VariantProps<typeof buttonVariants>["size"];
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
}

interface LayoutProps {
  children: ReactNode;
  breadcrumbItems?: BreadCrumbType[];
  processClick?: () => Promise<void> | void;
  isEditing?: boolean;
  hasSidebar?: boolean;
  onCancelClick?: () => void;
  onDraftClick?: () => void;
  showCancelButton?: boolean;
  showDraftButton?: boolean;
  showRegisterButton?: boolean;
  showUpdateButton?: boolean;
  searchErrorMessage?: string | string[];
  errorMessage?: string | string[];
  footerType?: FooterType;
  internalModals?: boolean;
  onInlineRegister?: () => void;
  onInlineCancel?: () => void;
  onInlineDraft?: () => void;
  onClickError?: () => void;
  onUpdateClick?: () => void;
  useFullHeightLayout?: boolean;
  updateButtonText?: string;
  updateButtonDisabled?: boolean;
  registerButtonDisabled?: boolean;
  draftButtonDisabled?: boolean;
  confirmButtonDisabled?: boolean;
  cancelConfirmButtonDisabled?: boolean;
}

export default function MasterLayout({
  children,
  breadcrumbItems,
  isEditing = true,
  hasSidebar = true, //サイドバーの有無に合わせたフッター幅 {true}=サイドバー有 {false}=サイドバー無
  //登録,キャンセル,下書きフッター
  showCancelButton, //showCancelButton= {true} or {false} キャンセルボタン
  showDraftButton, //showDraftButton= {true} or {false} 下書きボタン
  showUpdateButton, //showUpdateButton= {true} or {false} 更新ボタン
  showRegisterButton, //showRegisterButton= {true} or {false} 登録ボタン
  updateButtonText, //更新ボタンテキスト
  updateButtonDisabled, //更新ボタンの非活性制御
  registerButtonDisabled, //登録ボタンの非活性制御
  draftButtonDisabled, //下書きボタンの非活性制御
  confirmButtonDisabled, //確認ボタン（この内容で登録）の非活性制御
  cancelConfirmButtonDisabled, //確認画面の内容を修正ボタンの非活性制御
  searchErrorMessage, //searchErrorMessage={searchErrorMessage} エラー表示(searchErrorMessageの場合)
  errorMessage, //errorMessage={errorMessage} エラー表示(errorMessageの場合)
  onClickError, //エラー内容押下した際の処理
  //モーダル有
  processClick, //登録
  onCancelClick, //キャンセル
  onDraftClick, //下書き
  onUpdateClick, //更新
  //モーダル無
  onInlineRegister, //登録,この内容で登録
  onInlineCancel, //キャンセル,内容を修正
  onInlineDraft, //下書き
  //内容を修正,この内容で登録フッター
  footerType = "default", //default(登録・下書き・キャンセル),confirmation(修正・登録)
  internalModals, //internalModals= {true} モーダル表示不必要
  useFullHeightLayout, //拠点エネルギー情報画面用フラグ
}: LayoutProps) {
  const navigate = useNavigate();

  const [pendingNavigation, setPendingNavigation] = useState<{
    link: string;
    state?: unknown;
    originalOnClick?: () => void;
  } | null>(null);

  const [showBreadcrumbConfirm, setShowBreadcrumbConfirm] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const handleConfirm = async () => {
    await processClick?.();
    setShowConfirm(false);
  };

  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const handleCancelConfirm = async () => {
    onCancelClick?.();
    setShowCancelConfirm(false);
  };

  const [showDraftConfirm, setShowDraftConfirm] = useState(false);
  const handleDraftConfirm = async () => {
    console.log("onDraftClick:", onDraftClick);
    onDraftClick?.();
    setShowDraftConfirm(false);
  };
  const [draftFlg, setDraftFlg] = useState(false);

  const buttons: ButtonInfo[] = [];

  if (footerType === "confirmation") {
    buttons.push(
      {
        text: "内容を修正",
        variant: "third",
        className: "ml-6",
        disabled: cancelConfirmButtonDisabled,
        onClick: () => {
          onInlineCancel?.();
        },
      },
      {
        text: confirmButtonDisabled
          ? (draftFlg ? "保存中" : "登録中")
          : (draftFlg ? "この内容で保存" : "この内容で登録"),
        variant: "primary",
        className: "mr-6",
        isLoading: confirmButtonDisabled,
        disabled: confirmButtonDisabled,
        onClick: () => {
          processClick?.();
        },
      },
    );
  } else {
    if (showCancelButton) {
      buttons.push({
        text: "キャンセル",
        variant: "third",
        className: "ml-6",
        onClick: () => setShowCancelConfirm(true),
      });
    }
    if (showDraftButton) {
      buttons.push({
        text: draftButtonDisabled ? "保存中" : "下書き保存",
        isLoading: draftButtonDisabled,
        variant: "second",
        className: "ml-2",
        disabled: draftButtonDisabled,
        onClick: () => {
          internalModals ? onInlineDraft?.() : setShowDraftConfirm(true);
          if (!draftButtonDisabled) {
            setDraftFlg(true);
          }
        },
      });
    }
    if (showRegisterButton) {
      buttons.push({
        text: registerButtonDisabled ? "登録中" : "登録",
        isLoading: registerButtonDisabled,
        variant: "primary",
        className: "mr-6",
        disabled: registerButtonDisabled,
        onClick: () => {
          if (internalModals) {
            onInlineRegister?.();
          } else {
            setShowConfirm(true);
          }
          setDraftFlg(false);
        }
      });
    }
    if (showUpdateButton) {
      buttons.push({
        text: updateButtonText ?? "更新",
        variant: "primary",
        className: "ml-2",
        disabled: updateButtonDisabled,
        onClick: () => onUpdateClick?.(),
      });
    }
  }

  const mergedErrorMessage = errorMessage ?? searchErrorMessage ?? [];
  // パンくずクリック時の処理
  const handleBreadcrumbClick = (item: BreadCrumbType) => {
    if (!item.link) return;

    // 編集画面のとき：まず確認モーダルを出す（onClick はまだ実行しない）
    if (showCancelButton) {
      setPendingNavigation({
        link: item.link,
        state: item.state,
        originalOnClick: item.onClick, // ← ここに元の onClick を保持
      });
      setShowBreadcrumbConfirm(true);
      return;
    }

    // 編集状態でない画面：そのまま遷移（onClick → navigate）
    item.onClick?.();
    navigate(item.link, { state: item.state });
  };

  // パンくずクリック時の確認モーダル
  // パンくず items をすべて MasterLayout 管理の onClick に差し替え
  const breadcrumbItemsWithConfirm =
    breadcrumbItems?.map((item) => ({
      ...item,
      onClick: () => handleBreadcrumbClick(item), // item ごと渡す
    })) ?? [];

  return (
    // <div
    //   className={`w-[calc(100%-220px)] absolute top-[72px] overflow-y-visible px-[16px] pb-10 flex-col  bg-[#f9fafb] h-fit ${useFullHeightLayout ? "h-screen" : ""
    //     }`}
    // >
    <div
      className={`px-[16px] bg-[#f9fafb] pt-[72px] ${
        useFullHeightLayout
          ? `flex w-full min-h-0 overflow-hidden mt-[45px]  ${isEditing ? "mb-[45px]" : ""}`
          : "pb-30 min-h-screen top-[72px] right-0 bottom-0 left-[220px]"
      }`}
    >
      {/* BreadCrumb (上部) */}
      {breadcrumbItems && <BreadCrumb items={breadcrumbItemsWithConfirm} />}

      {/* メインコンテンツ */}
      <div className={useFullHeightLayout ? "flex-grow min-h-0 overflow-hidden" : "flex-grow"}>{children}</div>

      {/* Footer (下部) - isEditingがtrueのときのみ表示 */}
      {((isEditing && (footerType === "confirmation" || buttons.length > 0)) || footerType === "confirmation") && (
        <Footer
          hasSidebar={hasSidebar}
          buttons={buttons}
          errorMessage={mergedErrorMessage}
          onClickError={onClickError}
          type={footerType}
        />
      )}

      <AlertModal
        isOpen={showCancelConfirm}
        onClose={() => setShowCancelConfirm(false)}
        onConfirm={() => handleCancelConfirm()}
        loading={false}
        title="入力内容の確認"
        description="入力内容が破棄されます。よろしいですか？"
        cancelText="いいえ"
        continueText="はい"
      />
      {/* パンくず遷移確認モーダル */}
      <AlertModal
        isOpen={showBreadcrumbConfirm}
        onClose={() => setShowBreadcrumbConfirm(false)}
        onConfirm={() => {
          if (pendingNavigation) {
            // ① 先実行：画面側で定義された onClick（例：setIsEditing(false)）
            pendingNavigation.originalOnClick?.();

            // ② その後に遷移
            navigate(pendingNavigation.link, {
              state: pendingNavigation.state,
            });

            // ③ 後始末
            setPendingNavigation(null);
            setShowBreadcrumbConfirm(false);
          }
        }}
        loading={false}
        title="入力内容の確認"
        description="入力内容が破棄されます。よろしいですか？"
        cancelText="いいえ"
        continueText="はい"
      />

      {/* showConfirmとshowDraftConfirm: どちらも!internalModalsのときだけ表示 */}
      {!internalModals && (
        <>
          <AlertModal
            isOpen={showDraftConfirm}
            onClose={() => setShowDraftConfirm(false)}
            onConfirm={() => handleDraftConfirm()}
            loading={false}
            title="確認"
            description="この内容で下書き保存してもよいですか？"
            cancelText="いいえ"
            continueText="はい"
          />
          <AlertModal
            isOpen={showConfirm}
            onClose={() => setShowConfirm(false)}
            onConfirm={() => handleConfirm()}
            loading={false}
            title="入力内容の確認"
            description="この入力内容で登録します。よろしいですか？"
            cancelText="いいえ"
            continueText="はい"
          />
        </>
      )}
    </div>
  );
}
