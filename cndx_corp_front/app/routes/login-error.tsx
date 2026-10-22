import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  PageHeader,
  PageHeaderDescription,
  PageHeaderHeading,
} from "~/components/page-header";
import { Shell } from "~/components/shell";

export default function LoginErrorPage({ messages }: { messages?: string[] }) {
  const [searchParams] = useSearchParams();
  const [errorMessages, setErrorMessages] = useState<string[]>(messages || []);

  useEffect(() => {
    // URLパラメータからエラーメッセージを取得
    const errorParam = searchParams.get("error");
    if (errorParam) {
      setErrorMessages([errorParam]);
    }
  }, [searchParams]);

  return (
    <>
      <head>
        <title>Login Error</title>
      </head>
      <div className="flex min-h-screen items-start justify-center pt-8">
        <Shell className="w-[350px]">
          <PageHeader
            id="login-error-page-header"
            aria-labelledby="login-error-page-header-heading"
            className="text-center"
          >
            <PageHeaderHeading size="sm">ログインエラー</PageHeaderHeading>
            {errorMessages.length > 0 ? (
              errorMessages.map((msg, index) => (
                <PageHeaderDescription key={index} className="w-full whitespace-pre-line">
                  {msg}
                </PageHeaderDescription>
              ))
            ) : (
              <PageHeaderDescription>
                入力されたアカウント情報とログイン先のサービスとの連携に問題があります。
              </PageHeaderDescription>
            )}
          </PageHeader>
        </Shell>
      </div>
    </>
  );
}
