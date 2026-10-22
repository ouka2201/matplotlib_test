// import React from "react";
import { useNavigate } from "react-router-dom"; // React Router のナビゲーションフックをインポート
// import sidebar_styles from '../../styles/sidebarMenu.module.css';
import '../styles/middle-test2.css';
import { useSession } from "~/components/layout/session-provider";
import { useToast } from "~/components/ui/use-toast";
import { postData } from "~/lib/fetch";

export default function Header () {
  // const [isExpanded, setIsExpanded] = useState(true); // サイドバーの全体の展開/折りたたみを制御
  // const [openSubMenu, setOpenSubMenu] = useState<{ [key: string]: boolean }>({}); // 各親メニューの展開状態
  const navigate = useNavigate(); // ナビゲート用のフックを使用

  // // サブメニューの展開/折りたたみ状態を切り替える
  // const toggleSubMenu = (menuKey: string) => {
  //   setOpenSubMenu(prevState => ({
  //     ...prevState,
  //     [menuKey]: !prevState[menuKey], // サブメニューの状態を切り替え
  //   }));
  // };

  // const menuItems = [
  //   { name: "ホーム", link: "/home" },
  //   {
  //     name: "マスタ管理",
  //     subItems: [
  //       { name: "ユーザー管理", link: "/user_management" },
  //       { name: "係数管理", link: "/coefficient_management" },
  //       { name: "建物管理", link: "/building_management", 
  //         subSubItems: [
  //           { name: "AEI建物情報入力", link: "/building_management_input_AEI" },
  //           // { name: "AEI建物情報一覧", link: "/building_management_search_AEI" },
  //           { name: "AEI建物情報一覧", link: "/building_management_search_AEI" },
  //           { name: "建物情報入力", link: "/building_management_input_PG" },
  //           { name: "建物情報入力1", link: "/building_management_input_1" },
  //           { name: "建物情報一覧", link: "/building_management_search_PG" },
  //         ],
  //       },
  //     ],
  //   },
  //   {
  //     name: "エネルギーデータ", 
  //     subItems: [
  //       { name: "エネルギーデータ入力", link: "/inquiry" },
  //       { name: "エネルギーデータ一覧", link: "/inquiry_search" },
  //     ],
  //   },
  //   { name: "指定表入力", link: "/designated_input" },
  //   { name: "特定表入力", link: "/specific_input" },
  //   { name: "エネルギーデータ一覧閲覧", link: "/energy_data_view" },
  //   { name: "エネルギーデータ補正", link: "/energy_data_correction" },
  //   { name: "情報開示", link: "/information_disclosure" },
  //   { name: "ダッシュボード", link: "/dashboard" },
  // ];

  
  const { session, clearSession } = useSession();
  const { toast } = useToast();
  const handleLogout = async () => {
    try {
      const response = await postData("/api/auth/signout");
  
      if (response.status === "success") {
        clearSession();
        sessionStorage.removeItem("isAuthenticated");
        sessionStorage.removeItem("token");
        sessionStorage.removeItem("session");
        
        // ログアウト完了画面にリダイレクト
        navigate("/auth/logout");
      } else {
        console.error("ログアウト失敗", response);
      }
    } catch (error) {
      console.error("ログアウトエラー", error);
    }
  };

  return (
		// <div className="main-container">
			<div className="frame-header">
				<div className="header-title">
					<div className="header-title-logo">
						<div className="tepco-header" />
					</div>
					<button className="header-title-text" onClick={() => navigate("/")}>てぷれぽ</button>
				</div>
				<div className="header-account">
					<div className="header-account-popup">
						<div className="header-account-popup-setting">
							<span className="header-account-popup-text-gray">
								ユーザー設定
							</span>
						</div>
						<div 
              className="header-account-popup-logout"
              role="button"
              tabIndex={0}
              onClick={handleLogout}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  handleLogout();
                }
              }}
            >
							<span className="header-account-popup-text-black">
								ログアウト
							</span>
						</div>
					</div>
					<div className="header-account-icon" />
					<div className="header-account-text">
						<span className="header-account-text-branch">EP法人営業部</span>
						<span className="header-account-text-username">{session?.name ?? "ゲスト"}</span>
					</div>
					<div className="header-account-arrow" />
				</div>
			</div>
		// </div>
  );
}


