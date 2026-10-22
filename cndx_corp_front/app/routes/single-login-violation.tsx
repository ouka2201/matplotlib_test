import {
  PageHeader,
  PageHeaderDescription,
} from "~/components/page-header";
import { Shell } from "~/components/shell";
// SAML削除対応 Start
// import { LogInButton } from "~/components/auth/login-button";
// SAML削除対応 End

export default function SingleLoginViolationPage() {
  return (
    <>
      <head>
        <title>Single Login Violation</title>
      </head>
      <div className="flex min-h-screen items-start justify-center pt-8">
        <Shell className="w-[350px]">
          <PageHeader
            id="single-login-violation-page-header"
            aria-labelledby="single-login-violation-page-header-heading"
            className="text-center"
          >
            <PageHeaderDescription className="w-full">
              別のデバイスまたはブラウザでログインされたため、
              このセッションは無効になりました。
            </PageHeaderDescription>
            <PageHeaderDescription className="w-full">
              ログインする場合は
            </PageHeaderDescription>
            <PageHeaderDescription className="w-full">
              TOP画面に再度アクセスしてください。
            </PageHeaderDescription>
          </PageHeader>
          {/* SAML削除対応 Start */}
          {/* <div className="mt-6 w-[350px]">
            <LogInButton />
          </div> */}
          {/* SAML削除対応 Start */}
        </Shell>
      </div>
    </>
  );
}

