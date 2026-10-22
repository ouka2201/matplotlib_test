// hooks/useAuthority.tsx
import React, {
    createContext,
    useContext,
    useEffect,
    useState,
    useMemo,
    ReactNode,
  } from "react";
import { SessionAuthorityInfo, SessionState, useSession } from "~/components/layout/session-provider";
  
  type AuthorityInfo = {
    orgId: string | null;
    orgTypeCode: string | null;
    userRole: string | null;
    authCodeMap: Record<string, string> | null;
  };
  
//   const AuthorityContext = createContext<AuthorityInfo | null>(null);
  
//   export const AuthorityProvider = ({
//     children,
//   }: {
//     children: ReactNode;
//   }) => {
//     const [authority, setAuthority] = useState<AuthorityInfo>({
//       orgId: null,
//       orgTypeCode: null,
//       userRole: null,
//       authCodeMap: null,
//     });
//     const { session} = useSession();
  
//     useEffect(() => {
        
//       const authorityInfo = session?.authorityInfo;
  
//       if (authorityInfo) {
//         setAuthority({
//           orgId: authorityInfo.org_id ?? null,
//           orgTypeCode: authorityInfo.org_type_code ?? null,
//           userRole: authorityInfo.user_role ?? null,
//           authCodeMap: authorityInfo.authority_code_map ?? null,
//         });
//       } else if (typeof window !== "undefined") {
//         const sessionData = sessionStorage.getItem("session");
//         if (sessionData) {
//           try {
//             const parsed = JSON.parse(sessionData);
//             setAuthority({
//               orgId: parsed.orgId ?? null,
//               orgTypeCode: parsed.orgTypeCode ?? null,
//               userRole: parsed.userRole ?? null,
//               authCodeMap: parsed.authCodeMap ?? null,
//             });
//           } catch (e) {
//             console.error("Failed to parse sessionStorage data", e);
//           }
//         }
//       }
//     }, [session]);
  
//     return (
//       <AuthorityContext.Provider value={authority}>
//         {children}
//       </AuthorityContext.Provider>
//     );
//   };

  export const useAuthority = (session: SessionState | null) => {
    const authorityInfo: SessionAuthorityInfo | undefined = session?.authorityInfo;
  
    const orgId = authorityInfo?.org_id ?? null;
    const orgTypeCode = authorityInfo?.org_type_code ?? null;
    const userRole = authorityInfo?.role ?? null;
    const authCodeMap = authorityInfo?.authority_code_map ?? null;
  
    const isEP = orgTypeCode === "01";
    const isBank = orgTypeCode === "02";
    const isBankBranch = orgTypeCode === "03";
    const isREP = orgTypeCode === "04";
    const isTCS = orgTypeCode === "05";
    const isVis = orgTypeCode === "06"; 
    const isSYS = orgTypeCode === "07";
  
    const userTypeMap: Record<string, boolean> = {
      EP: isEP,
      BANK: isBank,
      BANK_BRANCH: isBankBranch,
      REP: isREP,
      TCS: isTCS,
      VIS: isVis,
      SYS: isSYS,
    };
  
    const getUserType = (key: keyof typeof userTypeMap): boolean => {
      return userTypeMap[key] ?? false;
    };
  
    const getAccessibleScreens = () => {
      if (!authCodeMap) return [];
      return Object.entries(authCodeMap)
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        .filter(([_, value]) => value.authority_code === "0")
        .map(([key]) => key);
    };
  
    const getRestrictedScreens = () => {
      if (!authCodeMap) return [];
      return Object.entries(authCodeMap)
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        .filter(([_, value]) => value.authority_code === "1")
        .map(([key]) => key);
    };
    
    // 編集可能かどうかの判定
    const canEdit = (targetOrgId: string | null) => {
      if (!orgId || !targetOrgId) return false;
      return orgId === targetOrgId;
    };
  
    const isAdminRole = () => userRole === "0";
    const isNormalRole = () => userRole === "1";
    const isParentRole = () => userRole === "9";
  
    const hasScreenAccess = (screenCode: string) => {
        return authCodeMap?.some(
          (perm) => perm.authority_id === screenCode && perm.authority_id === "0"
        );
      };
  
    return {
      orgId,
      orgTypeCode,
      userRole,
      authCodeMap,
      isEP,
      isBank,
      isBankBranch,
      isREP,
      isTCS,
      isSYS,
      isVis,
      getUserType,
      getAccessibleScreens,
      getRestrictedScreens,
      canEdit,
      isAdminRole,
      isNormalRole,
      isParentRole,
      hasScreenAccess,
    };
  };
  
  
  