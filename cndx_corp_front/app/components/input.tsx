import React, { useState } from "react";
import styles from "../styles/middleBase.module.css";
import Text from "./text";

// InputPropsの定義
type InputProps = {
  label?: string;                                
  required?: boolean;                            
  supportText?: string;                          
  unit?: string;                                 
  className?: string;                            
  errorMessage?: string;                         
  typeOption?: "dropdown" | "yearRange" | "dateRange";
  dropdownOptions?: string[];                    
  onChange: (value: string) => void;                  
} & (
  | (React.InputHTMLAttributes<HTMLInputElement> & {
      typeOption?: Exclude<"dropdown" | "yearRange" | "dateRange", "dropdown">;
    })
  | (React.SelectHTMLAttributes<HTMLSelectElement> & {
      typeOption: "dropdown";
    })
);

const Input: React.FC<InputProps> = ({
  label,
  required,
  supportText,
  unit,
  className,
  errorMessage,
  typeOption,
  dropdownOptions,
  onChange,
  ...props
}) => {
  // 内部エラーメッセージ状態
  const [error, setError] = useState<string>("");
  // 範囲入力用の状態
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // 外部からのエラーがあればそちらを優先（errorMessageが空文字の場合も内部エラーを使う）
  const displayError = errorMessage ? errorMessage : error;

  // --- 共通のonBlurハンドラ --- //
  const handleBlur = (
    e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    if (required && !e.target.value.trim()) {
      setError("必須項目です");
    } else if (
      e.target instanceof HTMLInputElement &&
      !e.target.validity.valid
    ) {
      setError("入力値が正しくありません");
    } else {
      setError("");
    }
    if (props.onBlur) {
      props.onBlur(e);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;  // event.target.value で入力された値を取得
    if (onChange) {
      onChange(value);  // 受け取ったvalueをそのまま親のonChangeへ渡す
    }
  };

  // --- 範囲入力用のonBlurハンドラ --- //
  const handleBlurRange = () => {
    if (required && (!startDate.trim() || !endDate.trim())) {
      setError("必須項目です");
    } else {
      setError("");
    }
  };

  // --- 範囲入力の開始日変更 --- //
  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setStartDate(value);
    onChange({ startDate: value, endDate });
    if (required && value.trim() && endDate.trim()) {
      setError("");
    }
  };

  // --- 範囲入力の終了日変更 --- //
  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setEndDate(value);
    onChange({ startDate, endDate: value });
    if (required && startDate.trim() && value.trim()) {
      setError("");
    }
  };

  

  // CSS Modules用のクラスを返すヘルパー
  const getInputClass = (base: keyof typeof styles) =>
    `${styles[base]} ${displayError ? styles.error : ""}`;

  return (
    <div className={`${styles.inputContainer} ${className || ""}`}>
      {label && (
        <label className={styles.inputLabel}>
          <Text content={label} color="gray-dark" size="sm"/>
          {required && <div className={styles.requiredMark }><Text content="必須" color="white" size="sm"/></div>}
        </label>
      )}

      {supportText && <Text content={supportText} color="gray-dark" size="sm"/>}

      {typeOption === "dropdown" && dropdownOptions ? (
        // --- ドロップダウンの場合 --- //
        <div className={styles.inputWrapper}>
          <select
            className={getInputClass("inputField")}
            onChange={(e) => onChange(e.target.value)}
            onBlur={handleBlur}
            defaultValue=""
            {...(props as React.SelectHTMLAttributes<HTMLSelectElement>)}
          >
            {/* 初期値として「選択してください」を追加 */}
            <option value="">選択してください</option>
            {dropdownOptions.map((option, index) => (
              <option key={index} value={option}>
                <Text content={option} />
              </option>
            ))}
          </select>
          {unit && <Text content={unit} />}
        </div>
      ) : typeOption === "yearRange" ? (
        // --- 年度範囲の場合 --- //
        <div className={styles.inputWrapper}>
          <input
            type="number"
            className={getInputClass("inputField")}
            placeholder="yyyy"
            value={startDate}
            onChange={handleStartDateChange}
            onBlur={handleBlurRange}
            {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
          />
          <Text content="-" />
          <input
            type="number"
            className={getInputClass("inputField")}
            placeholder="yyyy"
            value={endDate}
            onChange={handleEndDateChange}
            onBlur={handleBlurRange}
            {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
          />
        </div>
      ) : typeOption === "dateRange" ? (
        // --- 日付範囲の場合 --- //
        <div className={styles.inputWrapper}>
          <input
            type="date"
            className={getInputClass("inputField")}
            placeholder="yyyy"
            value={startDate}
            onChange={handleStartDateChange}
            onBlur={handleBlurRange}
            {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
          />
          <Text content="-" />
          <input
            type="date"
            className={getInputClass("inputField")}
            value={endDate}
            onChange={handleEndDateChange}
            onBlur={handleBlurRange}
            {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
          />
        </div>
      ) : (
        // --- 通常の入力欄の場合 --- //
        <div className={styles.inputWrapper}>
          <input
            className={getInputClass("inputField")}
            placeholder="入力してください"
            onBlur={handleBlur}
            onChange={handleChange}
            {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
          />
          {unit && <Text content={unit} />}
        </div>
      )}

      {displayError && (
        <div className={styles.errorMessage}>
          <Text content={displayError} color="red" size="sm"/>
        </div>
      )}
    </div>
  );
};

export default Input;
