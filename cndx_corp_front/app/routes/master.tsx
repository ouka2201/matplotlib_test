import { Outlet } from "@remix-run/react";
import Header from "~/components/layout/header";
import Sidebar from "~/components/sidebar";

export default function App() {
  return (
    <>
      <Header />
      <aside className="fixed inset-y-0 left-0 w-[220px] bg-white border-r border-gray-200 z-10">
        <div className="h-full pt-0 overflow-y-auto overflow-x-hidden">
          <Sidebar />
        </div>
      </aside>

      <div className="ml-[220px]">
        <main className="w-full">
          <Outlet />
        </main>
      </div>
    </>
  );
}