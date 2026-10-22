import { jwtDecode } from "jwt-decode";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMenu } from "~/components/layout/menu-provider";
import { AuthJwtPayload, useSession } from "~/components/layout/session-provider";
import { useToast } from "~/components/ui/use-toast";
import { Messages } from "~/constants/messages/message";
import { getData } from "~/lib/fetch";
import LoginErrorPage from "./login-error";

export default function UserInfoInit() {
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { updateSession } = useSession();
  const { updateNaviItems } = useMenu();
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    // リロード時にsessionStorageからエラーメッセージを取得
    const savedError = sessionStorage.getItem("userInfoInitErrorMessage");
    if (savedError) {
      console.log("[auth.user_info_init.tsx] リロード時に保存されたエラーメッセージを取得:", savedError);
      setError(savedError);
      setIsLoading(false);
      return;
    }

    console.log("[auth.user_info_init.tsx] useEffect実行開始");

    const handleUserInfoInit = async () => {
      try {
        setError(null);
        setIsLoading(true);

        // バックエンドAPIでユーザー情報を初期化
        const data = await getData("/api/auth/user_info_init");
        console.log("[auth.user_info_init.tsx] 取得したデータ:", data);

        // レスポンスが成功しているか確認
        if (data && data.status === "ok" && data.token) {
          // JWTトークンをデコード
          const decoded = jwtDecode<AuthJwtPayload>(data.token);
          const isAdminOrg = (orgId: string) =>
            ["TEP", "SYS"].includes(orgId.slice(0, 3));
          // セッション情報を保存
          updateSession({
            name: decoded.name,
            email: decoded.user_id,
            org_name: decoded.org_name,
            token: data.token,
            session_id: data.session_id,
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
            refreshToken: data.refreshToken,
            masterData: data.master,
          });

          // ナビゲーションアイテムを更新
          updateNaviItems(decoded.authority_code_map);

          // ログイン成功後、認証済みフラグを設定
          sessionStorage.setItem("isAuthenticated", "true");
          // tokenもsessionStorageに保存（_index.tsxのチェックで必要）
          sessionStorage.setItem("token", data.token);
          // エラーメッセージをクリア（成功時）
          sessionStorage.removeItem("userInfoInitErrorMessage");

          // SAML削除対応 Start
          // toast({
          //   description: "SAML認証成功",
          // });
          // SAML削除対応 End

          // トップページにリダイレクト（フルページリロードで確実に状態を反映）
          setIsLoading(false);
          navigate("/common/cmtp01");
          return;
        }

        // エラーレスポンスの場合
        // SAML削除対応 Start
        // setError(data?.message || Messages.login.saml_response_failed);
        setError(data?.message);
        // SAML削除対応 End
        setIsLoading(false);
      } catch (error: any) {
        console.error("[auth.user_info_init.tsx] ユーザー情報初期化エラー:", error);
        
        // セッション情報をクリア
        sessionStorage.clear();
        try {
          localStorage.clear();
        } catch {}
        
        // Cookieもクリア
        try {
          document.cookie.split(";").forEach((c) => {
            document.cookie = c
              .replace(/^ +/, "")
              .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
          });
        } catch {}
        
        // エラーメッセージを取得（APIから渡されたメッセージ）
        // SAML削除対応 Start
        // const errorMessage = error?.data?.message || error?.message || Messages.login.saml_response_error;
        const errorMessage = error?.data?.message || error?.message
        // SAML削除対応 End
        // エラーメッセージをsessionStorageに保存（リロード時も表示できるようにする）
        sessionStorage.setItem("userInfoInitErrorMessage", errorMessage);
        setError(errorMessage);
        setIsLoading(false);
      }
    };

    handleUserInfoInit();
  }, [navigate]);

  if (error) {
    const defaultmsg = "入力されたアカウント情報とログイン先のサービスとの連携に問題があります。"
    sessionStorage.removeItem("userInfoInitErrorMessage");
    return <LoginErrorPage messages={[defaultmsg]} />;
  }

  if (isLoading) {
    return (
      <div className="p-4 flex justify-center items-center text-gray-500 text-sm">
        <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin mr-2"></div>
        認証情報を初期化しています...
      </div>
    );
  }

  return null;
}
