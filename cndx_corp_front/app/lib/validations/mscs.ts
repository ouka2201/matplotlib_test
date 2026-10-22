import * as z from "zod";
import { Messages } from "~/constants/messages/message";
import { commonSchema } from "./validationBase";

// フィールドラベル (共通化)
export const FieldLabels = {
  company_name: "お客さま名",
  company_name_kana: "お客さま名（フリガナ）",
  corporate_number: "法人番号",
  company_address_prefecture: "本社所在地（都道府県）",
  company_address_city: "本社所在地（市区町村以降）",
  company_address: "所在地",
  agreement_category: "同意書取得経路",
  agreement_org: "同意書取得組織",
  // building_name: "拠点名",
  location_identifier_name: "拠点名",
  building_address_prefecture: "拠点所在地（都道府県）",
  building_address_city: "拠点所在地（市区町村以降）",
  building_address: "所在地",
  ep_office_code: "事業所コード",
  ep_customer_number: "お客さま番号",
  supply_point_number: "供給地点特定番号",
};

export const nonEmptyDate = (field: string) =>
  z.preprocess(
    (val) => {
      if (!val || val === "") return undefined;
      const date = new Date(val as string);
      return isNaN(date.getTime()) ? undefined : date;
    },
    z.date({
      required_error: Messages.validation.required(field),
      invalid_type_error: "データ不正",
    }),
  );

// 建物情報スキーマ
export const buildingSchema = z.object({
  agreement_category: commonSchema.nonEmptyString(FieldLabels.agreement_category),
  agreement_org: commonSchema.nonEmptyString(FieldLabels.agreement_org),
  location_identifier_name: commonSchema
    .nonEmptyString(FieldLabels.location_identifier_name)
    .and(commonSchema.stringInMaxRange(FieldLabels.location_identifier_name, 100)),
  building_address_prefecture: commonSchema.nonEmptyString(FieldLabels.building_address_prefecture),
  building_address_city: commonSchema
    .nonEmptyString(FieldLabels.building_address_city)
    .and(commonSchema.stringInMaxRange(FieldLabels.building_address_city, 100))
    .and(commonSchema.noNewlines),
  ep_office_code: z.preprocess(
    (v) => (v === null || v === "" ? undefined : v),
    z
      .string()
      .optional()
      .and(commonSchema.noSpaces(FieldLabels.ep_office_code))
      .and(commonSchema.numericStringWithLength(FieldLabels.ep_office_code, 3))
      .and(commonSchema.noNewlines),
  ),
  ep_customer_number: z.preprocess(
    (v) => (v === null || v === "" ? undefined : v),
    z
      .string()
      .optional()
      .and(commonSchema.noSpaces(FieldLabels.ep_customer_number))
      .and(commonSchema.numericStringWithLength(FieldLabels.ep_customer_number, 13))
      .and(commonSchema.noNewlines),
  ),
  supply_point_number: z.preprocess(
    (v) => (v === null || v === "" ? undefined : v),
    z
      .string()
      .optional()
    .and(commonSchema.noSpaces(FieldLabels.supply_point_number))
    .and(commonSchema.numericStringWithLength(FieldLabels.supply_point_number, 22))
    .and(commonSchema.noNewlines),
  ),
  org_name: z.string().nullable().optional(),
  building_id: z.string().optional(),
  agreement_org_id: z.string().optional(),
  isFromApi: z.boolean().optional(),
});

// 企業情報スキーマ
export const mscsSchema = z.object({
  company_name: commonSchema
    .nonEmptyString(FieldLabels.company_name)
    .and(commonSchema.stringInMaxRange(FieldLabels.company_name, 100))
    .and(commonSchema.noNewlines),
  company_name_kana: commonSchema
    .nonEmptyString(FieldLabels.company_name_kana)
    .and(commonSchema.katakanaOnly)
    .and(commonSchema.stringInMaxRange(FieldLabels.company_name_kana, 100))
    .and(commonSchema.noNewlines),
  corporate_number: commonSchema
    .nonEmptyString(FieldLabels.corporate_number)
    .and(commonSchema.numericStringWithLength(FieldLabels.corporate_number, 13))
    .and(commonSchema.noNewlines),
  company_address_prefecture: commonSchema.nonEmptyString(FieldLabels.company_address_prefecture),
  company_address_city: commonSchema
    .nonEmptyString(FieldLabels.company_address_city)
    .and(commonSchema.stringInMaxRange(FieldLabels.company_address_city, 100))
    .and(commonSchema.noNewlines),
  company_address: z.string().optional(),
  office_info_list: z.array(buildingSchema).optional(),
});
