import { useEffect } from "react";
import { useNavigate } from "@remix-run/react";
import { useSession } from "./session-provider";
import { toast } from "../ui/use-toast";

export default function useIdleLogout(timeout = 30 * 60 * 1000) {  // 30分
  const navigate = useNavigate();
  const {clearSession} = useSession()

  useEffect(() => {
    let timer: NodeJS.Timeout;

    const resetTimer = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        clearSession();
        sessionStorage.removeItem("session");
        sessionStorage.removeItem("isAuthenticated");
        sessionStorage.removeItem("token");
        
        // ログアウト完了画面にリダイレクト
        navigate("/auth/logout");
        toast({
          title: "30分無操作でログアウトしました",
        });
      }, timeout);
    };

    // ユーザーの操作を監視
    window.addEventListener("mousemove", resetTimer);
    window.addEventListener("keydown", resetTimer);
    window.addEventListener("click", resetTimer);

    resetTimer();  // 初回実行

    return () => {
      clearTimeout(timer);
      window.removeEventListener("mousemove", resetTimer);
      window.removeEventListener("keydown", resetTimer);
      window.removeEventListener("click", resetTimer);
    };
  }, [navigate, timeout, clearSession]);
}
