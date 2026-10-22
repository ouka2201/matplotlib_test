import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import type { z } from "zod";

import { useMutation } from "@tanstack/react-query";
import { jwtDecode } from "jwt-decode";
import { useNavigate } from "react-router-dom";
import { Icons } from "~/components/icons";
import { useMenu } from "~/components/layout/menu-provider";
import { AuthJwtPayload, useSession } from "~/components/layout/session-provider";
import { PasswordInput } from "~/components/password-input";
import { Button } from "~/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "~/components/ui/form";
import { Input } from "~/components/ui/input";
import { useToast } from "~/components/ui/use-toast";
import { postData } from "~/lib/fetch";
import { logMessage } from "~/lib/logger";
import { authSchema } from "~/lib/validations/auth";

type Inputs = z.infer<typeof authSchema>;

interface SignInFormProps {
  onError?: (errorMessage: string) => void;
}

export function SignInForm({ onError }: SignInFormProps) {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { updateSession } = useSession();
  const { updateNaviItems } = useMenu();

  // react-hook-form
  const form = useForm<Inputs>({
    resolver: zodResolver(authSchema),
    defaultValues: {
      email_address: "",
      password: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: Inputs) => {
      return postData("/api/auth/login", data);
      // return postData("/api/user/insert", data);
    },
    onSuccess: (data) => {
      const decoded = jwtDecode<AuthJwtPayload>(data.token);
      const isAdminOrg = (orgId: string) =>
        ["TEP", "SYS"].includes(orgId.slice(0, 3));
      updateSession({
        name: decoded.name,
        // email: decoded.user_id,
        email: decoded.email_address,
        org_name: decoded.org_name,
        token: data.token,
        session_id: data.session_id, // レスポンスからsession_idを取得
        authorityInfo: {
          user_id: decoded.name,
          org_id: decoded.org_id,
          name: decoded.name,
          role: decoded.role,
          org_type_code: decoded.org_type_code,
          authority_code_map: decoded.authority_code_map
        },
        userRoleFlags: {
          isEpAdmin: isAdminOrg(decoded.org_id) && decoded.role === "0",
          isEpGeneral: decoded.org_id.slice(0, 3) === "TEP" && decoded.role === "1",
          isBank: decoded.org_id.slice(0, 3) === "BNK" && decoded.role === "9",
          isBranchAdmin: decoded.org_id.slice(0, 3) === "BNK" && decoded.role === "0",
          isBranchGeneral: decoded.org_id.slice(0, 3) === "BNK" && decoded.role === "1",
          isRepAdmin: decoded.org_id.slice(0, 3) === "REP" && decoded.role === "0",
          isRepGeneral: decoded.org_id.slice(0, 3) === "REP" && decoded.role === "1",
          isTcsAdmin: decoded.org_id.slice(0, 3) === "TCS" && decoded.role === "0",
          isTcsGeneral: decoded.org_id.slice(0, 3) === "TCS" && decoded.role === "1",
          isJfs: decoded.org_id.slice(0, 3) === "JFS",
          isZrb: decoded.org_id.slice(0, 3) === "ZRB",
          isAse: decoded.org_id.slice(0, 3) === "ASE",
        },
        refreshToken: data.refreshToken,
        masterData: data.master,
      });

      // updateNaviItems(data.token);
      updateNaviItems(decoded.authority_code_map);
      // ログイン成功後、認証済みフラグを設定
      sessionStorage.setItem("isAuthenticated", "true");
      setTimeout(() => {
        navigate("/common/cmtp01");
      }, 100);
      toast({
        title: "ログイン成功",
      });
    },
    onError: (error: any) => {

      const errorMessage = error?.data?.message || error?.message || "ログインに失敗しました。システム管理者にお問い合わせください。";

      // ユーザーが見つからない場合やパスワードが間違っている場合はフォームエラーとして表示
      // if (errorMessage === "User not found" || errorMessage.includes("存在しないユーザ")) {
      //   form.setError("email_address", {
      //     type: "manual",
      //     message: "存在しないユーザです。",
      //   });
      // } else if (errorMessage === "Incorrect password" || errorMessage.includes("パスワードが間違っています")) {
      //   form.setError("password", {
      //     type: "manual",
      //     message: "パスワードが間違っています。",
      //   });
      // } else {
      //   if (onError) {
      //     onError(errorMessage);
      //   }
      // }
      const isAuthError =
        error?.status === 401 ||
        error?.response?.status === 401 ||
        /User not found|Incorrect password|存在しないユーザ|パスワードが間違っています|認証/i.test(errorMessage);

      if (isAuthError) {
        const msg = "メールアドレスまたはパスワードが正しくありません。";
        // どちらか一方に出す（最小）：email に表示
        form.setError("email_address", { type: "manual", message: msg });
        // もし両方に出したいなら下も有効化
        // form.setError("password", { type: "manual", message: msg });
        return;
      }

      if (onError) onError(errorMessage);
    },
  });

  async function onSubmit(data: Inputs) {
    logMessage({ message: "Sign in form submitted", object: data });
    mutation.mutate(data);
  }

  return (
    <Form {...form}>
      <form className="grid gap-4" onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="email_address"
          render={({ field }) => (
            <FormItem>
              <FormLabel className={form.formState.errors.email_address ? "text-black" : ""}>
                メールアドレス
              </FormLabel>
              <FormControl>
                <Input
                  type="text"
                  placeholder="xx@xx.jp"
                  autoComplete="username"
                  className="w-full"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel className={form.formState.errors.password ? "text-black" : ""}>
                パスワード
              </FormLabel>
              <FormControl>
                <PasswordInput placeholder="**********" className="w-full" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button variant="primary" type="submit" disabled={mutation.isPending} className="w-full">
          {mutation.isPending && (
            <Icons.spinner
              className="mr-2 size-4 animate-spin"
              aria-hidden="true"
            />
          )}
          ログイン
          <span className="sr-only">ログイン</span>
        </Button>
      </form>
    </Form>
  );
}
