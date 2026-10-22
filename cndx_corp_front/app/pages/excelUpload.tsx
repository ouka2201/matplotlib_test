import axios, { isAxiosError } from "axios";
import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useSession } from "~/components/layout/session-provider";
import { AlertModal } from "~/components/modal/alert-modal";
import { Button, Icon, ItemPair, Layout, styles, Text } from "../components/import";

const BASE_URL = process.env.VITE_API_URL;
// const BASE_URL = `${window.location.protocol}${process.env.VITE_API_URL}`
//const BASE_URL = "http://10.191.30.4:10072";
const ExcelUpload: React.FC = () => {

  const navigate = useNavigate(); // 画面遷移用フック
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string | null>(null); // 選択されたファイル名を保持
  const [file, setFile] = useState<File | null>(null); // Fileオブジェクトを保持
  const [errorMessage, setErrorMessage] = useState<string | null>(null); // エラーメッセージ用の状態
  const [registerError, setRegisterError] = useState<boolean>(false); // 登録時のエラー発生フラグ
  const [isPopupOpen, setIsPopupOpen] = useState(false); // ポップアップの表示状態
  const [loading, setLoading] = useState(false); // 処理中状態
  const [message, setMessage] = useState<string | null>(null); // メッセージ表示

  const extensionList = [".xlsx"];

  const { session, clearSession } = useSession();
  const [token, setToken] = useState<string | null>(session?.token ?? null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sessionData = sessionStorage.getItem("session");
      if (sessionData) {
        setToken(JSON.parse(sessionData).token);
      }
    }
  }, [session]);

  // ボタンをクリックしてファイル選択ダイアログを開く
  const handleButtonClick = () => {
    // ボタン自体の情報をログに出力
    if (fileInputRef.current) {
      console.log("fileInputRefが参照されました:", fileInputRef.current); // fileInputRefが参照されているか確認
      fileInputRef.current.click(); // ダイアログを開く
    } else {
      console.error("fileInputRefがnullです");
    }
  };

  // ファイル選択後の処理
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) {
      if (!file) {
        setErrorMessage("ファイルが選択されていません");
      }
      return;
    }

    const selectedFile = files[0];
    const fileExtension = selectedFile.name.slice(
      selectedFile.name.lastIndexOf(".")
    );

    if (!extensionList.includes(fileExtension)) {
      setErrorMessage("許可されていないファイル形式です");
      return;
    }

    setFileName(selectedFile.name); // ファイル名を設定
    setFile(selectedFile); // Fileオブジェクトを保存

    // `fileName` を localStorage に保存
    localStorage.setItem("fileName", selectedFile.name);

    // handleRegisterClickで発生したエラーをクリア
    //handleRegisterClick時のエラー⇒handleButtonClick時のエラーの順でエラーが発生した場合、handleRegisterClick時のファイルが残っており、わかりづらくなる可能あり(後に対応)
    if (registerError) {
      setErrorMessage(null);
      setRegisterError(false);
    } else {
      setErrorMessage(null); // `handleFileChange`のエラーをクリア
    }

    console.log("選択されたファイル:", selectedFile);
  };

  // ポップアップを開く
  const openPopup = () => setIsPopupOpen(true);

  // ポップアップを閉じる
  const closePopup = () => setIsPopupOpen(false);

  //登録ボタンの処理
  const handleRegisterClick = async () => {
    if (file) {
      console.log(message);
      setLoading(true); // 処理中状態にする
      setMessage(null); // 前のメッセージをクリア
      try {
        // // APIに送信するデータ(mock)
        const formData = new FormData();
        formData.append("file", file); // fileオブジェクトをFormDataに追加

        // // APIに送信するデータ
        // const formData = new FormData();
        // formData.append("file", file); // fileオブジェクトをFormDataに追加

        // FormDataに追加されたすべての項目をループして確認
        formData.forEach((value, key) => {
          console.log(`${key}: ${value instanceof File ? value.name : value}`);
        });

        console.log("送信データ:", formData);

        // mockにデータを送信(mock)
        // const apiUrl = "http://localhost:5173/file/check-tansfer";
        // const response = await axios.post(apiUrl, formData, {
        //   headers: {
        //     "Content-Type": "multipart/form-data", // multipart形式で送信
        //   },
        // });

        //APIにデータを送信
        // const apiUrl = "http://10.191.30.4:10072/api/file/check-transfer";
        // mockにデータを送信(mock)
        const apiUrl = `${BASE_URL}/api/file/check-transfer`;

        const response = await axios.post(apiUrl, formData, {
          headers: {
            "Content-Type": "multipart/form-data", // multipart形式で送信
            Authorization: `Bearer ${token}`
          },
        });

        //成功時
        console.log("APIレスポンス:", response.data);
        // HTTPステータスコードを取得
        // HTTPステータスコードでの分岐
        console.log("APIレスポンス:", response.data);
        const statusCode = response.status;
        console.log("HTTPステータスコード:", statusCode);

        switch (statusCode) {
          case 200:
            console.log("正常系:", response.data);
            setErrorMessage(null);
            setMessage("登録完了");
            setLoading(false);
            closePopup(); // 処理後にポップアップを閉じる
            navigate("/cndx-corp/excel/success"); // 次のページに遷移
            break;
          default:
            console.error(`予期しないステータスコード: ${statusCode}`);
            setErrorMessage(`予期しないエラー。システム担当者に連絡してください。: ステータスコード ${statusCode}`);
            setRegisterError(true); // 登録エラー発生を記録
            setLoading(false);
            closePopup(); // 処理後にポップアップを閉じる
            break;
        }
      } catch (error) {
        // Axios のエラーオブジェクトを処理
        if (isAxiosError(error) && error.response) {
          // サーバーからのエラーレスポンスを処理
          const statusCode = error.response.status;
          const errorData = error.response.data;

          console.error("サーバーエラー:", errorData);
          console.error("HTTPステータスコード:", statusCode);

          if (statusCode == 401) {
            clearSession();
            sessionStorage.removeItem("session");
            return window.location.href = "/session-expired";
          }
          switch (statusCode) {
            case 400:
              console.error("バリデーションチェック不正");
              setErrorMessage(errorData.error_message_list || "不正な入力です");
              setRegisterError(true); // 登録エラー発生を記録
              setLoading(false);
              closePopup(); // 処理後にポップアップを閉じる
              break;
            // case 404:
            //   console.error("リソース存在しない");
            //   setErrorMessage("エラー: リソースが存在しません。");
            //   setRegisterError(true); // 登録エラー発生を記録
            //   setLoading(false);
            //   closePopup(); // 処理後にポップアップを閉じる
            //   break;
            // case 409:
            //   console.error("コンフリクトエラー");
            //   setErrorMessage("エラー: コンフリクトが発生しました。");
            //   setRegisterError(true); // 登録エラー発生を記録
            //   setLoading(false);
            //   closePopup(); // 処理後にポップアップを閉じる
            //   break;
            // case 412:
            //   console.error("マスタデータ不備");
            //   setErrorMessage("エラー: マスタデータが不完全です。");
            //   setRegisterError(true); // 登録エラー発生を記録
            //   setLoading(false);
            //   closePopup(); // 処理後にポップアップを閉じる
            //   break;
            case 500:
              console.error("システムエラー");
              setErrorMessage("エラー: サーバーエラーが発生しました。");
              setRegisterError(true); // 登録エラー発生を記録
              setLoading(false);
              closePopup(); // 処理後にポップアップを閉じる
              break;
            default:
              console.error(`予期しないステータスコード: ${statusCode}`);
              setErrorMessage(
                `予期しないエラー。システム担当者に連絡してください。: ステータスコード ${statusCode}`
              );
              setRegisterError(true); // 登録エラー発生を記録
              setLoading(false);
              closePopup(); // 処理後にポップアップを閉じる
              break;
          }
        } else {
          // ネットワークエラーまたはその他のエラー
          console.error("APIリクエスト中にエラーが発生しました:", error);
          setErrorMessage(
            "APIリクエスト中にエラーが発生しました。システム担当者に連絡してください。"
          );
          setRegisterError(true); // 登録エラー発生を記録
          setLoading(false);
          closePopup(); // 処理後にポップアップを閉じる
        }
      }
    } else {
      console.log("ファイルが選択されていません");
      setErrorMessage("ファイルが選択されていません");
      setRegisterError(true); // 登録エラー発生を記録
      setLoading(false);
      closePopup(); // 処理後にポップアップを閉じる
    }
  };
  return (
    <div className={styles.mainContainer}>
      <div className={styles.layoutTitle}>
        <Text size="xl" weight="bold">
          Excelアップロード
        </Text>
      </div>
      <Layout direction='row' align='center' gap={16}>
        <div>
          {/* ファイル選択をトリガーするボタン */}
          <Button
            variant="secondary"
            text="Excelデータ選択"
            icon={<Icon name="upload" />}
            iconPosition="left"
            onClick={handleButtonClick}
          />

          {/* 非表示のファイル入力 */}
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            accept=".xlsx"
            onChange={handleFileChange} // ファイル変更時に呼ばれる処理
          />
        </div>
      </Layout>
      <div className={styles.whiteBox}>
        <Text content="選択されたファイル" size="lg" weight="bold" />
        {/* ファイル名 */}
        {/* <div className={styles.pair80}>
					<span className={styles.labelBox}><Text content="ファイル名" color="gray"/></span>
					<span className={styles.contentBox}><Text content="abc.xlsx" color="gray"/></span>
				</div> */}
        <ItemPair
          label="ファイル名"
          content={fileName || "ファイルを選択してください"}
          is80
        />

        {/* エラー表示 */}
        {errorMessage && (
          <div className={styles.errorBox}>
            <div className={styles.errorBoxLabel}>
              <Icon name="error-pink" />
              <Text content="エラーがあります" color="white" weight="bold" />
            </div>
            <div className="content-error-detail">
              {Array.isArray(errorMessage) ? (
                <ul>
                  {errorMessage.map((message, index) => (
                    <li key={index}>{message}</li>
                  ))}
                </ul>
              ) : (
                <div className="content-error-detail-text-main">
                  {errorMessage}
                </div>
              )}
            </div>
          </div>
        )}
        <Button
          variant="primary"
          text="登録"
          onClick={openPopup} // ポップアップ表示
        />
      </div>
      {/* ポップアップ */}
      <AlertModal
        isOpen={isPopupOpen}
        onClose={() => closePopup()}
        onConfirm={handleRegisterClick}
        loading={loading}
        title="確認"
        description="登録を実行してもよいですか？"
        cancelText="いいえ"
        continueText="はい"
      />
    </div>
  );
};

export default ExcelUpload;
