import React, { useState } from "react";
import { useNavigate } from "react-router-dom"; // React Router のナビゲーションフックをインポート
import sidebar_styles from '../../styles/sidebarMenu.module.css';

const SidebarMenu: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(true); // サイドバーの全体の展開/折りたたみを制御
  const [openSubMenu, setOpenSubMenu] = useState<{ [key: string]: boolean }>({}); // 各親メニューの展開状態
  const navigate = useNavigate(); // ナビゲート用のフックを使用

  // サブメニューの展開/折りたたみ状態を切り替える
  const toggleSubMenu = (menuKey: string) => {
    setOpenSubMenu(prevState => ({
      ...prevState,
      [menuKey]: !prevState[menuKey], // サブメニューの状態を切り替え
    }));
  };

  const menuItems = [
    { name: "ホーム", link: "/home" },
    {
      name: "マスタ管理",
      subItems: [
        { name: "ユーザー管理", link: "/user_management" },
        { name: "入力シートアップロード画面", link: "/input_excel" },
        { name: "係数管理", link: "/coefficient_management" },
        { name: "建物管理", link: "/building_management", 
          subSubItems: [
            { name: "AEI建物情報入力", link: "/building_management_input_AEI" },
            // { name: "AEI建物情報一覧", link: "/building_management_search_AEI" },
            { name: "AEI建物情報一覧", link: "/building_management_search_AEI" },
            { name: "建物情報入力", link: "/building_management_input_PG" },
            { name: "建物情報入力1", link: "/building_management_input_1" },
            { name: "建物情報一覧", link: "/building_management_search_PG" },
          ],
        },
      ],
    },
    {
      name: "エネルギーデータ", 
      subItems: [
        { name: "エネルギーデータ入力", link: "/inquiry" },
        { name: "エネルギーデータ一覧", link: "/inquiry_search" },
      ],
    },
    { name: "指定表入力", link: "/designated_input" },
    { name: "特定表入力", link: "/specific_input" },
    { name: "エネルギーデータ一覧閲覧", link: "/energy_data_view" },
    { name: "エネルギーデータ補正", link: "/energy_data_correction" },
    { name: "情報開示", link: "/information_disclosure" },
    { name: "ダッシュボード", link: "/dashboard" },
  ];

  return (
    <div className={`${sidebar_styles.sidebar} ${isExpanded ? sidebar_styles.expanded : sidebar_styles.collapsed}`}>
      <button className={sidebar_styles.toggle_btn} onClick={() => setIsExpanded(!isExpanded)}>
        ☰
      </button>

      <ul className={sidebar_styles.menu}>
        {menuItems.map((item, index) => {
          const parentKey = `parent-${index}`; // 各親メニューに一意なキーを生成
          return (
            <li key={parentKey} className={item.subItems ? "parent_menu" : ""}>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  // item.link が有効であることを確認
                  if (item.link) {
                    navigate(item.link); // navigate を使ってルートを変更
                  }
                  toggleSubMenu(parentKey); // 現在の親メニューの展開状態を切り替える
                }}
              >
                {item.name}
              </button>
              
              {/* サブメニューの展開 */}
              {item.subItems && (
                <ul className={`${sidebar_styles.submenu} ${openSubMenu[parentKey] ? sidebar_styles.open : ""}`}>
                  {item.subItems.map((subItem, subIndex) => {
                    const subKey = `sub-${parentKey}-${subIndex}`; // 各サブメニューに一意なキーを生成
                    return (
                      <li key={subKey}>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            // subItem.link が有効であることを確認
                            if (subItem.link) {
                              navigate(subItem.link); // navigate を使ってルートを変更
                            }
                            toggleSubMenu(subKey); // 現在のサブメニューの展開状態を切り替える
                          }}
                        >
                          {subItem.name}
                        </button>

                        {/* サブサブメニューの展開 */}
                        {subItem.subSubItems && (
                          <ul className={`${sidebar_styles.submenu} ${openSubMenu[subKey] ? sidebar_styles.open : ""}`}>
                            {subItem.subSubItems.map((subSubItem, subSubIndex) => (
                              <li key={subSubIndex}>
                                <button
                                  onClick={(e) => {
                                    e.preventDefault();
                                    // subSubItem.link が有効であることを確認
                                    if (subSubItem.link) {
                                      navigate(subSubItem.link); // navigate を使ってルートを変更
                                    }
                                  }}
                                >
                                  {subSubItem.name}
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default SidebarMenu;
