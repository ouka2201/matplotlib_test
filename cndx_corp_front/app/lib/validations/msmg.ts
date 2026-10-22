import { format } from "date-fns";
import * as z from "zod";
import { Messages } from "~/constants/messages/message";
import { commonSchema } from "./validationBase";

// フィールドラベル (共通化)
export const FieldLabels = {
  company_name: "お客さま名",
  corporate_number: "法人番号",
  company_address: "所在地",
  user_id: "アプリユーザーID",
  email_address: "メールアドレス",
  org_name: "組織名",
  user_name: "氏名",
  org_id: "組織ID",
  org_type_code: "組織種別コード",
  user_role: "ロール",
  agreement_category: "同意書取得経路",
  consent_receipt_date: "同意書受領日",
};

// 担当者情報スキーマ
export const contractPersonSchema = z
  .object({
    user_id: z.string().optional(),
    email_address: commonSchema
      .nonEmptyString(FieldLabels.email_address)
      .max(100, { message: Messages.validation.maxLength(FieldLabels.email_address, 100) }),
    org_name: z.string().optional(),
    user_name: z.string().optional(),
    org_id: z.string().optional(),
    org_type_code: z.string().optional(),
    user_role: z.string().optional(),
    agreement_category: commonSchema.nonEmptyString(
      FieldLabels.agreement_category
    ),
    consent_receipt_date: z.preprocess((val) => {
      if (val instanceof Date && !isNaN(val.getTime())) {
        return format(val, "yyyy/MM/dd");
      }
      return val;
    }, z.string().optional()),
  })
  .refine(
    (data) => {
      const orgTypeCode = data.org_type_code ?? "";
      const role = data.user_role ?? "";

      const shouldBeRequired =
        (orgTypeCode === "02" && role === "9") ||
        (orgTypeCode === "03" && (role === "0" || role === "1"));

      if (shouldBeRequired) {
        return (
          data.consent_receipt_date && data.consent_receipt_date.trim() !== ""
        );
      }
      return true;
    },
    {
      message: Messages.validation.required(FieldLabels.consent_receipt_date),
      path: ["consent_receipt_date"],
    }
  );
// 基本情報スキーマ
export const msmgSchema = z.object({
  company_name: z.string().optional(),
  corporate_number: z.string().optional(),
  company_address: z.string().optional(),
  contact_person_list: z.array(contractPersonSchema).optional(),
});
