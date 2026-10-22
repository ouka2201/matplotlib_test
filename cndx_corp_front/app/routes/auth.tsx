import { Outlet, Link } from "@remix-run/react";
import "../styles/middle-test2.css";

export default function App() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Link
        to="/"
        className="absolute left-8 top-6 z-20 flex items-center text-lg font-bold tracking-tight"
      />
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
