import { DoubleArrowLeftIcon, DoubleArrowRightIcon, TriangleDownIcon, TriangleUpIcon } from "@radix-ui/react-icons";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  PaginationState,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { useState } from "react";

import { Button } from "~/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { Messages } from "~/constants/messages/message";

export function parseSortQueryParam(query: string | undefined) {
  if (!query) {
    return [];
  }
  const decoded = decodeURIComponent(query);
  const [field, order] = decoded.split(":");

  const isDesc = order === "desc";
  return [{ id: field, desc: isDesc }];
}

export interface PageableTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  pageSizeOptions?: number[];
  initialPageSize?: number;
  initailSort?: SortingState;
  pageCount: number;
  totalCount: number;
  renderRow?: (item: TData, index: number) => React.ReactNode;
  onPageChange?: () => void;
  rowKeyResolver?: (row: TData, index: number) => string | number;
}

export function PageableTable<TData, TValue>({
  columns,
  data,
  totalCount,
  initialPageSize,
  initailSort = [],
  pageCount,
  pageSizeOptions = [5, 10, 20, 50],
  renderRow,
  onPageChange,
  rowKeyResolver,
}: PageableTableProps<TData, TValue>) {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: initialPageSize ?? 50,
  });

  const [sorting, setSorting] = useState<SortingState>(initailSort);

  const table = useReactTable({
    data,
    columns,
    pageCount,
    getCoreRowModel: getCoreRowModel(),
    columnResizeMode: "onChange",
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: {
      pagination,
      sorting,
    },
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    getPaginationRowModel: getPaginationRowModel(),
    manualFiltering: false,
    manualSorting: false,
  });

  const startRow = Math.min(totalCount, pagination.pageIndex * pagination.pageSize + 1);
  const endRow = Math.min(totalCount, (pagination.pageIndex + 1) * pagination.pageSize);

  const totalPages = Math.max(1, Math.ceil(totalCount / pagination.pageSize));

  return (
    <>
      <div className="h-auto w-full overflow-auto rounded-md border">
        <Table className="w-full border-collapse border-none [&_th]:border-none [&_td]:border-none [&_tr]:border-none" wrapperClassName="max-h-[calc(50vh-50px)]">
          <TableHeader className="sticky top-0 z-[200] bg-[#F2F4F7]">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead
                      key={header.id}
                      style={{ width: header.getSize() }}
                      className="text-black P-0 whitespace-nowrap"
                      colSpan={header.colSpan}
                      // colSpan={table.getAllLeafColumns().length}
                    >
                      <div
                        role="button"
                        tabIndex={0}
                        onClick={header.column.getToggleSortingHandler()}
                        onKeyDown={header.column.getToggleSortingHandler()}
                        className="flex items-center justify-normal bg-[#F2F4F7]"
                      >
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                        {{
                          asc: <TriangleUpIcon />,
                          desc: <TriangleDownIcon />,
                        }[header.column.getIsSorted() as string] ?? null}
                      </div>
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody className="bg-white">
            {table.getRowModel().rows?.length ? (
              renderRow ? (
                table.getRowModel().rows.map((row, index) => renderRow(row.original, index))
              ) : (
                table.getRowModel().rows.map((row, index) => (
                  <TableRow key={rowKeyResolver ? rowKeyResolver(row.original, index) : row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                    ))}
                  </TableRow>
                ))
              )
            ) : (
              <TableRow>
                <TableCell colSpan={table.getAllLeafColumns().length} className="h-24 text-center px-4 py-2">
                  {Messages.SEARCH_NONE}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {totalCount > 0 && (
        <div className="flex flex-col items-center justify-end gap-2 space-x-2 py-4 sm:flex-row">
          <div className="flex w-full items-center justify-between">
            <div className="flex-1 text-sm text-muted-foreground font-medium">
              {/* {totalCount} 件中 {endRow}件 */}
              {totalCount} 件中 {startRow}–{endRow} 件
            </div>
            <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-6 lg:gap-8">
              <div className="flex items-center space-x-2">
                <p className="whitespace-nowrap text-sm font-medium">1ページの行数:</p>
                <Select
                  value={`${pagination.pageSize}`}
                  onValueChange={(value) => {
                    setPagination({
                      pageIndex: 0, // 1ページ目に戻す
                      pageSize: Number(value),
                    });
                    onPageChange?.();
                  }}
                >
                  <SelectTrigger className="h-8 w-[70px]">
                    <SelectValue placeholder={pagination.pageSize} />
                  </SelectTrigger>
                  <SelectContent side="top">
                    {pageSizeOptions.map((pageSize) => (
                      <SelectItem key={pageSize} value={`${pageSize}`}>
                        {pageSize}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <div className="flex w-full items-center justify-between gap-2 sm:justify-end">
            <div className="flex w-[100px] items-center justify-center text-sm font-medium">
              {pagination.pageIndex + 1} / {totalPages} ページ
            </div>
            <div className="flex items-center space-x-2">
              {/* 最初のページボタン */}
              <Button
                aria-label="Go to first page"
                variant="outline"
                className="hidden h-8 w-8 p-0 lg:flex"
                onClick={() => {
                  setPagination((prev) => ({ ...prev, pageIndex: 0 }));
                  onPageChange?.();
                }}
                disabled={pagination.pageIndex === 0}
              >
                <DoubleArrowLeftIcon className="h-4 w-4" aria-hidden="true" />
              </Button>

              {/* 前のページボタン */}
              <Button
                aria-label="Go to previous page"
                variant="outline"
                className="h-8 w-8 p-0"
                onClick={() => {
                  setPagination((prev) => ({
                    ...prev,
                    pageIndex: Math.max(0, prev.pageIndex - 1),
                  }));
                  onPageChange?.();
                }}
                disabled={pagination.pageIndex === 0}
              >
                <ChevronLeftIcon className="h-4 w-4" aria-hidden="true" />
              </Button>

              {/* 次のページボタン */}
              <Button
                aria-label="Go to next page"
                variant="outline"
                className="h-8 w-8 p-0"
                onClick={() => {
                  setPagination((prev) => ({
                    ...prev,
                    pageIndex: Math.min(totalPages - 1, prev.pageIndex + 1),
                  }));
                  onPageChange?.();
                }}
                disabled={pagination.pageIndex >= totalPages - 1}
              >
                <ChevronRightIcon className="h-4 w-4" aria-hidden="true" />
              </Button>

              {/* 最後のページボタン */}
              <Button
                aria-label="Go to last page"
                variant="outline"
                className="hidden h-8 w-8 p-0 lg:flex"
                onClick={() => {
                  setPagination((prev) => ({
                    ...prev,
                    pageIndex: totalPages - 1,
                  }));
                  onPageChange?.();
                }}
                disabled={pagination.pageIndex >= totalPages - 1}
              >
                <DoubleArrowRightIcon className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
