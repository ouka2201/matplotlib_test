import type { LinksFunction, MetaFunction } from "@remix-run/node";
import { Links, Meta, Outlet, redirect, Scripts, ScrollRestoration, useFetcher, useLocation, useNavigate, useNavigation } from "@remix-run/react";
import React, { useEffect, useState, useRef } from 'react';
import { Providers } from "~/components/layout/providers";
import { LoadingSpinner } from "./components/common/loadingSpinner";
import stylesheet from "./tailwind.css?url";

export const links: LinksFunction = () => [
  { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
  { rel: "preload", as: "style", href: stylesheet },
  { rel: "stylesheet", href: stylesheet }
];

export const meta: MetaFunction = () => [
  { title: "TEPCO LecMoc" },
  { name: "description", content: "TEPCO LecMoc" },
];

console.log(`process : ${process.env.VITE_API_URL}`)
console.log(`import.meta : ${import.meta.env.VITE_API_URL}`)

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Error caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return <h1>Something went wrong.</h1>;
    }
    return this.props.children;
  }
}

export function HydrateFallback() {
  return (
    <html lang="ja">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="stylesheet" href={stylesheet} />
        <Meta />
        <Links />
      </head>
      <body>
        <LoadingSpinner />
        <Scripts />
      </body>
    </html>
  );
}

export default function Root() {
  // useIdleLogout();

  const navigation = useNavigation();
  const fetcher = useFetcher();
  const [showSpinner, setShowSpinner] = useState(false);

  useEffect(() => {
    const isNavigating = navigation.state !== "idle";
    const isSubmitting = fetcher.state !== "idle";

    setShowSpinner(isNavigating || isSubmitting);
  }, [navigation.state, fetcher.state]);

  const navigate = useNavigate();
  const location = useLocation();
  const previousPathnameRef = useRef<string | null>(null);
  const isInitialMountRef = useRef<boolean>(true);

  useEffect(() => {
    // セッションタイムアウトのハンドラー
    const sessionExpiredHandler = () => {
      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      // セッション情報を完全にクリア
      sessionStorage.removeItem("session");
      sessionStorage.removeItem("isAuthenticated");
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("refreshToken");
      window.location.href = "/session-expired";
    };

    // シングルログイン違反のハンドラー
    const singleLoginViolationHandler = (event: Event) => {
      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      // セッション情報を完全にクリア
      sessionStorage.removeItem("session");
      sessionStorage.removeItem("isAuthenticated");
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("refreshToken");
      navigate("/single-login-violation");
    };

    const sessionUserStatusErrorHandler = (event: Event) => {
      const customEvent = event as CustomEvent;
      const errorMessage = customEvent.detail?.message || "ユーザーステータスが変更されました。";

      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      sessionStorage.removeItem("session");
      sessionStorage.setItem("sessionUserStatusErrorMessage", errorMessage);
      navigate("/session-user-status-error");
    };

    window.addEventListener("sessionExpired", sessionExpiredHandler);
    window.addEventListener("singleLoginViolation", singleLoginViolationHandler as EventListener);
    window.addEventListener("sessionUserStatusError", sessionUserStatusErrorHandler as EventListener);

    return () => {
      window.removeEventListener("sessionExpired", sessionExpiredHandler);
      window.removeEventListener("singleLoginViolation", singleLoginViolationHandler as EventListener);
      window.removeEventListener("sessionUserStatusError", sessionUserStatusErrorHandler as EventListener);
    };
  }, [navigate]);

  // useEffect(() => {
  //   const isAuth = sessionStorage.getItem("isAuthenticated");
  //   const authSignin = sessionStorage.getItem("allowAuthSignin");
  //   console.log(`isAuth : ${isAuth}`)
  //   if (!isAuth && !authSignin) {
  //     console.log("rootから user_infi_initへ遷移する。")
  //     navigate("/auth/user_info_init");
  //   }
  // }, []);
  // URL手動変更時の制御（/auth/signin と / 以外は / にリダイレクト）
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const isFromRever = window.location.hostname.includes("lecmoc.jp");
    const previousPathname = previousPathnameRef.current;
    const pathnameChanged = previousPathname !== null && previousPathname !== location.pathname;
    const isRoot = location.pathname === "/";
    const isAuthSignin = location.pathname === "/auth/signin";
    const isAuthLogout = location.pathname === "/auth/logout";
    const isAuthUserInfoInit = location.pathname === "/auth/user_info_init";
    const isSessionUserStatusError = location.pathname === "/session-user-status-error";
    const isSingleLoginViolation = location.pathname === "/single-login-violation";
    const isLoginError = location.pathname === "/login-error";
    const isSessionErrorPage = location.pathname === "/session-user-status-error" ||
      location.pathname === "/session-expired" ||
      location.pathname === "/single-login-violation" ||
      location.pathname === "/login-error";
    const previousWasErrorPage = previousPathname === "/session-user-status-error" ||
      previousPathname === "/session-expired" ||
      previousPathname === "/single-login-violation" ||
      previousPathname === "/login-error";
    const isNavigating = navigation.state !== "idle";

    // // 初回マウント時は記録のみ
    // if (isInitialMountRef.current) {
    //   // /session-user-status-error と /single-login-violation、/login-error の場合は、リダイレクトしない
    //   if (isSessionUserStatusError || isSingleLoginViolation || isLoginError) {
  //     previousPathnameRef.current = location.pathname;
    //     isInitialMountRef.current = false;
  //     return;
  //   }
    //   previousPathnameRef.current = location.pathname;
    //   isInitialMountRef.current = false;
    //   return;
    // }

    // ナビゲーション中は制御しない（無限ループ防止）
    if (isNavigating) {
      return;
    }

    // isAuthenticatedを取得
    const isAuthenticated = sessionStorage.getItem("isAuthenticated") === "true";
    const allowAuthSignin = sessionStorage.getItem("allowAuthSignin") === "true";
    const naviTo = isFromRever ? "/auth/user_info_init" : "/"

    if (!isAuthenticated && !allowAuthSignin && !isAuthLogout && !isSessionErrorPage) {
      if (isFromRever) {}
        console.log("rootから user_infi_initへ遷移する。")
        navigate(naviTo);

      return;
    }
    // /auth/user_info_init は認証処理中のため、スキップ
    if (isAuthUserInfoInit) {
      previousPathnameRef.current = location.pathname;
      return;
    }

    // /auth/logout はログアウト完了画面のため、スキップ
    if (isAuthLogout) {
      previousPathnameRef.current = location.pathname;
      return;
    }

    // /session-user-status-error と /single-login-violation は認証フロー内のエラー画面のため、認証不要で表示を許可
    // リロード時も / にリダイレクトしない
    if (isSessionUserStatusError || isSingleLoginViolation) {
      previousPathnameRef.current = location.pathname;
      return;
    }

    // URLが変更された場合、認証されていない場合のみisAuthenticatedをfalseにリセット
    // エラー画面とユーザー情報初期化画面、ログアウト画面はスキップ
    // エラー画面から戻った場合もスキップ（戻るボタンで戻った際のセッションタイムアウトを防ぐため）
    if (pathnameChanged && !isRoot && !isAuthSignin && !isAuthLogout && !isSessionErrorPage && !isAuthenticated && !previousWasErrorPage) {
      sessionStorage.setItem("isAuthenticated", "false");
    }

    // /auth/signin への直接アクセスを防ぐ（API経由での遷移のみ許可）
    if (isAuthSignin && !allowAuthSignin) {
      sessionStorage.removeItem("allowAuthSignin");
      // navigate("/");
      navigate(naviTo);
      return;
    }

    // /auth/signin は許可（API経由での遷移の場合）
    if (isAuthSignin && allowAuthSignin) {
      previousPathnameRef.current = location.pathname;
      return;
    }

    // エラー画面は認証状態に関係なく表示を許可
    // ただし、リロード時は / にリダイレクト（session-user-status-error と single-login-violation、login-error は除く）
    if (isSessionErrorPage) {
      // /login-error の場合はリロード時もリダイレクトしない
      if (isLoginError) {
        previousPathnameRef.current = location.pathname;
        return;
      }
      // session-user-status-error と single-login-violation は既に上で処理済みのため、ここには来ない
      // その他のエラー画面のリロード時（previousPathnameが現在のパスと同じ場合）
      if (previousPathname === location.pathname) {
        // navigate("/");
        navigate(naviTo);
        return;
      }
      previousPathnameRef.current = location.pathname;
      return;
    }

    // エラー画面から戻った場合、/ にリダイレクト（セッションタイムアウトを防ぐため）
    // エラー画面から戻った場合、セッションが無効な状態で業務画面に戻ることを防ぐ
    // session-user-status-errorから戻った場合は除外（認証フロー内のエラーのため）
    if (previousWasErrorPage && !isSessionErrorPage && previousPathname !== "/session-user-status-error") {
      previousPathnameRef.current = location.pathname;
      // navigate("/");
      navigate(naviTo);
      return;
    }

    // 認証済みの場合は、業務画面への遷移を許可
    if (isAuthenticated && !isRoot && !isAuthSignin && !isAuthLogout) {
      // /auth/signinから他の画面に遷移した場合、allowAuthSigninフラグを削除
      if (previousPathname === "/auth/signin") {
        sessionStorage.removeItem("allowAuthSignin");
      }
      previousPathnameRef.current = location.pathname;
      return;
    }

    // URLが変更された場合、/ と /auth/signin、/auth/logout 以外はすべて / にリダイレクト
    // navigation.stateがidleで、かつpathnameが変更された場合、URLの直接変更と判断
    // ただし、認証済みの場合は業務画面への遷移を許可するため、この条件は認証されていない場合のみ
    // エラー画面はスキップ
    // エラー画面から戻った場合もスキップ（戻るボタンで戻った際のセッションタイムアウトを防ぐため）
    // /auth/user_info_init から遷移した場合もスキップ（認証処理中のため）
    if (pathnameChanged && !isAuthSignin && !isAuthLogout && !isSessionErrorPage && !isAuthenticated && !previousWasErrorPage && previousPathname !== "/auth/user_info_init") {
      // navigate("/");
      navigate(naviTo);
      return;
    }

    // 認証されていない場合、/ と /auth/signin、/auth/logout 以外は常に / に戻す
    // エラー画面はスキップ
    // エラー画面から戻った場合もスキップ（戻るボタンで戻った際のセッションタイムアウトを防ぐため）
    if (location.pathname !== "/" && !isAuthenticated && !isAuthSignin && !isAuthLogout && !isSessionErrorPage && !previousWasErrorPage) {
      // navigate("/");
      navigate(naviTo);
      return;
    }

    // 現在のパス名を記録
    previousPathnameRef.current = location.pathname;
  }, [location.pathname, navigate, navigation.state]);

  return (
    <>
      <html lang="ja">
        <head>
          <meta charSet="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <link rel="stylesheet" href={stylesheet} />
          <Meta />
          <Links />
        </head>
        <body>
          <Providers>
            <ErrorBoundary>
              {showSpinner && <LoadingSpinner />}
              <Outlet />
            </ErrorBoundary>
          </Providers>
          <ScrollRestoration />
          <Scripts />
        </body>
      </html>
    </>
  );
}
