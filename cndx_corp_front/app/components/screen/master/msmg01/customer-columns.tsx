import { useNavigate } from "@remix-run/react";
import { ColumnDef } from "@tanstack/react-table";

// カスタムソート関数 (日本語)
const japaneseCollator = new Intl.Collator("ja", { numeric: true });

type CustomerCompany = {
  company_name: string;
  corporate_number: string;
  company_address: string;
}

export const customerColumns: ColumnDef<CustomerCompany>[] = [
  {
    accessorKey: "company_name",
    header: "お客さま名",
    enableResizing: true,
    cell: ({ row }) => {

      // eslint-disable-next-line react-hooks/rules-of-hooks
      const navigate = useNavigate();
      const customer = row.original;

      // 企業名クリック処理

      const handleCustomerNameClick = (company: CustomerCompany) => {
        const params = new URLSearchParams({ corporate_number: company.corporate_number });
        navigate(`/master/msmg02?${params.toString()}`, {
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
  },
  {
    accessorKey: "company_address",
    header: "本社所在地",
    enableResizing: true,
    sortingFn: (rowA, rowB, columnId) => {
      const valueA = rowA.getValue<string>(columnId) || "";
      const valueB = rowB.getValue<string>(columnId) || "";
      return japaneseCollator.compare(valueA, valueB);
    },
  },

];
