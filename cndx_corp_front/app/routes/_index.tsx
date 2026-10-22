import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Index() {
  const navigate = useNavigate();

  useEffect(() => {
    // if (location.pathname === "/common/cmtp01") return;
    console.log("[_index.tsx] useEffect実行開始");
    
    // ログアウトフラグをチェック（ログアウト画面からの遷移時は自動認証をスキップ）
    const logoutFlag = sessionStorage.getItem("logoutFlag");
    if (logoutFlag === "true") { 
      if (location.pathname === "/") {
        sessionStorage.removeItem("logoutFlag")
        // navigate("/auth/signin")
        // window.location.href = "/common/cmtp01";
        setTimeout(() => {
          navigate("/auth/signin");
        }, 0);
        return
      }
      console.log("[_index.tsx] ログアウトフラグが設定されているため、自動認証をスキップ");
      // ログアウトフラグは削除せず、ログインボタンがクリックされた時に削除する
      return;
    }
    
    // 認証済みの場合はSAML認証を開始しない
    const isAuthenticated = sessionStorage.getItem("isAuthenticated") === "true";
    const hasToken = sessionStorage.getItem("token");
    
    if (isAuthenticated && hasToken) {
      console.log("[_index.tsx] 既に認証済みのため、認証をスキップしてトップページにリダイレクト");
      navigate("/auth/user_info_init");
      // navigate("/common/cmtp01");
      return;
    }

    // 認証初期化APIを呼び出して認証方式を判定
    const handleAuthInit = async () => {
      // root.tsxのロジックで/auth/signinへの直接アクセスを許可するため、フラグを設定
      // if (isLocal) {
      //   navigate("/auth/signin");
      // }
      // navigate("/common/cmtp01");
      // window.location.href = "/auth/signin";
      const isProd = window.location.hostname.includes("lecmoc.jp");
      // navigate(isProd ? "/common/cmtp01" : "/auth/signin")
      if (!isProd) {
        sessionStorage.setItem("allowAuthSignin", "true");
        navigate("/auth/signin");
      }
      return;
    };
    
    handleAuthInit();
  }, [navigate]);

  // if (samlError) {
  //   return (
  //     <LoginErrorPage
  //       messages={[samlError]}
  //     />
  //   )
  // }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-gray-600">認証リクエストを処理しています...</p>
    </div>
  );
}

