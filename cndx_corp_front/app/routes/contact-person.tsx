import { Outlet } from "@remix-run/react";
import Header from "~/components/layout/header";
// import Sidebar from "~/components/layout/sidebar";
import Sidebar from "~/components/sidebar";

// import { MetaFunction } from "@remix-run/node";

// export const meta: MetaFunction = () => {
//   return [{ title: "担当者設定" }, { name: "description", content: "set" }];
// };
// アプリケーションの主要なレイアウトコンポーネント
// すべての認証が必要なページで使用されます。
export default function App() {
  return (
    <>
      {/* ヘッダーコンポーネント */}
      <Header />
      <div className="flex h-screen z-0 overflow-hidden">
        {/* サイドバーコンポーネント */}
        <Sidebar />
        {/* メインコンテンツエリア */}
        <main className="w-full overflow-auto">
          <Outlet />
        </main>
      </div>
    </>
  );
}
