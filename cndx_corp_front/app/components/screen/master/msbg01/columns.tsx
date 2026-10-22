import { BuildingGroup } from "~/types/screen/master/mscs/msbgType";
import { ColumnDef } from "@tanstack/react-table";

export const columns: ColumnDef<BuildingGroup>[] = [
  {
    id: "No",
    header: "グループ",
    meta: {
      className: "w-20",
    },
  },
  {
    accessorKey: "group_name",
    header: "グループ名",
    meta: {
      className: "w-48",
    },
  },
  {
    accessorKey: "select_item1",
    header: "選択肢1",
    meta: {
      className: "w-48",
    },
  },
  {
    accessorKey: "select_item2",
    header: "選択肢2",
    meta: {
      className: "w-48",
    },
  },
  {
    accessorKey: "select_item3",
    header: "選択肢3",
    meta: {
      className: "w-48",
    },
  },
  {
    accessorKey: "select_item4",
    header: "選択肢4",
    meta: {
      className: "w-48",
    },
  },
  {
    accessorKey: "select_item5",
    header: "選択肢5",
    meta: {
      className: "w-48",
    },
  },
  {
    accessorKey: "select_item6",
    header: "選択肢6",
    meta: {
      className: "w-48",
    },
  },
  {
    accessorKey: "select_item7",
    header: "選択肢7",
    meta: {
      className: "w-48",
    },
  },
];
