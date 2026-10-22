import {
  PageHeader,
  PageHeaderDescription,
  PageHeaderHeading,
} from "~/components/page-header";
import { Shell } from "~/components/shell";

import { useEffect, useState } from "react";

export default function SessionUserStatusErrorPage() {
  const [messages, setMessages] = useState<string[]>([]);

  useEffect(() => {
    // sessionStorageからエラーメッセージを取得
    const errorMessage = sessionStorage.getItem("sessionUserStatusErrorMessage");
    console.log("[SessionUserStatusErrorPage] sessionStorageから取得:", errorMessage);
    
    if (errorMessage) {
      setMessages([errorMessage]);
      // ロールバック時にメッセージを表示できるように、sessionStorageから削除しない
    } else {
      // エラーメッセージがない場合のデフォルトメッセージ
      setMessages(["ユーザーステータスが変更されました。"]);
    }
  }, []);

  return (
    <>
      <head>
        <title>Session User Status Error</title>
      </head>
      <div className="flex min-h-screen items-start justify-center pt-8">
        <Shell className="w-[350px]">
          <PageHeader
            id="session-user-status-error-page-header"
            aria-labelledby="session-user-status-error-page-header-heading"
            className="text-center"
          >
            {messages.map((msg, index) => (
              <PageHeaderDescription key={index} className="w-full whitespace-pre-line">
                <strong>{msg}</strong>
              </PageHeaderDescription>
            ))}
          </PageHeader>
        </Shell>
      </div>
    </>
  );
}

