import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import {MCode} from "~/types/screen/master/mscs/mscsType"
// タグクラスマージ用
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// 丸付き数字の変換
export const getCircledNumber = (num: number): string => {
  if (num < 1 || num > 20) return String(num);
  return String.fromCharCode(0x245f + num);
};


// 共通のマッピング関数
export const mapToIdName = (items: MCode[]) =>
  items.map(({ code, jp_code_name }) => ({ id: code, name: jp_code_name }));


// APIから取得したデータを深くパースする関数
// 文字列が JSON 形式であれば、JSON.parse を繰り返す
export const deepParse = (raw: unknown) => {
  let v = raw;
  // 文字列が JSON 形式であれば、JSON.parse を繰り返す
  // ただし、無限ループを避けるために、文字列でない場合は break
  while (typeof v === 'string') {
    try {
      v = JSON.parse(v);
    } catch {
      break;
    }
  }
  return v;
}
// 外字チェック（環境依存文字）
export const containsGaiji = (text: string): boolean => {
  const forbiddenRegex = /[\uE000-\uF8FF]/;
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    if (0xd800 <= code && code <= 0xdbff) {
      const next = text.charCodeAt(i + 1);
      if (!(0xdc00 <= next && next <= 0xdfff)) {
        return true;
      }
    }
    if (0xdc00 <= code && code <= 0xdfff) {
      const prev = text.charCodeAt(i - 1);
      if (!(0xd800 <= prev && prev <= 0xdbff)) {
        return true;
      }
    }
  }
  return forbiddenRegex.test(text);
};

//登録ボタンの処理
export const isErrorWithStatus = (error: unknown): error is { status: number; error_message_list?: string } => {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    typeof (error as { status: number }).status === "number"
  );
}