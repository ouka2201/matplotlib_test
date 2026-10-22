import * as z from "zod";
import { commonSchema } from "./validationBase";

export const FieldLabels = {
  startYear: "開始年",
  startMonth: "開始月",
  endYear: "終了年",
  endMonth: "終了月",
  reportType: "フォーマット選択",
  agreementCategory: "同意書取得経路",
  orgId: "登録組織名",
  major: "産業分類（大分類）",
  middle: "産業分類（中分類）",
  minor: "産業分類（小分類）",
  detail: "産業分類（細分類）",
};

export const baseSchema = z
  .object({
    startYear: commonSchema
      .nonEmptyString(FieldLabels.startYear)
      .and(commonSchema.numericStringWithLength(FieldLabels.startYear, 4)),
    startMonth: commonSchema
      .nonEmptyString(FieldLabels.startMonth)
      .and(commonSchema.monthRange(FieldLabels.startMonth)),
    endYear: commonSchema
      .nonEmptyString(FieldLabels.endYear)
      .and(commonSchema.numericStringWithLength(FieldLabels.endYear, 4)),
    endMonth: commonSchema
      .nonEmptyString(FieldLabels.endMonth)
      .and(commonSchema.monthRange(FieldLabels.endMonth)),
  })

  // 年月の形式・範囲チェック（半角が保証された後にチェック）
  .refine(
    (data) => {
      const y = Number(data.startYear);
      const m = Number(data.startMonth);
      const today = new Date();
      const currentYear = today.getFullYear();
      const currentMonth = today.getMonth() + 1;
      return y < currentYear || (y === currentYear && m < currentMonth);
    },
    {
      path: ["startMonth"],
      message: "未来の年月は登録できません。",
    }
  );

// レポート作成スキーマ
export const ebrcReportCreateSchema = z.object({
  startYear: commonSchema.nonEmptyString(FieldLabels.startYear),
  startMonth: commonSchema.nonEmptyString(FieldLabels.startMonth),
  reportType: commonSchema.nonEmptyString(FieldLabels.reportType),
  agreementCategory: commonSchema.nonEmptyString(FieldLabels.agreementCategory),
  orgId: commonSchema.nonEmptyString(FieldLabels.orgId),
});

export type EbrcReportCreateInput = z.infer<typeof ebrcReportCreateSchema>;

export const industrySchema = z.object({
  major: commonSchema.nonEmptyString(FieldLabels.major),
  middle: commonSchema.nonEmptyString(FieldLabels.middle),
  minor: commonSchema.nonEmptyString(FieldLabels.minor),
  detail: commonSchema.nonEmptyString(FieldLabels.detail),
});

export type IndustryInput = z.infer<typeof industrySchema>;
