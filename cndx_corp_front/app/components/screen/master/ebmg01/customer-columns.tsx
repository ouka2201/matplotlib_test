import { useNavigate } from "@remix-run/react";
import { ColumnDef } from "@tanstack/react-table";
import { Option } from "~/types/screen/energy-building/ebmg/ebmgType";

interface CustomerCompanyList {
  company_address: string;
  company_name: string;
  company_name_kana: string;
  corporate_number: string;
}

export const customerColumns = (
  prefectureOptions: Option[],
  onClickCustomerName: (company: CustomerCompanyList) => void
): ColumnDef<CustomerCompanyList>[] => [
    {
      accessorKey: "company_name",
      header: "お客さま名",
      enableResizing: true,
      size: 150,
      minSize: 100,
      maxSize: 300,
      cell: ({ row }) => {
        const navigate = useNavigate();
        const customer = row.original;

        return (
          <div
            role="button"
            tabIndex={0}
            onClick={() => onClickCustomerName(customer)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                onClickCustomerName(customer);
              }
            }}
            className="textlink"
          >
            {customer.company_name}
          </div>
        );
      },
    },
    {
      accessorKey: "corporate_number",
      header: "法人番号",
      enableResizing: true,
      size: 150,
      minSize: 100,
      maxSize: 300,
    },
    {
      accessorKey: "company_address",
      header: "本社所在地",
      enableResizing: true,
      size: 150,
      minSize: 100,
      maxSize: 300,
      sortingFn: (rowA, rowB, columnId) => {
        const valueA = rowA.getValue<string>(columnId) || "";
        const valueB = rowB.getValue<string>(columnId) || "";
        return japaneseCollator.compare(valueA, valueB);
      },
      cell: ({ row }) => {
        const code = row.getValue<string>("company_address") ?? "";
        const label = prefectureOptions.find((opt) => opt.id === code)?.name ?? code;
        return <span>{label}</span>;
      },
    },
  ];

const japaneseCollator = new Intl.Collator("ja-JP");
