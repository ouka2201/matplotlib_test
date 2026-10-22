// import type { MetaFunction } from "@remix-run/node";
import { useState } from "react";

import { SignInForm } from "~/components/auth/signin-form";
import { Shell } from "~/components/shell";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import LoginErrorPage from "./login-error";

// export const meta: MetaFunction = () => {
//   return [
//     { title: "ログイン" },
//     { name: "description", content: "Sign in to your account" },
//   ];
// };

export default function SignInPage() {
  const [error, setError] = useState<string | null>(null);

  // エラーがある場合はログインエラー画面を表示（SAMLレスポンス時と同じパターン）
  if (error) {
    return <LoginErrorPage messages={[error]} />;
  }

  return (
    <>
      <Shell className="max-w-lg">
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl">
              <div className="login-title">
                {/* <div className="flex flex-col sm:flex-row items-center justify-center sm:gap-4 gap-2 py-6"> */}
                <div className="flex flex-col sm:flex-row items-center justify-center sm:gap-8 gap-6 py-6">
                  {/* <div className="tepco"></div>
                  <div className="lecmoc-logo"></div> */}
                  <div
                    className="tepco"
                    style={{ height: 48, width: 150, backgroundSize: "contain", backgroundRepeat: "no-repeat", backgroundPosition: "center" }}
                  />
                  <div
                    className="lecmoc-logo"
                    style={{ height: 48, width: 135, backgroundSize: "auto 135%", backgroundRepeat: "no-repeat", backgroundPosition: "center" }}
                  />
                </div>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <SignInForm onError={setError} />
          </CardContent>
        </Card>
      </Shell>
    </>
  );
}
