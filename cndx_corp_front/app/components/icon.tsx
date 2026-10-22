import React from "react";

// 型定義
//cndx_corp_front/public/assets/icons/の配下にあるiconファイルの名前
//命名規則”icon-「{名前}-{パターン}'」.svg”の「」の中身の部分を羅列
type IconName =
  //ヘッダー
  | "logo-tepsys"
  | "account"

  //ボタン類
  | "plus"
  | "upload"
  | "download"

  //テーブル
  | "calendar"
  | "checkbox-all"
  | "checkbox-checked"
  | "checkbox-empty"

  //エラー系
  | "error-red"
  | "error-pink"

  //サイドバー
  | "bank"

  //矢印
  | "arrow-line-right"
  | "arrow-line-right-black"
  | "arrow-line-up"
  | "arrow-line-down"
  | "arrow-filled-down"

  // STEP3デザインのアイコン
  // インデックス
  | "list"
  // 矢印
  | "chevron_right" 

  // 編集削除
  | "delete"
  | "edit"
  
  ;

type IconProps = {
  name: IconName; // アイコン名
  className?: string; // 任意のクラス
  size?: number | string; // サイズのオーバーライド（任意）
  color?: string; //色の指定（任意）、指定がなければ親要素の色を引き継ぐ
  // onClick?: React.MouseEventHandler<HTMLImageElement>;
  onClick?: () => void;
};

const ICON_SIZES: Record<IconName, { width: number; height: number }> = {
  //ヘッダー
  "logo-tepsys": { width: 88, height: 32 },
  account: { width: 32, height: 32 },

  //ボタン類
  plus: { width: 11.67, height: 11.67 },
  upload: { width: 13.33, height: 13.33 },
  download: { width: 13.33, height: 13.33 },

  //テーブル
  calendar: { width: 15, height: 16.67 },
  "checkbox-all": { width: 18, height: 18 },
  "checkbox-checked": { width: 18, height: 18 },
  "checkbox-empty": { width: 18, height: 18 },

  //エラー
  "error-red": { width: 15, height: 15 },
  "error-pink": { width: 20, height: 20 },

  //サイドバー
  bank: { width: 16.67, height: 16.67 },

  //矢印
  "arrow-line-right": { width: 7.4, height: 12 },
  "arrow-line-right-black": { width: 7.4, height: 12 },
  "arrow-line-up": { width: 10, height: 6.17 },
  "arrow-line-down": { width: 10, height: 6.17 },
  "arrow-filled-down": { width: 10, height: 5 },

  // STEP3デザインのアイコン
  // 矢印
  chevron_right: { width: 24, height: 24 },
  // インデックス
  list: { width: 24, height: 24 },
  //編集削除
  delete: { width: 20, height: 20 },
  edit: { width: 20, height: 20 },
};

const Icon: React.FC<IconProps> = ({ name, size, className, onClick }) => {
  const iconPath = `/assets/icons/icon-${name}.svg`;

  // デフォルトのサイズを取得
  const defaultSize = ICON_SIZES[name];

  // 縦横比を計算する
  const aspectRatio = defaultSize.width / defaultSize.height;
  // サイズ指定があればそれを使用、なければデフォルトサイズを使用

  //クリックができるだけカーソルをポインターにする
  const style: React.CSSProperties = {
    cursor: onClick ? "pointer" : undefined,
  };

  if (size?.width) {
    style.width = size.width;
    style.height = size.width / aspectRatio; // 幅を指定した場合、縦横比を保って高さを計算
  } else if (size?.height) {
    style.height = size.height;
    style.width = size.height * aspectRatio; // 高さを指定した場合、縦横比を保って幅を計算
  } else {
    style.width = defaultSize.width;
    style.height = defaultSize.height;
  }

  return (
    <img
      src={iconPath}
      alt={name}
      className={className}
      style={style}
      // onClick={onClick}
    />
  );
};

export default Icon;
