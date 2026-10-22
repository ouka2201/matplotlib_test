import { useNavigate } from "@remix-run/react";
import { KeyboardEvent, useEffect, useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import "../../styles/userNav.css";
import { AlertModal } from "../modal/alert-modal";
import { Skeleton } from "../ui/skeleton";
import { useToast } from "../ui/use-toast";
import { useSession } from "./session-provider";

export function UserNav() {
  const navigate = useNavigate();
  const { session, clearSession } = useSession();
  const { toast } = useToast();

  const [loading, setLoading] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [user, setUser] = useState<{ name: string; email: string; org_name: string; } | null>(
    null
  );
  const [isSessionLoading, setIsSessionLoading] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setUser(JSON.parse(sessionData));
      }
      setIsSessionLoading(false);
    }
  }, []);

  // const username = session?.name || user?.name || "ゲスト";
  // const email = session?.email || user?.email || "";
  // const orgName = session?.org_name || user?.org_name || "";
  const username = user?.name || session?.name || "ゲスト";
  const email = user?.email || session?.email || "";
  const orgName = user?.org_name || session?.org_name || "";

  const handleLogout = async () => {
    try {
      setLoading(true);
      clearSession();
      sessionStorage.removeItem("isAuthenticated");
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("session");

      // ログアウト完了画面にリダイレクト
      navigate("/auth/logout");
      toast({ title: "ログアウト成功" });
      // トーストは表示しない（ログアウト画面でメッセージを表示するため）
    } catch (error) {
      toast({ title: "ログアウトエラー" });
    } finally {
      setLoading(false);
      setShowLogoutConfirm(false);
    }
  };

  const handleKeyPress = (action: () => void) => (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      action();
    }
  };

  // ログアウト確認モーダル再表示用
  const handleLogoutOpen = () => {
    setShowLogoutConfirm(false);
    setTimeout(() => setShowLogoutConfirm(true), 0);
  };

  return (
    <DropdownMenu >
      <DropdownMenuTrigger asChild>
        <div className="user-nav cursor-pointer">
          <div className="user-nav__icon" />
          <div className="user-nav__text">
            <span className="user-nav__branch">{orgName}</span>
            <span className="user-nav__username">
              {isSessionLoading ? <Skeleton /> : <span>{username}</span>}
            </span>
          </div>
          <div
            className="user-nav__arrow"
            role="button"
            tabIndex={0}
            onKeyDown={handleKeyPress(() => { })}
          />
        </div>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="user-nav__menu bg-white " align="end" forceMount>
        <DropdownMenuLabel className="user-nav__label">
          <div className="user-nav__label-content ">
            <p className="user-nav__username">
              {isSessionLoading ? <Skeleton /> : username}
            </p>
            <p className="user-nav__email">
              {isSessionLoading ? <Skeleton /> : email}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="user-nav__logout"
          role="button"
          tabIndex={0}
          onClick={handleLogoutOpen}
          onKeyDown={handleKeyPress(handleLogoutOpen)}
        >
          ログアウト
        </DropdownMenuItem>
      </DropdownMenuContent>

      <AlertModal
        isOpen={showLogoutConfirm}
        onClose={() => setShowLogoutConfirm(false)}
        onConfirm={handleLogout}
        loading={loading}
        title="ログアウトの確認"
        description="ログアウトします。よろしいですか？"
        cancelText="いいえ"
        continueText="はい"
      />
    </DropdownMenu>
  );
}
