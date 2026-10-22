import { Electric } from "~/types/screen/energy-building/ebmg03";
import { ColumnDef } from "@tanstack/react-table";

import { useNavigate } from "@remix-run/react";
import { Row } from "react-day-picker";

export const electricColumns: ColumnDef<Electric>[] = [
  {
    id: "No",
    header: "No",
    size: 5,
    cell: ({ row }) => row.index + 1,
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "electric_company_reg_no",
    header: "電気事業者コード",
    enableResizing: true,
    cell: ({ row }) => {
      return <div className="">{row.original.electric_company_reg_no}</div>;
    },
    enableSorting: false,
    enableHiding: false,
  },
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
      const handleCustomerNameClick = (company: Electric) => {
        navigate(`/master/mscs03`, {
          state: { customerData: company, mode: "refer" },
        });
      };

      return (
        <div
          role="button"
          tabIndex={0}
          onClick={() => handleCustomerNameClick(customer)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              handleCustomerNameClick(customer);
            }
          }}
          className="text-blue-500 hover:underline cursor-pointer"
        >
          {customer.electric_supplier_nm}
        </div>
      );
    },
  },
  {
    accessorKey: "menu_code",
    header: "電気事業者_メニューコード",
    enableResizing: true,
    cell: ({ row }) => row.original.menu_no,
  },
  {
    accessorKey: "menu_name",
    header: "電気事業者_メニュー名",
    enableResizing: true,
    cell: ({ row }) => <p>{row.original.menu_nm}</p>,
  },
];
