import { createContext, useContext } from "react";

export type EbConsentSelection = {
  agreementCategory: string;
  orgId: string;
};

const EbConsentSelectionContext = createContext<EbConsentSelection | null>(null);

export const EbConsentSelectionProvider = EbConsentSelectionContext.Provider;

export const useEbConsentSelection = (): EbConsentSelection => {
  const ctx = useContext(EbConsentSelectionContext);
  if (!ctx) {
    // CommonLayout で Provider していない場合に気づけるように
    return { agreementCategory: "", orgId: "" };
  }
  return ctx;
};
