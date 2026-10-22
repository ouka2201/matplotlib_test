import * as z from "zod";
import { Messages } from "~/constants/messages/message";

export const authSchema = z.object({
  email_address: z
    .string()
    .nonempty({ message: "メールアドレスを入力してください。" })
    .email(Messages.VALIDATION.email.invalid)
    .max(100, { message: "メールアドレスは100文字以内で入力してください。" }),
  password: z
    .string()
    .nonempty({ message: "パスワードを入力してください。" }) 
    .max(100)
    .regex(/^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/, {
      message: "パスワードは大文字・小文字・記号・半角英数を含む8文字以上で入力してください。",
  }),
});

export const csrfTokenSchema = z.object({
  token: z.string(),
});