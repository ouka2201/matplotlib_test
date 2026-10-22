import { LogInButton } from "~/components/auth/login-button";
import {
  PageHeader,
  PageHeaderDescription,
  PageHeaderHeading,
} from "~/components/page-header";
import { Shell } from "~/components/shell";

export default function SessionExpiredPage() {
  return (
    <>
      <head>
        <title>Session Expired</title>
      </head>
      <Shell className="w-[350px]">
        <PageHeader
          id="session-expired-page-header"
          aria-labelledby="session-expired-page-header-heading"
          className="text-center"
        >
          <PageHeaderHeading size="sm">タイムアウト</PageHeaderHeading>
          <PageHeaderDescription className="w-full">
            セッションがタイムアウトしました。
          </PageHeaderDescription>
          <PageHeaderDescription className="w-full">
            ログインする場合は
          </PageHeaderDescription>
          <PageHeaderDescription className="w-full">
            TOP画面に再度アクセスしてください。
          </PageHeaderDescription>
          {/* SAML削除対応 Start
          <PageHeaderDescription className="w-full">
            再開する場合は再ログインしてください。
          </PageHeaderDescription>
          SAML削除対応 End */}
        </PageHeader>
        {/* SAML削除対応 Start
        <LogInButton />
        SAML削除対応 End */}
      </Shell>
    </>
  );
}
