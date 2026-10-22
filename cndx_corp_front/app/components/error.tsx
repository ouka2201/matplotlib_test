import React from "react";
import styles from "../styles/middleBase.module.css";
import Text from "./text";
import Icon from "./icon";

interface ErrorDetails {
  text: string;
  link?: string;
}

interface ErrorBoxProps {
  label?: string; 
  details?: ErrorDetails[]; // 配列で受け取る
  errorMessage?: string | string[];
}

const ErrorBox: React.FC<ErrorBoxProps> = ({
  label = "エラー項目の詳細",
  details = [], // デフォルトを空配列に
  errorMessage,
}) => {

  // errorMessageが文字列のときに、カンマ区切りで改行を挿入する
  const formatErrorMessage = (msg: string) => {
    return msg.split(",").map((line, index) => (
      <div key={index}>・{line.trim()}<br /></div>
    ));
  };

  return (
    <div className={styles.errorBox}>
      <div className={styles.errorBoxLabel}>
        <Icon name="error-pink" />
        <Text content={label} color="white" weight="bold" />
      </div>
      <div className={styles.errorBoxDetails}>
        {/* エラーメッセージの詳細部分 */}
        {details.length > 0 && (
          <div
            style={{
              color: "red",
              fontWeight: "bold",
              whiteSpace: "pre-line", // 改行が有効に
            }}
          >
            {details.map((detail, index) => (
              <div key={index}>
                {detail.link && detail.link.trim() ? (
                  <Text content={`・${detail.text}`} color="red" href={detail.link} />
                ) : (
                  <Text content={`・${detail.text}`} color="red" weight="bold" />
                )}
              </div>
            ))}
          </div>
        )}

        {/* errorMessageの表示部分 */}
        {errorMessage && (
          <div className="excelupload-content-error-detail">
            <div className="excelupload-content-error-detail-text-main">
              {Array.isArray(errorMessage)
                ? errorMessage.map((message, index) => (
                    <div key={index}>
                      ・{message}
                      <br />
                    </div>
                  ))
                : errorMessage}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


export default ErrorBox;