// routes/auth/signin/reset-password.tsx

import { Form } from "@remix-run/react";

export default function ResetPasswordPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-2xl font-bold mb-4">パスワードリセット</h1>
      <Form method="post" className="w-full max-w-md">
        <input
          type="email"
          name="email"
          required
          className="w-full px-4 py-2 border rounded"
        />
        <button type="submit" className="mt-4 bg-blue-500 text-white px-4 py-2 rounded">
          リセットリンクを送信
        </button>
      </Form>
    </div>
  );
}
