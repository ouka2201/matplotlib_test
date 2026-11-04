import type { MouseEvent } from "react";
import ErrorHint from "~/components/common/error-hint";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "~/components/ui/alert-dialog";
import { useToast } from "~/components/ui/use-toast";
import { HANDOVER_TYPE_BULK } from "~/constants/handover";
import { HANDOVER_MESSAGES } from "~/constants/messages/handover";
import { useHandoverRegistration } from "~/hooks/useHandoverRegistration";
import { handoverStateSchema } from "~/lib/validations/mgmg05";
import type { HandoverState } from "~/types/screen/management/mgmg05";

export type HandoverConfirmationModalProps = {
  isOpen: boolean;
  input: HandoverState;
  onClose: () => void;
  onRegistered?: () => void;
};

/** 呼び出し元が入力と開閉状態を保持し、登録後の再取得等はonRegisteredで行う。 */
export function HandoverConfirmationModal({
  isOpen,
  ...props
}: HandoverConfirmationModalProps) {
  // 閉じたときにモーダル内のエラーを破棄し、再表示時に持ち越さない。
  return isOpen ? <HandoverConfirmationContent {...props} /> : null;
}

function HandoverConfirmationContent({
  input,
  onClose,
  onRegistered,
}: Omit<HandoverConfirmationModalProps, "isOpen">) {
  const parsedInput = handoverStateSchema.safeParse(input);
  const { isSaving, errorMessage, registerHandover } = useHandoverRegistration();
  const { saveSuccessToast } = useToast();

  const handleSubmit = async (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    if (!parsedInput.success) return;
    const isRegistered = await registerHandover(parsedInput.data);
    if (isRegistered) {
      saveSuccessToast({ title: HANDOVER_MESSAGES.SUCCESS });
      onClose();
      onRegistered?.();
    }
  };

  return (
    <AlertDialog
      open
      onOpenChange={(isOpen) => {
        if (!isOpen && !isSaving) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{HANDOVER_MESSAGES.CONFIRM_TITLE}</AlertDialogTitle>
          <AlertDialogDescription>
            {parsedInput.success && parsedInput.data.handover_type === HANDOVER_TYPE_BULK
              ? HANDOVER_MESSAGES.CONFIRM_BULK
              : HANDOVER_MESSAGES.CONFIRM_INDIVIDUAL}
          </AlertDialogDescription>
        </AlertDialogHeader>
        {!parsedInput.success && <ErrorHint message={HANDOVER_MESSAGES.MISSING_INPUT} />}
        {errorMessage && <ErrorHint message={errorMessage} />}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSaving}>いいえ</AlertDialogCancel>
          <AlertDialogAction onClick={handleSubmit} disabled={isSaving || !parsedInput.success}>
            {isSaving ? "登録中..." : "はい"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
