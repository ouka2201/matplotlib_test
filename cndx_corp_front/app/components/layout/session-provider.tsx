import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { postData } from "~/lib/fetch";
import { logMessage } from "~/lib/logger";
import { Permission, useMenu } from "./menu-provider";
// import { useNavigate } from "react-router-dom";
import { jwtDecode, JwtPayload } from "jwt-decode";

export type SessionAuthorityInfo = {
  user_id: string;
  org_id: string;
  name: string;
  role: string;
  org_type_code: string;
  // authority_code_map: {
  //   [screen_id: string]: string; 
  // };
  authority_code_map: Permission[]
};

export type SessionUserRoleFlags = {
  isEpAdmin: boolean;
  isEpGeneral: boolean;
  isBank: boolean;
  isBranchAdmin: boolean;
  isBranchGeneral: boolean;
  isRepAdmin: boolean;
  isRepGeneral: boolean;
  isTcsAdmin: boolean;
  isTcsGeneral: boolean;
  isJfs: boolean;
  isZrb: boolean;
  isAse: boolean;
};

export interface AuthJwtPayload extends JwtPayload {
  user_id: string;
  email_address: string;
  org_id: string;
  name: string;
  org_name: string;
  role: string;
  org_type_code: string;
  authority_code_map: Permission[]
}
// export type CustomJwtPayload = JwtPayload & {
//   name: string;
//   role: string;
//   org_id: string;
//   org_type_code: string;
//   authority_code_map: SessionAuthorityInfo;
// };

type MasterData = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any[]; // マスターデータの型
};

export type SessionState = {
  name: string;
  email: string;
  org_name: string;
  token: string;
  selectedOrgId?: string | null;
  selectedAgreementCategory?: string | null;
  refreshToken?: string;
  session_id?: string; // セッションIDを追加
  csrf_access_token?: string;
  csrf_refresh_token?: string;
  masterData?: MasterData; // マスターデータを追加
  authorityInfo?: SessionAuthorityInfo;
  userRoleFlags?: SessionUserRoleFlags;
} | null;

type SessionValue = {
  session: SessionState;
  updateSession: (value: SessionState) => void;
  clearSession: () => void;
};

const defaultSessionValue = {
  session: null,
  updateSession: (value: SessionState) => { }, // eslint-disable-line @typescript-eslint/no-unused-vars
  clearSession: () => { },
};

const SessionContext = createContext(defaultSessionValue as SessionValue);

export const callRefreshTokenEndpoint = async (): Promise<{
  status: "ok" | "error";
  token?: string;
  refreshToken?: string;
}> => {
  const refreshToken = sessionStorage.getItem("refreshToken");
  if (!refreshToken) {
    return { status: "error" };
  }

  // const csrfToken = getCookie("csrf_refresh_token");

  try {
    const { status, token } = await postData("/api/auth/refresh",
      {}, {},
    );

    if ("error" === status) {
      throw new Error("Failed to refresh token");
    }
    return { status, token };
  } catch (error) {
    logMessage({ message: "Failed to refresh token", object: error });
    sessionStorage.removeItem("refreshToken");
    return { status: "error" };
  }
};

export const SessionProvider =
  ({ children, }: { children: React.ReactNode; }):
    JSX.Element => {
    const [session, setSession] = useState<SessionState>(null);

    // useEffect(() => {
    //   const data = sessionStorage.getItem("session");
    //   if (data) {
    //     setSession(JSON.parse(data));
    //   }
    // }, []);

    const { updateNaviItems } = useMenu();
    // const navigate = useNavigate();
    const isSessionChecked = useRef(false);

    // const decodeToken = (token: string) => {
    //   try {
    //     return JSON.parse(atob(token.split(".")[1]));
    //   } catch (error) {
    //     logMessage({ message: "Failed to decode token", object: error });
    //     return null;
    //   }
    // };

    // 画面リフレッシュ対応: 初回レンダリング時にセッションを復元
    useEffect(() => {
      if (isSessionChecked.current) return;

      // エラー画面とユーザー情報初期化画面ではトークンチェックをスキップ
      const currentPath = window.location.pathname;
      const isErrorPage = currentPath === "/session-user-status-error" ||
        currentPath === "/session-expired" ||
        currentPath === "/single-login-violation" ||
        currentPath === "/login-error";
      const isAuthUserInfoInit = currentPath === "/auth/user_info_init";
      if (isErrorPage || isAuthUserInfoInit) {
        logMessage({ message: "Error page or user info init page detected, skipping token check" });
        return;
      }

      isSessionChecked.current = true;

      const checkAndRefreshToken = async () => {
        try {

          // ★まずこのTabの sessionStorage からセッション復元（別Tabのcookie refreshに負けない）
          const storedSession = sessionStorage.getItem("session");
          if (storedSession) {
            try {
              const parsed = JSON.parse(storedSession);
              setSession(parsed);
              if (parsed?.authorityInfo?.authority_code_map) {
                updateNaviItems(parsed.authorityInfo.authority_code_map);
              }
              // tokenがあるなら refresh しない（multi-tabで別ユーザー同時利用するため）
              if (parsed?.token) return;
            } catch {
              // 破損してたら通常フローへ
            }
          }
          const { token, status } = await callRefreshTokenEndpoint();
          if (status == "ok" && token) {
            // const payload = decodeToken(token);
            // setSession({
            //   name: payload.name,
            //   email: payload.email,
            //   token,
            // });
            // const decoded = jwtDecode<JwtPayload>(token) as CustomJwtPayload;
            // setSession({
            //   name: decoded.name,
            //   email: decoded.email,
            //   token,
            // });
            // updateNaviItems(token);

            const decoded = jwtDecode<AuthJwtPayload>(token);
            const isAdminOrg = (orgId: string) =>
              ["TEP", "SYS"].includes(orgId.slice(0, 3));
            setSession({
              name: decoded.name,
              // email: decoded.user_id,
              email: decoded.email_address,
              org_name: decoded.org_name,
              token: token,
              authorityInfo: {
                user_id: decoded.name,
                org_id: decoded.org_id,
                name: decoded.name,
                role: decoded.role,
                org_type_code: decoded.org_type_code,
                authority_code_map: decoded.authority_code_map
              },
              userRoleFlags: {
                isEpAdmin: isAdminOrg(decoded.org_id) && decoded.role === "0",
                isEpGeneral: decoded.org_id.slice(0, 3) === "TEP" && decoded.role === "1",
                isBank: decoded.org_id.slice(0, 3) === "BNK" && decoded.role === "9",
                isBranchAdmin: decoded.org_id.slice(0, 3) === "BNK" && decoded.role === "0",
                isBranchGeneral: decoded.org_id.slice(0, 3) === "BNK" && decoded.role === "1",
                isRepAdmin: decoded.org_id.slice(0, 3) === "REP" && decoded.role === "0",
                isRepGeneral: decoded.org_id.slice(0, 3) === "REP" && decoded.role === "1",
                isTcsAdmin: decoded.org_id.slice(0, 3) === "TCS" && decoded.role === "0",
                isTcsGeneral: decoded.org_id.slice(0, 3) === "TCS" && decoded.role === "1",
                isJfs: decoded.org_id.slice(0, 3) === "JFS",
                isZrb: decoded.org_id.slice(0, 3) === "ZRB",
                isAse: decoded.org_id.slice(0, 3) === "ASE",
              },
            });

            // updateNaviItems(data.token);
            updateNaviItems(decoded.authority_code_map);

            logMessage({ message: "Refreshed token", object: { token } });
            // }else {
            //   logMessage({ message: "Failed to refresh token"});
            //   setSession(null);
            //   sessionStorage.removeItem("refreshToken");
            //   sessionStorage.removeItem("token");
            //   navigate("/auth")
          }
        } catch (error) {
          logMessage({ message: "Failed to refresh token", object: error });
          setSession(null);
          sessionStorage.removeItem("refreshToken");
          sessionStorage.removeItem("token");
          // navigate("/auth")
        }
      };

      // const storedSession = sessionStorage.getItem("session");
      // if (storedSession) {
      //   const parsedSession = JSON.parse(storedSession);
      //   setSession(parsedSession);
      //   accessToken = parsedSession.token;
      // } else {
      // }
      logMessage({ message: "SessionProvider mounted" });
      checkAndRefreshToken(); // 初回ロード時にトークン更新を試みる
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const clearSession = async () => {
      // try {
      //   // await deleteData("/api/auth/signout");
      //   const {status} = await postData("/api/auth/signout");
      //   if (status === "success") {
      //     console.log("Signed out successfully");
      //   }
      // } finally {
      setSession(null);
      sessionStorage.removeItem("refreshToken");
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("csrf_access_token");
      sessionStorage.removeItem("csrf_refresh_token");
      sessionStorage.removeItem("session");
    };

    const updateSession = async (value: SessionState) => {
      if (value) {
        const newSession = { ...session, ...value };
        setSession(newSession);
        // セッションストレージに保存
        sessionStorage.setItem("userRoleFlags", JSON.stringify(newSession.userRoleFlags!));
        sessionStorage.setItem("refreshToken", newSession.refreshToken!);
        sessionStorage.setItem("token", newSession.token!);
        if (newSession.session_id) {
          sessionStorage.setItem("session_id", newSession.session_id);
        }
        // sessionStorage.setItem("csrf_access_token", newSession.token!);
        // sessionStorage.setItem("csrf_refresh_token", newSession.token!);
        sessionStorage.setItem("name", newSession.name!);
        sessionStorage.setItem("email", newSession.email!);
        sessionStorage.setItem("org_name", newSession.org_name!);
        sessionStorage.setItem("session", JSON.stringify(newSession));
        // sessionStorage.setItem("mcode", JSON.stringify(newSession.masterData?.["M_CORP_CODE_INFO"]));
        // sessionStorage.setItem("m_prefecture", JSON.stringify(newSession.masterData?.["M_PREFECTURE"]));
        // 保存
        // await localforage.setItem("m_user", JSON.stringify(newSession.masterData?.["M_USER"]));
        // sessionStorage.setItem("m_user",JSON.stringify(newSession.masterData?.["M_USER"]));
        // sessionStorage.setItem("masterData", JSON.stringify(newSession.masterData)); // マスターデータも保存
      }
    };

    return (
      <SessionContext.Provider
        value={{
          session,
          updateSession,
          clearSession,
        }}
      >
        {children}
      </SessionContext.Provider>
    );
  };

// カスタムフックを作成してコンテキストにアクセスできるようにする
export const useSession = () => useContext(SessionContext);
