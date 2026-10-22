import { ColumnDef } from "@tanstack/react-table";
import { CustomerCompany } from "~/types/screen/master/mscs/mscsType";

import { useNavigate } from "@remix-run/react";

// カスタムソート関数 (日本語)
const japaneseCollator = new Intl.Collator("ja", { numeric: true });

export const customerColumns: ColumnDef<CustomerCompany>[] = [
  {
    accessorKey: "company_name",
    header: "お客さま名",
    enableResizing: true,
    // size: 150,
    // minSize: 100,
    // maxSize: 300,
    cell: ({ row }) => {

      // eslint-disable-next-line react-hooks/rules-of-hooks
      const navigate = useNavigate();
      const customer = row.original;

      // 企業名クリック処理
      const handleCustomerNameClick = (company: CustomerCompany) => {
        navigate(`/master/mscs03`, {
          state: {
            customerData: company,
            mode: "refer"
          }
        });
      };

      return (
        <div
          role="button"
          tabIndex={0}
          onClick={() => handleCustomerNameClick(customer)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              handleCustomerNameClick(customer);
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
    // size: 150,
    // minSize: 100,
    // maxSize: 300,
  },
  {
    accessorKey: "company_address",
    header: "所在地",
    enableResizing: true,
    // size: 150,
    // minSize: 100,
    // maxSize: 300,
    sortingFn: (rowA, rowB, columnId) => {
      const valueA = rowA.getValue<string>(columnId) || "";
      const valueB = rowB.getValue<string>(columnId) || "";
      return japaneseCollator.compare(valueA, valueB);
    },
    // enableSorting: false,
  },
];
