import React, { createContext, useContext, useState } from "react";
import { getData } from "~/lib/fetch";
import { logMessage } from "~/lib/logger";
import { NavItem } from "~/types";
import { navItems } from "~/constants/data";

export type Permission = {
  authority_id: string;
  authority_code: "0" | "1" ;
};

const defaultSessionValue = {
  navItems: [] as NavItem[],
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  updateNaviItems: (permissions: Permission[]) : void => {},
};

const MenuContext = createContext(defaultSessionValue);

export const fetchPermissions = async (
  token: string,
): Promise<{
  status: "ok" | "error";
  navItems?: NavItem[];
  permissions?: Permission[];
}> => {
  try {
    // トークンを使って認可情報を取得します。
    const { status, permissions } = await getData("/api/auth/permissions", {
      Authorization: `Bearer ${token}`,
    });

    if (status === "ok" && permissions) {
      const filteredNavItems = navItems.filter((item) => {
        
        // パーミッションの権限IDが一致しているかチェックします。
        return permissions.some((permission: Permission) =>
          item.authorityId === permission.authority_id);
      });
      return { status: "ok", navItems: filteredNavItems, permissions };
    }

    return { status: "error" };
  } catch (error) {
    logMessage({ message: "Failed to refresh token", object: error });
    sessionStorage.removeItem("refreshToken");
    sessionStorage.removeItem("token");
    return { status: "error" };
  }
};

export const getPermissions = (
  permissions: Permission[] = [],
): { navItems: NavItem[] } => {
  try {
    const filteredNavItems = navItems.filter((item) => {
      return permissions.some(
        (permission) => item.authorityId === permission.authority_id,
      );
    });
    return { navItems: filteredNavItems };
  } catch (error) {
    console.error("Failed to get permissions", error);
    sessionStorage.removeItem("refreshToken");
    sessionStorage.removeItem("token");
    return { navItems: [] }; // fallback safe
  }
};

export const MenuProvider = ({
  children,
}: {
  children: React.ReactNode;
}): JSX.Element => {
  const [navItems, setNavItems] = useState<NavItem[]>([]);
  const updateNaviItems = (permissions: Permission[]) => {
    const result = getPermissions(permissions);
    setNavItems(result.navItems);
  };
  return (
    <MenuContext.Provider
      value={{
        navItems,
        // updateNaviItems: async (token: string) => {
        //   const { navItems, status } = await fetchPermissions(token);
        //   if (status === "ok") {
        //     setNavItems(navItems!);
        //   }
        // },
        updateNaviItems,
      }}
    >
      {children}
    </MenuContext.Provider>
  );
};

// カスタムフックを作成してコンテキストにアクセスできるようにする
export const useMenu = () => useContext(MenuContext);
