import React from "react";

type GapSize = 0 | 8 | 16 | 24 | 32; // gap は 0px, 8px, 16px, 24px のみ
type PaddingSize = 0 | 4 | 8 | 16 | 24; // padding は 0px, 4px, 8px, 16px, 24px のみ

type LayoutProps = {
  children: React.ReactNode;
  direction?: "row" | "column"; // 縦並び or 横並び
  align?: "start" | "center" | "end" ; // 揃え
  justify?: "start" | "center" | "end" | "between" | "space-between" ; // 並び
  gap?: GapSize; // 小要素の隙間
  padding?: PaddingSize; // 内側の余白
};

const Layout: React.FC<LayoutProps> = ({
  children,
  direction = "row",
  align = "start",
  justify = "start",
  gap = 0,
  padding = 0,
}) => {
  return (
    <div
      style={{
        display: "flex", // デフォルトで flex
        flexDirection: direction, // 縦並び or 横並び
        alignItems: align, // 揃える位置
        justifyContent: justify === "between" ? "space-between" : justify, // 配置の仕方
        gap: `${gap}px`, // 子アイテム間の距離
        padding: `${padding}px`, // 内側の余白
        width: "100%", // デフォルトで幅100%
      }}
    >
      {children}
    </div>
  );
};

export default Layout;