import { z } from "zod";
import { Messages } from "~/constants/messages/message";

// 共通バリデーションスキーマ
export const commonSchema = {
  // 必須チェック
  nonEmptyString: (field: string) => z.string().nonempty({ message: Messages.validation.required(field) }),

  numericString: (field: string, length?: number) =>
    z
      .string()
      .optional()
      .refine(
        (val) => {
          if (!val) return true;
          if (!/^\d+$/.test(val)) return false;
          if (length && val.length !== length) return false;
          return true;
        },
        {
          message: length ? `${field}は${length}桁の数値で入力してください。` : `${field}は数値で入力してください。`,
        }
      ),
  nonEmptyDate: (field: string) =>
    z.preprocess(
      (val) => {
        if (!val || val === "") return undefined;
        const date = new Date(val as string);
        return isNaN(date.getTime()) ? undefined : date;
      },
      z.date({
        required_error: Messages.validation.required(field),
        invalid_type_error: "データ不正",
      })
    ),

  // 半角数字＋桁数チェック
  numericStringWithLength: (field: string, length?: number) =>
    z
      .string()
      .optional()
      .refine(
        (val) => {
          if (!val) return true; // 空欄OK（nonEmptyStringで必須化）
          if (!/^\d+$/.test(val)) return false; // 半角数字のみ
          if (length && val.length !== length) return false; // 桁数指定
          return true;
        },
        {
          message: length ? `${field}は半角数字${length}桁で入力してください。` : `${field}は半角数字で入力してください。`,
        }
      ),

  // 数値 (int + required)
  requiredInt: (field: string) =>
    z
      .number({
        required_error: Messages.validation.required(field),
        invalid_type_error: `${field}は数値で入力してください。`,
      })
      .int({ message: `${field}は整数で入力してください。` }),

  // 数値（桁数指定）
  intWithDigits: (field: string, digits: number) =>
    z
      .number({
        required_error: Messages.validation.required(field),
        invalid_type_error: `${field}は数値で入力してください。`,
      })
      .int({ message: `${field}は整数で入力してください。` })
      .refine(
        (val) => {
          const length = String(val).length;
          return length === digits;
        },
        { message: `${field}は${digits}桁の数値である必要があります。` }
      ),

  // 文字列（桁数指定）
  stringWithDigits: (field: string, digits: number) =>
    z
      .string()
      .optional()
      .refine((val) => !val || val.length === digits, { message: `${field}は${digits}桁で入力してください。` }),

  // 最小・最大値範囲付き数値
  numberInRange: (field: string, min: number, max: number) =>
    z
      .number({
        required_error: Messages.validation.required(field),
        invalid_type_error: `${field}は数値で入力してください。`,
      })
      .min(min, { message: `${field}は${min}以上である必要があります。` })
      .max(max, { message: `${field}は${max}以下である必要があります。` }),

  dateRange: () => {
    z.object({
      start: z.coerce.date({ required_error: "開始日は必須です。" }),
      end: z.coerce.date({ required_error: "終了日は必須です。" }),
    }).refine((data) => data.start <= data.end, {
      message: "開始日は終了日より前でなければなりません。",
      path: ["end"],
    });
  },

  // 最大値範囲付き文字列
  stringInMaxRange: (field: string, max: number) =>
    z.string().max(max, { message: Messages.validation.maxLength(field, max) }),

  // 改行チェック
  noNewlines: z
    .string()
    .optional()
    .refine((val) => !val || /^[^\n\r]*$/.test(val), { message: "改行を含めずに入力してください。" }),

  // カタカナのみ（全角・半角許容）
  katakanaOnly: z
    .string()
    .regex(
      /^(?=.*[\u30A0-\u30FF\uFF65-\uFF9Fー])[ \u30A0-\u30FF\uFF65-\uFF9Fー\s]+$/,
      "カタカナ（全角・半角）で入力してください。"
    ),

  halfWidthNumber: z.string().regex(/^[0-9]+$/, "半角数字のみで入力してください。"),

  halfWidthAscii: z.string().regex(/^[ -~]+$/, "半角英数記号のみで入力してください。"),

  decimalWithDigits: (intDigits: number, decimalDigits: number) =>
    z
      .string()
      .regex(
        new RegExp(`^\\d{1,${intDigits}}(\\.\\d{1,${decimalDigits}})?$`),
        `${intDigits}桁以内の整数および${decimalDigits}桁以内の小数で入力してください。`
      ),

  monthFormat: (field: string) =>
    z.string().refine((val) => /^\d{1,2}$/.test(val), {
      message: `${field}は1〜2桁の月を入力してください。`,
    }),

  monthRange: (field: string) =>
    z.string().refine(
      (val) => {
        if (!/^\d{1,2}$/.test(val)) return false
        const m = Number(val);
        return m >= 1 && m <= 12;
      },
      {
        message: `${field}は半角数字1〜12で入力してください。`,
      }
    ),

  //空白チェック
  noSpaces: (field: string) =>
    z
      .string()
      .optional()
      .refine((val) => !val || !/[ \t\n\r\f\v\u3000]/.test(val), { message: `${field}に空白が含まれています。` }),
};

// 日付前後チェック（start <= end）
export const dateRangeSchema = (startKey = "start", endKey = "end") =>
  z
    .object({
      [startKey]: z.coerce.date({ required_error: "開始日は必須です。" }),
      [endKey]: z.coerce.date({ required_error: "終了日は必須です。" }),
    })
    .refine((data) => data[startKey] <= data[endKey], {
      message: "開始日は終了日より前でなければなりません。",
      path: [endKey],
    });

// 日付の月が半角数値で1〜2桁
export const monthFormat = (field: string) =>
  z.string().refine((val) => /^\d{1,2}$/.test(val), {
    message: `${field}は1〜2桁の月を入力してください。`,
  });

// 日付の月が1〜12の範囲
export const monthRange = (field: string) =>
  z.string().refine(
    (val) => {
      const m = Number(val);
      return m >= 1 && m <= 12;
    },
    {
      message: `${field}は1〜12で入力してください。`,
    }
  );

// 半角数字のみ
export const halfWidthNumber = z.string().regex(/^[0-9]+$/, "半角数字のみで入力してください。");

// 半角英数字
export const halfWidthAlphaNum = z.string().regex(/^[a-zA-Z0-9]+$/, "半角英数字で入力してください。");

// 半角英大文字
export const upperAlphaOnly = z.string().regex(/^[A-Z]+$/, "半角英大文字のみで入力してください。");

// 半角英数字と記号
export const halfWidthAscii = z.string().regex(/^[ -~]+$/, "半角英数記号のみで入力してください。");
// 整数・小数桁チェック
export const decimalWithDigits = (intDigits: number, decimalDigits: number) =>
  z
    .string()
    .regex(
      new RegExp(`^\\d{1,${intDigits}}(\\.\\d{1,${decimalDigits}})?$`),
      `${intDigits}桁以内の整数および${decimalDigits}桁以内の小数で入力してください。`
    );

// 拡張子チェック（例: .jpg, .png）
export const extensionCheck = (allowedExts: string[]) =>
  z.string().refine(
    (filename) => {
      const ext = filename.split(".").pop()?.toLowerCase();
      return ext ? allowedExts.map((e) => e.toLowerCase()).includes(ext) : false;
    },
    {
      message: `${allowedExts.join(", ")} のいずれかの拡張子が必要です。`,
    }
  );

// 全角ひらがなのみ
export const hiraganaOnly = z.string().regex(/^[\u3040-\u309Fー\s]+$/, "全角ひらがなのみで入力してください。");