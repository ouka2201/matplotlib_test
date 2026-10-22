import React, { useRef, useState } from "react";
import "../styles/CNTable.css";
import styles from "../styles/middleBase.module.css";
import Button from "./button";
import Layout from "./layout";
import Text from "./text";


type CustomerItem = {
  bank_name: string;
  branch_name: string;
  corporation_name: string;
  user_name: string;
  fiscal_year: string;
  creation_datetime: string;
  registration_seq: number;
  status: string;
  file_id: string;
  bank_code: string;
  branch_code: string;
  corporate_number: string;
  building_id: string;
  report_type: string;
  update_datetime: string; //更新日時
  updateor: string; //更新者
};

type CNTableProps = {
  data: CustomerItem[];
  selectedItem: CustomerItem | null;
  isLoading: boolean;
  error: string;
  handleCheckboxChange: (item: CustomerItem) => void;
  handleNavigate: (item: CustomerItem) => void;
  handleDownloadPdf: (item: CustomerItem) => void;
};

const headers = [
  { key: "bank_name", label: "金融機関名", width: 10 },
  { key: "branch_name", label: "支店名", width: 10 },
  { key: "corporation_name", label: "お客さま名", width: 15 },
  { key: "user_name", label: "担当者", width: 10 },
  { key: "fiscal_year", label: "対象年度", width: 8 },
  { key: "creation_datetime", label: "情報登録日", width: 10 },
  { key: "registration_seq", label: "登録回数", width: 8 },
  { key: "status", label: "CO2企業カルテ", width: 15 },
];


const CNTable: React.FC<CNTableProps> = ({
  data,
  selectedItem,
  isLoading,
  handleCheckboxChange,
  handleNavigate,
  handleDownloadPdf,
}) => {
  const [columnWidths, setColumnWidths] = useState(headers.map((h) => h.width));
  const resizingIndex = useRef<number | null>(null);
  const startX = useRef<number>(0);
  const startWidths = useRef<number[]>([]);

  const handleMouseDown = (
    index: number,
    event: React.MouseEvent<HTMLSpanElement, MouseEvent>
  ) => {
    resizingIndex.current = index;
    startX.current = event.clientX;
    startWidths.current = [...columnWidths];

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleMouseMove = (event: MouseEvent) => {
    if (resizingIndex.current === null) return;

    const deltaX = event.clientX - startX.current;
    const totalWidth = startWidths.current.reduce((sum, w) => sum + w, 0);
    const parentWidth = 100;
    const widthPerPixel = totalWidth / parentWidth;
    const index = resizingIndex.current;
    const newWidths = [...startWidths.current];

    const deltaPercent = deltaX * widthPerPixel * 0.08;
    if (newWidths[index] + deltaPercent < 5 || newWidths[index + 1] - deltaPercent < 5) return;

    newWidths[index] += deltaPercent;
    newWidths[index + 1] -= deltaPercent;

    setColumnWidths(newWidths);
  };

  const handleMouseUp = () => {
    resizingIndex.current = null;
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
  };

  return (
    //全体のコンテナ
    <div className={styles.CNtableContainer}>
      {/* ドロップダウンとボタン、件数表示 */}
      <Layout justify="between" padding={16}>
        <Layout gap={16}>
          <Button variant="secondary" text="実行" />
        </Layout>
        {/* 件数表示 */}
        {displayCount > 0 && (
          <div className="report-table-menu-itemsdisplayed-number">
            {customerItems.length.toLocaleString()} 件中
            {displayCount.toLocaleString()} 件
          </div>
        )}
      </Layout>
      {/* エラー表示 */}
      {errorMessage && (
        <div className="report-table-error">
          <div className="excelupload-content-error-detail-text-main">
            {errorMessage}
          </div>
        </div>
      )}
      <table className={styles.CNtable}>
        <thead>
          <tr>
            <th className={styles.checkboxColumn}>
              <input type="checkbox" />
            </th>
            {headers.map((header, index) => (
              <th key={header.key} style={{ width: `${columnWidths[index]}%`, position: "relative" }}>
                <Text content={header.label} size="sm" color="gray-dark" weight="bold" />
                {index < headers.length - 1 && (
                  <span
                    role="button"
                    tabIndex={0}
                    className={styles.resizeHandle}
                    onMouseDown={(e) => handleMouseDown(index, e)}
                  />
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length > 0 ? (
            data.map((item, index) => {
              const isSelected =
                selectedItem &&
                selectedItem.bank_code === item.bank_code &&
                selectedItem.branch_code === item.branch_code &&
                selectedItem.corporate_number === item.corporate_number &&
                selectedItem.building_id === item.building_id &&
                selectedItem.fiscal_year === item.fiscal_year &&
                selectedItem.report_type === item.report_type &&
                selectedItem.registration_seq === item.registration_seq &&
                selectedItem.file_id === item.file_id;

              const checkboxDisabled = item.status === "2" || item.status === "1";

              return (
                <tr key={index}>
                  <td className={styles.checkboxColumn}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleCheckboxChange(item)}
                      disabled={checkboxDisabled}
                    />
                  </td>
                  {headers.map((header, colIndex) => (
                    <td key={header.key} style={{ width: `${columnWidths[colIndex]}%` }}>
                      {header.key === "corporation_name" ? (
                        <span
                          role="button"
                          tabIndex={0}
                          onClick={() => handleNavigate(item)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              handleNavigate(item);
                            }
                          }}
                          className={styles.linkText}
                          style={{ cursor: "pointer" }}
                        >
                          {item[header.key]}
                        </span>
                      ) : header.key === "status" ? (
                        item.status === "2" ? (
                          <span
                            role="button"
                            tabIndex={0}
                            onClick={() => handleDownloadPdf(item)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                handleDownloadPdf(item);
                              }
                            }}
                            className={styles.linkText}
                            style={{ cursor: "pointer" }}
                          >
                            作成済
                          </span>
                        ) : (
                          <span>{isLoading && isSelected ? "処理中" : item.status === "0" ? "未作成" : item.status === "1" ? "処理中" : item.status === "9" ? "エラー" : "不明"}</span>
                        )
                      ) : (
                        <Text content={item[header.key as keyof CustomerItem]} />
                      )}
                    </td>
                  ))}
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan={headers.length + 1} className={styles.noData}>
                データがありません
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export default CNTable;
