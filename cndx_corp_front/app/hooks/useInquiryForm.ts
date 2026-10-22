import { useState } from 'react';
  // データ型は設定
  type DynamicField = string | number | boolean;
/**
 * フォームデータと動的フィールドデータの管理に使用され、追加、削除、編集の操作をサポートします。
 * @returns 
 */  
const useInquiryForm = () => {
  // formData フォーム入力値を格納
  const [formData, setFormData] = useState<{ [key: string]: string }>({});
  // データに オブジェクトの配列を格納
  const [data, setData] = useState<{ id: number; [key: string]: DynamicField }[]>([]);

  // 項目名の変更を監視
  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setFormData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
  };

  // 削除関数は初期化（指定IDの結果）
  const deleteResult = (id: number) => {
    setData((prevData) => prevData.filter((item) => item.id !== id));
  };

  // 更新関数は初期化（指定IDの結果）
  const updateResult = (id: number, updatedFields: Partial<{ [key: string]: DynamicField }>) => {
    // undefined項目をクリアする
    // const validFields = Object.keys(updatedFields).reduce((acc, key) => {
    //   const value = updatedFields[key];
    //   if (value !== undefined) {
    //     acc[key] = value;
    //   }
    //   return acc;
    // }, {} as { [key: string]: DynamicField });

    // undefined の値を持つフィールドを除外
    const validFields = Object.fromEntries(
      Object.entries(updatedFields).filter(([, value]) => value !== undefined) 
    ) as { [key: string]: DynamicField };
  
    // データを更新
    setData((prevData) =>
      prevData.map((item) =>
        item.id === id ? { ...item, ...validFields } : item
      )
    );
  };
  
  return {
    formData,
    setFormData,
    data,
    setData,
    handleInputChange,
    deleteResult,
    updateResult,
  };
};

export default useInquiryForm;
