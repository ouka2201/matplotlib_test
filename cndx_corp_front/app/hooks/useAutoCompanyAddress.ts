import { Path, UseFormReturn } from "react-hook-form";
import { CdNmOption } from "~/types/screen/master/mscs/mscsType";

/**
 * 会社住所を生成するユーティリティ関数
 * @param form react-hook-formのインスタンス
 * @param prefectureList 都道府県リスト
 * @param prefectureField 都道府県コードのフィールド名
 * @param cityField 市区町村のフィールド名
 * @param addressField 結合後の住所フィールド名
 */
export function generateCompanyAddress<T>(
  form: UseFormReturn<T>,
  prefectureList: CdNmOption[] | undefined,
  prefectureField: keyof T = "company_address_prefecture" as any,
  cityField: keyof T = "company_address_city" as any,
  addressField: keyof T = "company_address" as any
) {
  const prefectureCode = form.getValues(prefectureField as unknown as Path<T>);
  const city = form.getValues(cityField as unknown as Path<T>) ?? "";

  const prefectureName = prefectureList?.find((p) => p.id === prefectureCode)?.name ?? "";

  form.setValue(addressField as unknown as Path<T>, `${prefectureName}${city}`, { shouldValidate: false });
}
