import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom"; // React Router のナビゲーションフックをインポート
import { useMenu } from "~/components/layout/menu-provider";
import type { NavItem } from "~/types";
import '../styles/middle-test2.css';
import sidebar_styles from '../styles/sidebarMenu.module.css';

const Sidebar: React.FC = () => {
  //const [isExpanded, setIsExpanded] = useState(true); // サイドバーの全体の展開/折りたたみを制御
  const [openSubMenu, setOpenSubMenu] = useState<{ [key: string]: boolean }>({}); // 各親メニューの展開状態
  const navigate = useNavigate(); // ナビゲート用のフックを使用
  // const { pathname } = useLocation();
  const location = useLocation();
  const { pathname, state } = location;
  const forceActiveMenu = (state as any)?.forceActiveMenu;
  const { navItems } = useMenu();

  // URL 末尾の画面コード（例: mscs03 / ebrc03）を取得
  const getScreenCode = (path: string): string | null => {
    const m = path.match(/\/([a-z]{4}\d{2})(?:\/|$)/i);
    return m ? m[1].toLowerCase() : null;
  };

  // 画面コードの prefix（先頭4文字）
  const getPrefix = (screenCode: string | null): string | null => {
    return screenCode ? screenCode.slice(0, 4) : null;
  };

  // prefix → 所属メニュー(title) のマッピング
  // ※ 同一機能内で画面コードが変わるケースを吸収
  const prefixToMenuTitle: Record<string, string> = {
    // master
    mscs: "mscs01",
    msbd: "mscs01",
    msbg: "mscs01",
    msog: "msog01",
    msus: "msus01",
    msmg: "msmg01",

    // energy-building
    ebmg: "ebmg01",
    ebrc: "ebmg01", // ebrc03 は「レポート作成・管理」配下
    ebmv: "ebmv01",

    // common
    cmtp: "cmtp01",
    cmhp: "cmhp01",
    cmdl: "cmdl01",
    cmcl: "cmcl01",
  };

  const isActiveNavItem = (path: string, item: NavItem): boolean => {
    if (forceActiveMenu) {
      return item.title.toLowerCase() === String(forceActiveMenu).toLowerCase();
    }
    const screenCode = getScreenCode(path); // 例: "ebrc03"
    const prefix = getPrefix(screenCode);   // 例: "ebrc"

    // ① 画面コード完全一致（ebdl01 / ebdl02 等の衝突回避）
    if (screenCode && item.title.toLowerCase() === screenCode) {
      return true;
    }

    // ② prefix から所属メニュー判定
    if (prefix) {
      const ownerTitle = prefixToMenuTitle[prefix];
      if (ownerTitle && ownerTitle.toLowerCase() === item.title.toLowerCase()) {
        return true;
      }
    }

    // ③ フォールバック（完全一致 or 子階層）
    if (item.link) {
      return path === item.link || path.startsWith(item.link + "/");
    }
    return false;
  };
  // サブメニューの展開/折りたたみ状態を切り替える
  const toggleSubMenu = (menuKey: string) => {
    setOpenSubMenu(prevState => ({
      ...prevState,
      [menuKey]: !prevState[menuKey], // サブメニューの状態を切り替え
    }));
  };

  const groupConfig: Record<string, string> = {
    "01": "インフォメーション",
    "02": "基本機能",
    "03": "電力30分値",
    "04": "マスタ",
    "05": "ユーザー・営業担当",
  };

  return (
    <aside className={`mt-20 ${sidebar_styles.sidebar2}`}>
      {Object.entries(groupConfig).map(([groupId, label]) => {
        const items = navItems.filter(item => item.groupId === groupId);
        if (items.length === 0) return null;

        return (
          <aside key={groupId} className={sidebar_styles.sidebar2}>
            <div className={sidebar_styles.sub_title}>
              <span className={sidebar_styles.sub_title_text}>{label}</span>
            </div>
            <ul className={sidebar_styles.menu}>
              {items.map((item, index) => {
                const parentKey = `${groupId}-${index}`;
                const active = isActiveNavItem(pathname, item);
                return (
                  <li key={parentKey}>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        if (item.link) {
                          navigate(item.link);
                        }
                        toggleSubMenu(parentKey);
                      }}
                      // className={pathname === item.link ? sidebar_styles.active_button : ""}
                      className={active ? sidebar_styles.active_button : ""}
                    >
                      <span>{item.name}</span>
                      <i className="chevron_right_dp_f_fill_wght_grad_opsz" />
                    </button>
                  </li>
                );
              })}
            </ul>
          </aside>
        );
      })}
    </aside>
  );

};

export default Sidebar;
