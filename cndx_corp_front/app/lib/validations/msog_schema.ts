import * as z from "zod";
import { Messages } from "~/constants/messages/message";
import { commonSchema } from "./validationBase";

export const FieldLabels = {
  orgType: "組織種別",
  organizationId: "組織ID",
  organizationName: "組織名",
  companyName: "企業名",
  companyCode: "企業コード",
  bankCode: "銀行コード",
  branchName: "支店名",
  branchCode: "支店コード",
};

export const msogSchema = z
  .object({
    org_type: z.string().optional(),
    org_type_code: commonSchema.nonEmptyString(FieldLabels.orgType),
    org_id: z.string().optional(),
    org_name: z.string().optional(),
    company_name: commonSchema
      .nonEmptyString(FieldLabels.companyName)
      .max(100, { message: Messages.validation.maxLength(FieldLabels.companyName, 100) }),
    company_code: z.string().optional(),
    bank_code: z.string().optional(),
    branch_name: commonSchema.stringInMaxRange(FieldLabels.branchName, 100)
      .optional(),
    branch_code: z.string().optional(),
    business_type: z.string().optional(),
  })
  .superRefine((values, ctx) => {
    const isBank = values.org_type_code === "02" || values.org_type_code === "03";

    if (isBank) {
      if (!values.bank_code || values.bank_code.trim() === "") {
        ctx.addIssue({
          path: ["bank_code"],
          code: z.ZodIssueCode.custom,
          message: Messages.validation.required(FieldLabels.bankCode),
        });
      } else if (!/^\d{4}$/.test(values.bank_code)) {
        ctx.addIssue({
          path: ["bank_code"],
          code: z.ZodIssueCode.custom,
          message: `${FieldLabels.bankCode}は半角数字4桁で入力してください。`,
        });
      }

      if (!values.branch_code || values.branch_code.trim() === "") {
        ctx.addIssue({
          path: ["branch_code"],
          code: z.ZodIssueCode.custom,
          message: Messages.validation.required(FieldLabels.branchCode),
        });
      } else if (!/^\d{3}$/.test(values.branch_code)) {
        ctx.addIssue({
          path: ["branch_code"],
          code: z.ZodIssueCode.custom,
          message: `${FieldLabels.branchCode}は半角数字3桁で入力してください。`,
        });
      }

      if (!values.branch_name || values.branch_name.trim() === "") {
        ctx.addIssue({
          path: ["branch_name"],
          code: z.ZodIssueCode.custom,
          message: Messages.validation.required(FieldLabels.branchName),
        });
      }
    } else {
      if (!values.company_code || values.company_code.trim() === "") {
        ctx.addIssue({
          path: ["company_code"],
          code: z.ZodIssueCode.custom,
          message: Messages.validation.required(FieldLabels.companyCode),
        });
      } else if (!/^[A-Z]{3}$/.test(values.company_code)) {
        ctx.addIssue({
          path: ["company_code"],
          code: z.ZodIssueCode.custom,
          message: `${FieldLabels.companyCode}は半角英字・大文字・3文字で入力してください。`,
        });
      }}
  });
