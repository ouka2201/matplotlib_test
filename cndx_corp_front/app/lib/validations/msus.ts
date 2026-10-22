import * as z from "zod";
import { commonSchema } from "./validationBase";
import { format } from "date-fns";
import { Messages } from "~/constants/messages/message";

// フィールドラベル (共通化)
export const FieldLabels = {
  user_name: "氏名",
  email_address: "メールアドレス",
  user_role: "権限",
  user_status: "ステータス",
};

export const userInfoSchema = z.object({
  user_name: commonSchema
    .nonEmptyString(FieldLabels.user_name)
    .and(commonSchema.stringInMaxRange(FieldLabels.user_name, 50)),
  email_address: commonSchema
    .nonEmptyString(FieldLabels.email_address)
    .email(Messages.VALIDATION.email.invalid)
    .and(commonSchema.stringInMaxRange(FieldLabels.email_address, 100)),
  user_role: commonSchema.nonEmptyString(FieldLabels.user_role),
  user_status: commonSchema.nonEmptyString(FieldLabels.user_status),
});

export const msusSchema = z.object({
  rows: z.array(userInfoSchema),
});
