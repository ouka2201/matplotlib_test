import * as z from "zod";
import { Messages } from "~/constants/messages/message";
import { Encoding } from "~/types/screen/master/msbg/msbgType";
import { containsGaiji } from "../utils";

export const commonSchema = {
  optionalString: () => z.string().optional(),
};

const baseBuildingGroupSchema = () =>
  z.object({
    group_name: z.string().optional(),
    select_item1: z.string().optional(),
    select_item2: z.string().optional(),
    select_item3: z.string().optional(),
    select_item4: z.string().optional(),
    select_item5: z.string().optional(),
    select_item6: z.string().optional(),
    select_item7: z.string().optional(),
  });

export const createBuildingGroupSchema = () =>
  baseBuildingGroupSchema().superRefine((data, ctx) => {
    const {
      group_name,
      select_item1,
      select_item2,
      select_item3,
      select_item4,
      select_item5,
      select_item6,
      select_item7,
    } = data;

    const hasGroupName = !!group_name?.trim();
    const hasAnySelectItem = [
      select_item1,
      select_item2,
      select_item3,
      select_item4,
      select_item5,
      select_item6,
      select_item7,
    ].some((item) => item?.trim());

    if (hasGroupName && !hasAnySelectItem) {
      const no = "不明";

      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `グループ${no}の選択肢が未設定です。`,
        path: ["group_name"],
      });
    }
  });

export const createBuildingGroupListSchema = (encoding?: Encoding) =>
  z.array(baseBuildingGroupSchema().extend({ group_id: z.string() })).superRefine((groups, ctx) => {
    const nameMap = new Map<string, number[]>();

    groups.forEach((group, index) => {
      const rawName = group.group_name ?? "";
      const name = rawName.trim();

      // 空文字・空白のみの名前は重複チェックしない
      if (name.length === 0) {
        return;
      }

      if (!nameMap.has(name)) {
        nameMap.set(name, []);
      }
      nameMap.get(name)!.push(index);
    });

    for (const [name, indices] of nameMap.entries()) {
      if (indices.length > 1) {
        const groupNos = indices.map((i) => groups[i].group_id.match(/\d+$/)?.[0] ?? `${i + 1}`);
        const firstIndex = indices[0];

        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `グループ${groupNos.join("とグループ")}のグループ名称が重複しています。`,
          path: [firstIndex, "group_name"],
        });
      }
    }

    groups.forEach((group, index) => {
      const hasGroupName = !!group.group_name?.trim();
      const hasAnySelectItem = [
        group.select_item1,
        group.select_item2,
        group.select_item3,
        group.select_item4,
        group.select_item5,
        group.select_item6,
        group.select_item7,
      ].some((item) => item?.trim());

      if (hasGroupName && !hasAnySelectItem) {
        const no = group.group_id.match(/\d+$/)?.[0] ?? `${index + 1}`;
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `グループ${no}の選択肢が未設定です。`,
          path: [index, "group_name"],
        });
      }

      const selectItems = [
        { key: "select_item1", label: "選択肢1", value: group.select_item1?.trim() ?? "" },
        { key: "select_item2", label: "選択肢2", value: group.select_item2?.trim() ?? "" },
        { key: "select_item3", label: "選択肢3", value: group.select_item3?.trim() ?? "" },
        { key: "select_item4", label: "選択肢4", value: group.select_item4?.trim() ?? "" },
        { key: "select_item5", label: "選択肢5", value: group.select_item5?.trim() ?? "" },
        { key: "select_item6", label: "選択肢6", value: group.select_item6?.trim() ?? "" },
        { key: "select_item7", label: "選択肢7", value: group.select_item7?.trim() ?? "" },
      ].filter((item) => item.value !== "");

      for (let i = 0; i < selectItems.length; i++) {
        for (let j = i + 1; j < selectItems.length; j++) {
          if (selectItems[i].value === selectItems[j].value) {
            const no = group.group_id.match(/\d+$/)?.[0] ?? `${index + 1}`;
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: `グループ${no}の${selectItems[i].label}と${selectItems[j].label}の名称が重複しています。`,
              path: [index, selectItems[j].key],
            });
          }
        }
      }

      const fieldsToCheck = [
        { key: "group_name", max: 20, label: "グループ名" },
        { key: "select_item1", max: 30, label: "選択肢1" },
        { key: "select_item2", max: 30, label: "選択肢2" },
        { key: "select_item3", max: 30, label: "選択肢3" },
        { key: "select_item4", max: 30, label: "選択肢4" },
        { key: "select_item5", max: 30, label: "選択肢5" },
        { key: "select_item6", max: 30, label: "選択肢6" },
        { key: "select_item7", max: 30, label: "選択肢7" },
      ] as const;

      for (const { key, max, label } of fieldsToCheck) {
        const val = group[key];
        if (val) {
          if (val.length > max) {
            const no = group.group_id.slice(-1);
            ctx.addIssue({
              code: z.ZodIssueCode.too_big,
              maximum: max,
              type: "string",
              inclusive: true,
              message: `グループ${no}の${label}は${max}文字以内で入力してください。`,
              path: [index, key],
            });
          }

          if (encoding && containsGaiji(val)) {
            const no = group.group_id.slice(-1);
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: `グループ${no}の${label}に機種依存文字が含まれています。`,
              path: [index, key],
            });
          }
        }
      }
    });
  });
