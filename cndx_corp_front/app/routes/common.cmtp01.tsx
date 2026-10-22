import React, { useEffect, useState } from "react";
import MasterLayout from "~/components/layout/master-layout";
import { ScrollArea } from "~/components/ui/scroll-area";
import { getData } from "~/lib/fetch";
import { jwtDecode } from "jwt-decode";
import { useMenu } from "~/components/layout/menu-provider";
import { AuthJwtPayload, useSession } from "~/components/layout/session-provider";

type AnnouncementItem = {
  title: string;
  message1: string;
  message2: string;
  message3: string;
  start_date: string;
};

const AnnouncementPage: React.FC = () => {
  
  const { updateSession } = useSession();
  const { updateNaviItems } = useMenu();
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);

  useEffect(() => {
    const handleUserInfoInit = async () => {
        try {
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
  
            return;
          }
  
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
        }
      };
  
    const fetchData = async () => {
      try {
        const res = await getData("/api/announcements/inquiry");
        setAnnouncements(res ?? []);
      } catch (e) {
        console.error("お知らせ取得失敗", e);
      }
    };
    
    const init = async () => {
      try {
        // const isAuth = sessionStorage.getItem("isAuthenticated");

        // if (!isAuth) {
        //   await handleUserInfoInit();   // ← ちゃんと待つ
        // }

        const res = await getData("/api/announcements/inquiry");
        setAnnouncements(res ?? []);

      } catch (e) {
        console.error("初期化 or お知らせ取得失敗", e);
      }
    };
    init();
  }, []);

  return (
    <MasterLayout breadcrumbItems={[{ title: "お知らせ", link: "" }]}>
      <div className="w-full h-full bg-white m-0 p-0">
        <ScrollArea className="h-[calc(100vh-140px)] w-full pr-4">
          <div className="flex flex-col divide-y divide-gray-300 px-6 pb-8">
            {announcements.length === 0 ? (
              <p className="text-muted-foreground py-4">お知らせはありません</p>
            ) : (
              announcements.map((item, index) => (
                <div key={index} className="py-4">
                  <div className="text-sm text-muted-foreground mb-1 whitespace-pre-wrap break-words">
                    {item.start_date}
                  </div>
                  <div className="font-medium text-base whitespace-pre-wrap break-words">
                    {item.title}
                  </div>
                  <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-line">
                    {item.message1}
                    {item.message2 && `\n${item.message2}`}
                    {item.message3 && `\n${item.message3}`}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </MasterLayout>
  );
};

export default AnnouncementPage;
