import { ClientActionFunction, Outlet, redirect } from "@remix-run/react";
import React from "react";
import Header from "~/components/layout/header";
import { callRefreshTokenEndpoint } from "~/components/layout/session-provider";
import Sidebar from "~/components/sidebar";
import { logMessage } from "~/lib/logger";
const MemoSidebar=React.memo(Sidebar);
export function withAuthLoader(
  loaderFn: ClientActionFunction,
): ClientActionFunction {
  return async (args) => {
    try {
      logMessage({
        message: `Checking authentication... at ${new Date().toISOString()}`,
      });

      // リフレッシュトークンエンドポイントを呼び出し、ステータスをチェック
      const { status } = await callRefreshTokenEndpoint();
      // 認証に失敗した場合、ルート（/）にリダイレクトしてSAML認証を実行
      if (status !== "ok") {
        // return redirect("/session-expired");
        return redirect("/");
      }

      // 認証に成功した場合、元のloader関数を実行
      return loaderFn(args);
    } catch (error) {
      // エラーハンドリング: 認証チェック中にエラーが発生した場合、セッション切れのページにリダイレクト
      logMessage({ message: `Error during authentication check: ${error}` });
      return redirect("/session-expired");
    }
  };
}

// クライアント側で実行されるloader関数
// 認証チェックが必要なすべてのクライアント側ナビゲーションで使用されます。
// export const clientLoader = withAuthLoader(async () => {
//   // クライアント側のナビゲーション中に直接APIエンドポイントにアクセス
//   return {};
// });

// アプリケーションの主要なレイアウトコンポーネント
// すべての認証が必要なページで使用されます。
export default function App() {
  return (
    <>
      {/* ヘッダーコンポーネント */}
      <Header />
      <div className="layout-wrapper">
        {/* サイドバーコンポーネント */}
        <MemoSidebar />
        {/* メインコンテンツエリア */}
        <main className="w-full pb-10 ">
          <Outlet />
        </main>
      </div>
    </>
  );
}
