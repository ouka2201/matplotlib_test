import React, { useState } from "react";
import styles from "../styles/middleBase.module.css"
import Button from "./button"
import Icon from "./icon"
import Text from "./text"
import Input from "./input"
import CNTable from "./CNTable"
import CNinfo from "./CNinfo"

const CNtableData = [
  {
    branchName: "東京支店",
    bankName: "テプ銀行",
    customerName: { text: "テプコシステムズ", href: "https://example.com/john" },
    representative: "テプ　シス",
    fiscalYear: "2024",
    registrationDate: "2024-02-17",
    registrationCount: 5,
    record: { text: "作成済み", href: "https://example.com/record/john" },
  },
  {
    branchName: "大阪支店",
    bankName: "テプ銀行aaaaaaaaaaaa",
    customerName: { text: "テプコシステムズaaaaaaaaaaaaaaa" },
    representative: "テプコ　EP",
    fiscalYear: "2023",
    registrationDate: "2023-12-25",
    registrationCount: 3,
    record: { text: "作成済み", href: "https://example.com/record/jane" },
  },
];

const App: React.FC = () => {
  const [dropdownValue, setDropdownValue] = useState<string>("");
  const [yearRange, setYearRange] = useState<{ startDate: string; endDate: string }>({
    startDate: "",
    endDate: "",
  });
  const [dateRange, setDateRange] = useState<{ startDate: string; endDate: string }>({
    startDate: "",
    endDate: "",
  });

  const handleDropdownChange = (value: string) => {
    setDropdownValue(value);
    console.log("ドロップダウンの選択肢:", value);
  };

  const handleYearRangeChange = (value: { startDate: string; endDate: string }) => {
    setYearRange(value);
    console.log("年度範囲:", value);
  };

  const handleDateRangeChange = (value: { startDate: string; endDate: string }) => {
    setDateRange(value);
    console.log("日付範囲:", value);
  };

  const handleClick = () => {
    alert('Button clicked!');
  };

  return (
    <div className={styles.mainContainer}>
      {/* Primaryボタン、左にアイコン */}
      <Button
        variant="primary"
        text="あいうえお"
				// icon={<Icon name="upload" />}
        // iconPosition="left"
        onClick={handleClick}
      />

      {/* Secondaryボタン、右にアイコン、非活性 */}
      <Button
        variant="secondary"
        text="あ"
        icon={<Icon name="upload" />}
        iconPosition="left"
        onClick={handleClick}
      />
      
      {/* Defaultボタン、アイコンなし */}
      <Button
        variant="default"
        text="デフォルト"
        // onClick={handleClick}
      />

      <Text size="sm" color="red" weight="bold" >あいうえお</Text>

      <div className={styles.layoutRow}>
        <Button
          variant="secondary"
          text="あいうえお"
        />

        <div className={styles.inputField}>
          <Text content="abcde"/>
          <Icon name="calendar"/>
        </div>
      </div>

      {/* <Input label="price" required unit="$" supportText="Hey!"/>
      
      <CNTable data={CNtableData} /> */}

      {/* 通常の入力欄 */}
      <Input
        label="入力"
        supportText="入力欄"
        required
        unit="kg"
        onChange={(e) => console.log("入力内容:", e.target.value)}
      />

      {/* ドロップダウン */}
      <Input
        label="選択肢"
        typeOption="dropdown"
        dropdownOptions={["選択肢1", "選択肢2", "選択肢3"]}
        onChange={handleDropdownChange}
        supportText="ドロップダウンメニュー"
      />

      {/* 年度範囲 */}
      <Input
        label="年度範囲"
        typeOption="yearRange"
        onChange={handleYearRangeChange}
        supportText="開始年と終了年"
      />

      {/* 日付範囲 */}
      <Input
        label="日付範囲"
        typeOption="dateRange"
        onChange={handleDateRangeChange}
        supportText="開始日と終了日"
      />
      <CNinfo/>
      </div>
    
  );
};

export default App;