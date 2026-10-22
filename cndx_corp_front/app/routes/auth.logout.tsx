import { useNavigate } from "@remix-run/react";
import { useEffect } from "react";
import { getData } from "~/lib/fetch";
import {
  PageHeader,
  PageHeaderDescription,
  PageHeaderHeading,
} from "~/components/page-header";
import { Shell } from "~/components/shell";
// SAML削除対応 Start
// import { Button } from "~/components/ui/button";
// SAML削除対応 End

export default function LogoutPage() {
  // SAML削除対応 Start
  // const navigate = useNavigate();
  // SAML削除対応 End

  useEffect(() => {
    const handleUserInfoInit = async () => {
      await getData("/api/auth/signout");
    }
    // この画面では自動認証をスキップするため、ログアウトフラグを設定
    sessionStorage.setItem("logoutFlag", "true");

    // セッション情報を確実にクリア
    sessionStorage.removeItem("isAuthenticated");
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("session");
    handleUserInfoInit()
  }, []);

  // SAML削除対応 Start
  // const handleLogin = () => {
  //   // ログアウトフラグを削除してから通常の認証フローに遷移
  //   sessionStorage.removeItem("logoutFlag");
  //   navigate("/");
  // };
  // SAML削除対応 End

  return (
    <>
      <head>
        <title>ログアウト完了</title>
      </head>
      <div className="flex min-h-screen items-start justify-center pt-8 bg-gray-50">
        <Shell className="w-[350px]">
          <PageHeader
            id="logout-page-header"
            aria-labelledby="logout-page-header-heading"
            className="text-center"
          >
            <PageHeaderHeading size="sm">ログアウト完了</PageHeaderHeading>
            <PageHeaderDescription className="w-full">
              ログアウトしました。
            </PageHeaderDescription>
            <PageHeaderDescription className="w-full">
              ログインする場合は
            </PageHeaderDescription>
            <PageHeaderDescription className="w-full">
              TOP画面に再度アクセスしてください。
            </PageHeaderDescription>
            {/* SAML削除対応 Start
            <PageHeaderDescription className="w-full">
              再開する場合は再ログインしてください。
            </PageHeaderDescription>
            SAML削除対応 End */}
          </PageHeader>
          {/* SAML削除対応 Start
          <div className="mt-6 w-[350px]">
            <Button
              onClick={handleLogin}
              size="sm"
              className="w-full"
            >
              ログイン画面へ
            </Button>
          </div>
          SAML削除対応 End */}
        </Shell>
      </div>
    </>
  );
}

