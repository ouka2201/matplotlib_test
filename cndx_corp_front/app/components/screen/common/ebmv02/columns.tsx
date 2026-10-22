import { ColumnDef, RowData } from "@tanstack/react-table";
import clsx from "clsx";

// カスタムソート関数 (日本語)
const japaneseCollator = new Intl.Collator("ja", { numeric: true });

type CorporateResponseItem = {
  agreement_category: string; // 同意取得経路
  company_name: string; //お客さま名
  corporate_number: string; //法人番号
  company_address_prefecture: string; //企業所在地(都道府県)
  company_address_city: string; //企業所在地(市区町村)
  building_id: string; //建物ID
  building_name: string; //建物・事業所名
  building_address_prefecture: string; //建物所在地(都道府県)
  building_address_city: string; //建物所在地(市区町村)
  ep_office_code: string; //事業所コード
  ep_customer_number: string; //EPお客さま番号
  supply_point_number: string; //供給地点特定番号
};

type CustomColumnDef<T> = ColumnDef<T> & {
  label?: string;
  id: string;
  centerHeader?: boolean;
  accessorKey?: string;
  accessorFn?: (row: T) => any;
};

type GroupedColumn<T> = {
  header: string;
  columns: Array<CustomColumnDef<T>>; // ColumnDef 型をそのまま使用
};

declare module "@tanstack/table-core" {
  // 型パラメータを一致させ、RowData を使うように修正
  interface ColumnMeta<TData extends RowData, TValue> {
    className?: string;
  }
}

export function hasAccessorKey<T>(
  col: ColumnDef<T>
): col is ColumnDef<T> & { accessorKey: string } {
  return "accessorKey" in col && typeof col.accessorKey === "string";
}

function resolveHeaders<T>(
  groups: GroupedColumn<T>[]
): ColumnDef<T, unknown>[] {
  return groups.map((group, index) => ({
    id: `group-${index}`,
    header: group.header
      ? () => <span className="text-left w-full block">{group.header}</span>
      : undefined,
    columns: group.columns.map((col) => {
      const accessorKey =
        "accessorKey" in col && typeof col.accessorKey === "string"
          ? col.accessorKey
          : undefined;
      const accessorFn = "accessorFn" in col ? col.accessorFn : undefined;
      const id = col.id ?? accessorKey ?? crypto.randomUUID();

      return {
        ...col,
        id,
        accessorKey,
        accessorFn,
        header:
          typeof col.header === "string" || typeof col.header === "function"
            ? col.header
            : () => (
              <div
                role="button"
                tabIndex={0}
                className={clsx(
                  "flex items-center w-full",
                  col.meta?.className,
                  col.centerHeader ? "justify-center" : "" // `centerHeader`がtrueならjustify-centerを適用
                )}
              >
                <span className="inline-block">{col.label ?? id}</span>
              </div>
            ),
        meta: {
          ...(col.meta ?? {}),
          className: clsx("text-center", col.meta?.className ?? ""),
        },
      } as ColumnDef<T, unknown>;
    }),
  })) as ColumnDef<T, unknown>[];
}

const groupedColumns: GroupedColumn<CorporateResponseItem>[] = [
  {
    header: "",
    columns: [
      {
        label: "選択",
        accessorKey: "select",
        id: "select",
        header: "選択",
        size: 70,
      },
    ],
  },
  {
    header: "お客さま基本情報",
    columns: [
      {
        label: "お客さま名",
        accessorKey: "company_name",
        id: "company_name",
        header: () => <div className="text-left w-full">お客さま名</div>,
      },
      {
        label: "法人番号",
        accessorKey: "corporate_number",
        id: "corporate_number",
        header: () => <div className="text-left w-full">法人番号</div>,
      },
      {
        label: "本社所在地",
        accessorKey: "company_address",
        id: "company_address",
        header: () => <div className="text-left w-full">本社所在地</div>,
        accessorFn: (row) =>
          `${row.company_address_prefecture ?? ""}${row.company_address_city ?? ""
          }`,
        sortingFn: (rowA, rowB) => {
          const valueA = `${rowA.original.company_address_prefecture ?? ""}${rowA.original.company_address_city ?? ""
            }`;
          const valueB = `${rowB.original.company_address_prefecture ?? ""}${rowB.original.company_address_city ?? ""
            }`;
          return japaneseCollator.compare(valueA, valueB);
        },
      },
    ],
  },
  {
    header: "拠点情報",
    columns: [
      {
        label: "拠点名",
        accessorKey: "building_name",
        id: "building_name",
        header: () => <div className="text-left w-full">拠点名</div>,
      },
      {
        label: "拠点所在地",
        accessorKey: "building_address",
        id: "building_address",
        header: () => <div className="text-left w-full">拠点所在地</div>,
        accessorFn: (row) =>
          `${row.building_address_prefecture ?? ""}${row.building_address_city ?? ""
          }`,
        sortingFn: (rowA, rowB) => {
          const valueA = `${rowA.original.building_address_prefecture ?? ""}${rowA.original.building_address_city ?? ""
            }`;
          const valueB = `${rowB.original.building_address_prefecture ?? ""}${rowB.original.building_address_city ?? ""
            }`;
          return japaneseCollator.compare(valueA, valueB);
        },
      },
      {
        label: "事業所コード",
        accessorKey: "ep_office_code",
        id: "ep_office_code",
        header: () => <div className="text-left w-full">事業所コード</div>,
      },
      {
        label: "EPお客さま番号",
        accessorKey: "ep_customer_number",
        id: "ep_customer_number",
        header: () => <div className="text-left w-full">お客さま番号</div>,
      },
      {
        label: "供給地点特定番号",
        accessorKey: "supply_point_number",
        id: "supply_point_number",
        header: () => (
          <div className="text-left w-full">供給地点特定番号</div>
        ),
      },
    ],
  },
  {
    header: "同意書取得経路情報",
    columns: [
      {
        label: "同意書取得経路",
        accessorKey: "agreement_category",
        id: "agreement_category",
        header: () => <div className="text-left w-full">同意書取得経路</div>,
        size: 120,
      },
    ],
  },
];
export const columns: ColumnDef<CorporateResponseItem>[] =
  resolveHeaders(groupedColumns);
