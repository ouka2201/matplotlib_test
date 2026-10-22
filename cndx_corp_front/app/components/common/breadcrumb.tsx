import { useNavigate } from "@remix-run/react";
import React from "react";
import Icon from "../icon";

export type BreadCrumbType = {
  title: string; // 画面名
  link: string; // リンク先
  state?: unknown; // リンク先に渡す状態（オプション）
  onClick?: () => void; // 画面専用クリック処理（任意）
};

type BreadCrumbPropsType = {
  items: BreadCrumbType[]; // 複数のパンくずアイテムを受け取る
};

/**
 * パンくずリストを作成
 */
function BreadCrumbItem(props: {
  item: BreadCrumbType;
  isLast: boolean; // 最後のアイテムか
  showSeparator: boolean; // 「>」を表示するか
}) {
  const { item, isLast, showSeparator } = props;
  const navigate = useNavigate();

  const handleClick = () => {
    if (item.onClick) {
      item.onClick(); // 画面専用処理を優先
    } else if (item.link) {
      navigate(item.link, { state: item.state ?? undefined });
    }
  };

  return (
    <React.Fragment>
      {showSeparator && <Icon name="chevron_right" />}
      {/* <span
        role="link"
        tabIndex={0}
        className={`cursor-pointer ${isLast
          ? "breadcrumb__link breadcrumb__link--last"
          : "breadcrumb__link breadcrumb__link--not-last"
          }`}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            handleClick();
          }
        }}
      >
        {item.title}
      </span> */}
      <span
        role={item.link ? "link" : undefined}
        tabIndex={item.link ? 0 : undefined}
        className={`${item.link ? "cursor-pointer" : "cursor-default text-muted"} ${
          isLast ? "breadcrumb__link breadcrumb__link--last" : "breadcrumb__link breadcrumb__link--not-last"
        }`}
        onClick={item.link ? handleClick : undefined}
        onKeyDown={
          item.link || item.onClick
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") handleClick();
              }
            : undefined
        }
      >
        {item.title}
      </span>
    </React.Fragment>
  );
}

export default function BreadCrumb(props: BreadCrumbPropsType) {
  const { items } = props;

  return (
    <>
      {items.length > 1 ? (
        <div className="breadcrumb__list">
          {items.map((item, index) => (
            <BreadCrumbItem
              key={item.title}
              item={item}
              isLast={index === items.length - 1}
              showSeparator={index > 0}
            />
          ))}
        </div>
      ) : (
        <div className="page-title-box page-title-text">{items[0]?.title}</div>
      )}
    </>
  );
}
