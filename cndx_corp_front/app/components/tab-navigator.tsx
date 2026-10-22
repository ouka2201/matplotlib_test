import { useLocation, useNavigate } from "react-router-dom";
import { useRoleFlags } from "~/hooks/useRoleFlags";
const TABS = [
  "お客さま基本情報",
  "拠点・エネルギー情報",
  "CNカルテ",
  "電力情報",
  "電力見える化レポート",
] as const;

export type TabName = (typeof TABS)[number];

export const PERMISSION_TAB_URLS: {
  [key in 1 | 2]: Partial<Record<TabName, string>>;
} = {
  1: {
    "お客さま基本情報": "/energy-building/ebrc03",
    "拠点・エネルギー情報": "/energy-building/ebrc04",
    "CNカルテ": "/energy-building/ebrc02",
    "電力情報": "/energy-building/ebrc07",
    "電力見える化レポート": "/energy-building/ebrc06",

  },
  2: {
    "お客さま基本情報": "/energy-building/ebrc03",
    "拠点・エネルギー情報": "/energy-building/ebrc05",
    "CNカルテ": "/energy-building/ebrc01",
  },
};

export const TabNavigator = ({
  selectedTab,
  onTabChange,
  permission,
}: {
  selectedTab: TabName;
  onTabChange: (tab: TabName) => void;
  permission: 1 | 2;
}) => {

  const navigate = useNavigate();
  const location = useLocation();
  const customerData = location.state?.customerData;
  const { isVis } = useRoleFlags();

  const getTabUrl = (permission: 1 | 2, tab: TabName): string | undefined => {
    return PERMISSION_TAB_URLS[permission]?.[tab];
  };

  const availableTabs = TABS.filter((tab) => {
    if (permission === 2 && isVis && tab === "CNカルテ") return false;
    return !!getTabUrl(permission, tab);
  });

  const handleTabClick = (tab: TabName) => {
    const url = getTabUrl(permission, tab);
    if (!url) return;


    const orgId = (location.state as any)?.orgId ?? sessionStorage.getItem("selectedOrgId");
    const agreementCategory =
      (location.state as any)?.agreementCategory ?? sessionStorage.getItem("selectedAgreementCategory");

    onTabChange(tab);
    navigate(url, {
      state: {
        permission,
        customerData,
        orgId,
        agreementCategory
      },
    });
  };


  return (
    <div className="tablist px-16">
      {availableTabs.map((tab) => (
        <button
          key={tab}
          onClick={() => handleTabClick(tab)}
          className={`tab-button ${tab === selectedTab ? "tab-button-active" : "tab-button-inactive"
            }`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
};

