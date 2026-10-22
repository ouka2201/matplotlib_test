import React, { useState } from "react"; // React本体とuseStateフックをインポート

// Dropdownコンポーネントの定義
const Dropdown = ({ label, options, placeholder = "Select an option", onChange }) => {
  // useStateを使って選択状態を管理する
  const [selectedValue, setSelectedValue] = useState("");

  // ユーザーが選択肢を変更したときの処理
  const handleChange = (event) => {
    const newValue = event.target.value; // 選択された値を取得
    setSelectedValue(newValue); // 状態を更新
    if (onChange) {
      onChange(newValue); // 親コンポーネントへ通知
    }
  };

  return (
    <div className="dropdown">
      {/* ラベル表示 */}
      {label && <label className="dropdown-label">{label}</label>}

      {/* プルダウンのセレクトボックス */}
      <select
        className="dropdown-select"
        value={selectedValue} // 選択された値を設定
        onChange={handleChange} // 値変更時のイベントを設定
      >
        {/* プレースホルダーとして最初に表示 */}
        <option value="" disabled>
          {placeholder}
        </option>

        {/* 配列で渡された選択肢を順に表示 */}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default Dropdown;
