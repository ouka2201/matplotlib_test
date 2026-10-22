import React, { useCallback, useEffect, useMemo, useState } from "react";
import SearchForm from "~/components/common/search-form";
import { DialogDescription, DialogTitle } from "~/components/ui/dialog";
import { Messages } from "~/constants/messages/message";
import { useLoadingSpinner } from "~/hooks/use-loadingspinner";
import { postData } from "~/lib/fetch";

type SupplierItem = {
  id: string;
  name: string;
  extra?: unknown;
};

type Props = {
  title: string;
  expLabel: string;
  searchNone: string;
  searchLabel: string;
  apiPath: string;
  startYearMonth: string;
  mapItem: (raw: any) => SupplierItem;
  onSelect: (item: SupplierItem) => void;
};

const cacheByYear = new Map<string, SupplierItem[]>();
const inFlightByYear = new Map<string, Promise<SupplierItem[]>>();

const filterItems = (items: SupplierItem[], keyword: string): SupplierItem[] => {
  const trimmed = keyword.trim().toLowerCase();
  if (!trimmed) return items;
  return items.filter((item) => {
    const name = item.name?.toLowerCase() ?? "";
    const id = item.id?.toLowerCase() ?? "";
    return name.includes(trimmed) || id.includes(trimmed);
  });
};

export default function SupplierSearchModal({
  title,
  expLabel,
  searchNone,
  searchLabel,
  apiPath,
  startYearMonth,
  mapItem,
  onSelect,
}: Props) {
  const { withLoading } = useLoadingSpinner();
  const [companyName, setCompanyName] = useState("");
  const [items, setItems] = useState<SupplierItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<SupplierItem[]>([]);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const cacheKey = useMemo(() => {
    const targetYear = startYearMonth.slice(0, 4);
    return `${apiPath}:${targetYear}`;
  }, [apiPath, startYearMonth]);

  const loadInitial = useCallback(async () => {
    const targetYear = startYearMonth.slice(0, 4);
    if (!targetYear) return;

    if (cacheByYear.has(cacheKey)) {
      const cached = cacheByYear.get(cacheKey) ?? [];
      setItems(cached);
      setFilteredItems(cached);
      return;
    }

    if (inFlightByYear.has(cacheKey)) {
      const cached = await inFlightByYear.get(cacheKey);
      const list = cached ?? [];
      setItems(list);
      setFilteredItems(list);
      return;
    }

    const requestParams = {
      company_name: "",
      target_year: targetYear,
    };

    setIsLoading(true);
    const promise = withLoading(() => postData(`${apiPath}`, requestParams)).then((response) =>
      (response ?? []).map(mapItem),
    );
    inFlightByYear.set(cacheKey, promise);

    try {
      const list = await promise;
      cacheByYear.set(cacheKey, list);
      setItems(list);
      setFilteredItems(list);
    } catch (error) {
      console.error(Messages.VALIDATION.api.search_error, error);
    } finally {
      inFlightByYear.delete(cacheKey);
      setIsLoading(false);
    }
  }, [apiPath, cacheKey, mapItem, startYearMonth, withLoading]);

  useEffect(() => {
    if (hasLoaded) return;
    setHasLoaded(true);
    loadInitial();
  }, [hasLoaded, loadInitial]);

  const handleSearch = () => {
    setFilteredItems(filterItems(items, companyName));
  };

  return (
    <div>
      <DialogTitle className="h-8">{title}</DialogTitle>
      <DialogDescription className="h-8">{expLabel}</DialogDescription>
      <DialogDescription hidden />
      <SearchForm
        fields={[{ id: "company_name", label: searchLabel, placeholder: "" }]}
        values={{ company_name: companyName }}
        onValueChange={(val) => setCompanyName(val.company_name || "")}
        onSearch={handleSearch}
      />
      {/* 一覧 */}
      <div className="">
        <div>
          <table className="w-full caption-bottom text-sm mt-8">
            <thead className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
              <tr className="border-b transition-colors hover:bg-muted/50">
                <th className="w-[10%] p-4 align-middle">No</th>
                <th className="w-[90%] p-4 align-middle">{searchLabel}</th>
              </tr>
            </thead>
          </table>
        </div>
        <div className="h-80 overflow-scroll">
          <table className="w-full caption-bottom text-sm">
            <tbody className="">
              {isLoading ? (
                <tr>
                  <td colSpan={2}>読み込み中...</td>
                </tr>
              ) : filteredItems.length > 0 ? (
                filteredItems.map((item, index) => (
                  <tr key={`${item.id}-${index}`} className="border-b transition-colors hover:bg-muted/50 h-10">
                    <td className="w-[10%] p-4 align-middle">{index + 1}</td>
                    <td className="w-[90%] p-4 align-middle">
                      <button
                        onClick={() => onSelect(item)}
                        className="w-full justify-start text-left text-[#00897b] underline font-semibold bg-transparent p-0 m-0 border-none cursor-pointer min-w-[250px]"
                        type="button"
                      >
                        {item.name}
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={2}>{searchNone}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
