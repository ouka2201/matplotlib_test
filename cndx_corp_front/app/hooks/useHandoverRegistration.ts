import { useRef, useState } from "react";
import { useSession } from "~/components/layout/session-provider";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { HANDOVER_TYPE_INDIVIDUAL } from "~/constants/handover";
import { HANDOVER_MESSAGES } from "~/constants/messages/handover";
import { postData } from "~/lib/fetch";
import type { HandoverState } from "~/types/screen/management/mgmg05";

export function useHandoverRegistration() {
  const { session } = useSession();
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const isSubmitting = useRef(false);

  const registerHandover = async (input: HandoverState): Promise<boolean> => {
    if (isSubmitting.current) return false;
    const user = session?.authorityInfo;
    if (!user?.user_id || !user.org_id) {
      setErrorMessage(HANDOVER_MESSAGES.MISSING_SESSION);
      return false;
    }
    const url = input.handover_type === HANDOVER_TYPE_INDIVIDUAL
      ? API_ENDPOINTS.CONTACT_PERSON.API_INDIVIDUAL_HANDOVER
      : API_ENDPOINTS.CONTACT_PERSON.API_INCLUSIVE_HANDOVER;
    isSubmitting.current = true;
    setIsSaving(true);
    setErrorMessage("");
    try {
      await postData(url, {
        ...input.handover,
        handover_type: input.handover_type,
        user_id: user.user_id,
        org_id: user.org_id,
      });
      return true;
    } catch (cause) {
      setErrorMessage(cause instanceof Error ? cause.message : HANDOVER_MESSAGES.FAILED);
      return false;
    } finally {
      isSubmitting.current = false;
      setIsSaving(false);
    }
  };

  return { isSaving, errorMessage, registerHandover };
}
