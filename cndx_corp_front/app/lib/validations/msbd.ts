import * as z from "zod";
import { Messages } from "~/constants/messages/message";
import { commonSchema } from "./validationBase"; // 共通メッセージ

export const FieldLabels = {
  locationIdentifierName: "拠点名",
  buildingAddressPrefecture: "本社所在地（都道府県）",
  buildingAddressCity: "本社所在地（市区町村以降）",
  grossFloorArea: "延床面積",
  industryClassDetailCode: "細分類番号",
  industryClassDetailName: "細分類",
  benchmarkDenom: "原単位分母",
  benchmarkVal: "原単位分母数値",
};

export const msbdSchema = z.object({
    org_id: z.string().optional(),
    corporate_number: z.string().optional(),
    agreement_category: z.string().optional(),
    building_id: z.string(),
    location_identifier_name: commonSchema
      .nonEmptyString(FieldLabels.locationIdentifierName)
      .and(commonSchema.stringInMaxRange(FieldLabels.locationIdentifierName, 50)),

    building_address_prefecture: commonSchema
      .nonEmptyString(FieldLabels.buildingAddressPrefecture),

    building_address_city: commonSchema
      .nonEmptyString(FieldLabels.buildingAddressCity)
      .and(commonSchema.stringInMaxRange(FieldLabels.buildingAddressCity, 100)),

    gross_floor_area: z
      .string()
      .trim()
      .optional()
      .refine(
        (val) => {
          if (!val) return true;
          return /^\d{1,6}(\.\d{1,2})?$/.test(val);
        },
        {
          message: `${FieldLabels.grossFloorArea}は整数6桁以内、小数2桁以内で入力してください。`,
        }
      ),

    industry_class_detail_code: z
    .string()
    .trim()
    // 半角数字のみチェック（該当しない場合は共通メッセージ）
    .regex(/^\d*$/, { message: Messages.validation.invalidField() })
    // 桁数チェック：4桁でない場合
    .refine((val) => !val || val.length === 4, {
    message: `${FieldLabels.industryClassDetailCode}は4桁で入力してください。`,
    }),

    industry_class_detail_name: commonSchema
      .stringInMaxRange(FieldLabels.industryClassDetailName, 50),

    benchmark_denom: commonSchema
      .stringInMaxRange(FieldLabels.benchmarkDenom, 50),

    benchmark_val: z
      .string()
      .trim()
      .refine(
        (val) => {
          if (!val) return true; // ← 空欄はOK
          return /^\d{1,7}(\.\d{1,3})?$/.test(val); // ← 数値形式チェック
        },
        {
          message: `${FieldLabels.benchmarkVal}は整数7桁以内、小数3桁以内で入力してください。`,
        }
    ),

    group1: z.string().optional(),
    group2: z.string().optional(),
    group3: z.string().optional(),
    group4: z.string().optional(),
    group5: z.string().optional(),
});
