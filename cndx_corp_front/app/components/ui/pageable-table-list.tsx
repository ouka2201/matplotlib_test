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
import { ScrollArea, ScrollBar } from "~/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { ResizableColumnHandle } from "../common/ResizableColumnHandle";
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
  initailSort?: SortingState;
  pageCount: number;
  totalCount: number;
  renderRow?: (item: TData, index: number) => React.ReactNode;
  showPagination?: boolean;
}

export function PageableTable<TData, TValue>({
  columns,
  data,
  totalCount,
  initailSort = [],
  pageCount,
  pageSizeOptions = [5, 10, 20, 50],
  renderRow,
  showPagination = true,
}: PageableTableProps<TData, TValue>) {
  const [{ pageIndex, pageSize }, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: pageSizeOptions[0],
  });

  const [sorting, setSorting] = useState<SortingState>(initailSort);

  const table = useReactTable({
    data,
    columns,
    pageCount: pageCount ?? -1,
    getCoreRowModel: getCoreRowModel(),
    columnResizeMode: "onChange",
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: {
      pagination: { pageIndex, pageSize },
      sorting,
    },
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    getPaginationRowModel: getPaginationRowModel(),
    manualPagination: true,
    manualFiltering: false,
    manualSorting: false, //use pre-sorted row model instead of sorted row model
  });

  const startRow = pageIndex * pageSize + 1;
  // const endRow = startRow + table.getFilteredRowModel().rows.length - 1;
  const endRow = Math.min(totalCount, (pageIndex + 1) * pageSize);
  const currentPageCount = endRow - startRow + 1;

  return (
    <>
      <ScrollArea className="h-[calc(50vh-50px)] rounded-md border">
        {/* <div className="relative overflow-auto h-[calc(50vh-120px)] rounded-md border"> */}
        <Table className="w-full border-collapse">
          <TableHeader className="sticky top-0 z-200 bg-[#F2F4F7]">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead
                      key={header.id}
                      style={{ width: header.getSize() }}
                      // className="text-black font-bold text-center overflow-auto"
                      className="text-black P-0"
                      colSpan={header.colSpan}
                      // colSpan={table.getAllLeafColumns().length}
                    >
                      <div
                        role="button"
                        tabIndex={0}
                        // className="flex items-center justify-normal"
                        onClick={header.column.getToggleSortingHandler()}
                        onKeyDown={header.column.getToggleSortingHandler()}
                        className="flex items-center justify-normal bg-[#F2F4F7]"
                      >
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                        {{
                          asc: <TriangleUpIcon />,
                          desc: <TriangleDownIcon />,
                        }[header.column.getIsSorted() as string] ?? null}
                        {/* ▼ リサイズ専用ハンドル */}
                        {/* <div
                          role="presentation" // ← ボタンじゃないよ、と明示
                          tabIndex={-1}       // ← フォーカスさせない
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                          className="w-1 h-full cursor-col-resize bg-gray-300"
                          onClick={(e) => e.stopPropagation()} // ← ソート抑制
                        />
                         */}
                        <ResizableColumnHandle onResizeStart={header.getResizeHandler()} />
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
                table
                  .getRowModel()
                  .rows.slice(
                    table.getState().pagination.pageIndex * table.getState().pagination.pageSize,
                    (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize
                  )
                  .map((row) => (
                    <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                      ))}
                    </TableRow>
                  ))
              )
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  {Messages.SEARCH_NONE}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <ScrollBar orientation="horizontal" />
        {/* </div> */}
      </ScrollArea>

      {showPagination && (
        <div className="flex flex-col items-center justify-end gap-2 space-x-2 py-4 sm:flex-row">
          <div className="flex w-full items-center justify-between">
            <div className="flex-1 text-sm text-muted-foreground">
              {/* Showing {startRow}-{endRow} of {totalCount} rows.
            {totalCount}件中  {startRow}-{endRow}件 */}
              {totalCount} 件中 {currentPageCount}件
            </div>
            <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-6 lg:gap-8">
              <div className="flex items-center space-x-2">
                <p className="whitespace-nowrap text-sm font-medium">1ページの行数:</p>
                <Select
                  value={`${table.getState().pagination.pageSize}`}
                  onValueChange={(value) => {
                    table.setPageSize(Number(value));
                  }}
                >
                  <SelectTrigger className="h-8 w-[70px]">
                    <SelectValue placeholder={table.getState().pagination.pageSize} />
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
              {/* Page {table.getState().pagination.pageIndex + 1} of{" "} */}
              {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
            </div>
            <div className="flex items-center space-x-2">
              <Button
                aria-label="Go to first page"
                variant="outline"
                className="hidden h-8 w-8 p-0 lg:flex"
                onClick={() => table.setPageIndex(0)}
                disabled={table.getState().pagination.pageIndex === 0}
              >
                <DoubleArrowLeftIcon className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                aria-label="Go to previous page"
                variant="outline"
                className="h-8 w-8 p-0"
                onClick={() => table.setPageIndex(table.getState().pagination.pageIndex - 1)}
                disabled={table.getState().pagination.pageIndex === 0}
              >
                <ChevronLeftIcon className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                aria-label="Go to next page"
                variant="outline"
                className="h-8 w-8 p-0"
                onClick={() => table.setPageIndex(table.getState().pagination.pageIndex + 1)}
                disabled={
                  (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize >=
                  table.getRowModel().rows.length
                }
              >
                <ChevronRightIcon className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                aria-label="Go to last page"
                variant="outline"
                className="hidden h-8 w-8 p-0 lg:flex"
                onClick={() =>
                  table.setPageIndex(
                    Math.ceil(table.getRowModel().rows.length / table.getState().pagination.pageSize) - 1
                  )
                }
                disabled={
                  (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize >=
                  table.getRowModel().rows.length
                }
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
