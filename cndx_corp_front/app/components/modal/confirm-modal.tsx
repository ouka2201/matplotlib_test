import { useEffect, useState } from "react";

import { Button } from "~/components/ui/button";
import { Modal } from "~/components/ui/modal";

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading?: boolean;
  title: string;
  description: string;
  cancelText: string;
  continueText: string;
  hideButtons: boolean;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  loading,
  title,
  description,
  cancelText,
  continueText,
  hideButtons,
}) => {
  const [isMounted, setIsMounted] = useState(false);

  // loading が false に変更されたときに少し遅延させてUIを更新
  useEffect(() => {
    if (loading === false) {
      // loading が false になったときに1秒待ってから isMounted を true にする
      setTimeout(() => {
        setIsMounted(true);
      }, 100); // 適切な遅延時間を設定（例：100ms）
    } else {
      setIsMounted(true); // loading が true の場合は即座に表示
    }
  }, [loading]);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return null;
  }

  // loading が true のときは onClose を無効にする
  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  return (
    <Modal
      title={title}
      description={description}
      isOpen={isOpen}
      onClose={handleClose} 
    >
      {/* メッセージ表示のみ(通知モード)では、continueText/cancelTextのボタンを表示しない */}
      {loading ? (
        <div className="flex items-center justify-center h-32 text-lg font-bold">
          処理中です...
        </div>
      ) : (
        !hideButtons && (
        <div className="flex w-full items-center justify-end space-x-2 pt-6">
          <Button disabled={loading} onClick={onConfirm}>
            {continueText}
          </Button>
          <Button disabled={loading} variant="outline" onClick={handleClose}>
            {cancelText}
          </Button>
        </div>
      ))}
    </Modal>
  );
};
