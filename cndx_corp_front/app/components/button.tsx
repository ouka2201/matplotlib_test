import React from "react";
import styles from "../styles/middleBase.module.css";

interface ButtonProps {
  variant?: "default" | "primary" | "secondary" | "building1" | "building2"; // ボタンの種類
  text: string; // ボタンの文言
  icon?: React.ReactNode; // アイコン
  iconPosition?: "left" | "right"; // アイコンの位置
  disabled?: boolean; // 非活性化
  onClick?: () => void; // クリック時の処理
}

const Button: React.FC<ButtonProps> = ({
  variant = "default",
  text = "ボタン",
  icon,
  iconPosition = "left",
  disabled = false,
  onClick,
}) => {
  // ボタンのクラス設定
  const buttonClass = `${styles.button} ${styles[`button--${variant}`]} ${
    icon ? styles[`button--icon-${iconPosition}`] : ""
  } ${disabled ? styles["button--disabled"] : ""}`;

  return (
    <button className={buttonClass} disabled={disabled} onClick={onClick}>
      {/* アイコンが左の場合 */}
      {icon && iconPosition === "left" && (
        <span className={styles["button-icon"]}>{icon}</span>
      )}
      {/* ボタンのテキスト */}
      <span className={styles["button-text"]}>{text}</span>
      {/* アイコンが右の場合 */}
      {icon && iconPosition === "right" && (
        <span className={styles["button-icon"]}>{icon}</span>
      )}
    </button>
  );
};

export default Button;
