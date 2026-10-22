import { Button } from "~/components/ui/button";

export function LogInButton() {
  const handleLogIn = () => {
    // セッションエラー画面から再ログインする場合は、セッション情報をクリア
    sessionStorage.removeItem("isAuthenticated");
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("session");
    sessionStorage.removeItem("refreshToken");

    // セッションエラー画面から再ログインする場合は、/ に遷移して認証初期化を実行
    // これにより、SAML認証または通常ログインの適切なフローが開始される
    window.location.href = "/";
  };

  return (
    <Button
      aria-label="Log in"
      size="sm"
      className="w-full"
      onClick={handleLogIn}
    >
      ログイン画面へ
    </Button>
  );
}
