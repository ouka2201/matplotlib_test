import React from "react";
import style from "../styles/items.css";

// Propsの定義
interface ItemPairProps {
  label: string;
  value: string;
  type?: "single" | "table" | "vertical";  // 表示タイプの指定（単体, 表形式, 縦並び）
}

const ItemPair: React.FC<ItemPairProps> = ({ label, value, type = "single" }) => {
  return (
    <div className={`style.item-pair item-pair--${type}`}>
      <div className={style.itemPair__label}>{label}</div>
      <div className={style.itemPair__value}>{value}</div>
    </div>
  );
};

export default ItemPair;