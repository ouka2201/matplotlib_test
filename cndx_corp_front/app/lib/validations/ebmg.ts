import * as z from "zod";
import { Messages } from "~/constants/messages/message";
import { commonSchema, decimalWithDigits } from "./validationBase";

// フィールドラベル (共通化)
export const FieldLabels = {
  industry_class_minor_code: "産業分類（小分類）",
  industry_class_detail_code: "産業分類（細分類）",
  gross_floor_area: "延床面積",
  electricity_supplier_no: "契約先電気事業者",
  energy_quantity: "エネルギー使用量",
};

const decimalWithDigits = (field: string, intDigits: number, decimalDigits: number, required: boolean = true) =>
  z.preprocess(
    (val) => {
      if (val === "") return undefined;
      if (typeof val === "number") return val.toString();
      return val;
    },
    (() => {
      const core = z
        .string({
          ...(required ? { required_error: Messages.validation.required(field) } : {}),
        })
        .and(commonSchema.decimalWithDigits(intDigits, decimalDigits));
      return required ? core : core.optional();
    })()
  );

const energyQuantitySchema = z.array(decimalWithDigits("エネルギー使用量", 15, 10, false));

const energyInfoSchema = z.object({
  energy_code: z.string(),
  energy_quantity: energyQuantitySchema,
});

export const makeBuildingSchema = (mode: "full" | "nonRequired") =>
  z
    .object({
      industry_class_minor_code:
        mode === "full" ? commonSchema.nonEmptyString(FieldLabels.industry_class_minor_code) : z.string().optional(),
      industry_class_detail_code:
        mode === "full" ? commonSchema.nonEmptyString(FieldLabels.industry_class_detail_code) : z.string().optional(),
      gross_floor_area: decimalWithDigits(FieldLabels.gross_floor_area, 6, 2, mode === "full"),
      electricity_supplier_no:
        mode === "full" ? commonSchema.nonEmptyString(FieldLabels.electricity_supplier_no) : z.string().optional(),
      energy_info: z.array(energyInfoSchema),
    })
    .superRefine((data, ctx) => {
      if (mode === "full") {
        // 電気使用量の必須チェックは full のときだけ
        data.energy_info.forEach((info, index) => {
          if (info.energy_code === "0200010011") {
            const hasAny = info.energy_quantity.some((val) => val !== undefined && val !== null && val !== "");
            if (!hasAny) {
              ctx.addIssue({
                path: ["energy_info", index, "energy_quantity"],
                code: z.ZodIssueCode.custom,
                message: "電気の使用量を1つ以上入力してください。",
              });
            }
          }
        });
      }
    });
