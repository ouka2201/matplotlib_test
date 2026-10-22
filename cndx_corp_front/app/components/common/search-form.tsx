import SectionTitle from "~/components/common/section-title";
import { Button } from "~/components/ui/button";
import { Command, CommandInput } from "~/components/ui/command";
import { cn } from "~/lib/utils";

export interface SearchField {
  id: string;
  label: string;
  type?: "text" | "number" | "select";
  placeholder?: string;
  className?: string;
  options?: { value: string; label: string }[];
  disabled?: boolean;
}

interface SearchFormProps {
  searchConditionTitle?: string;
  fields: SearchField[];
  values: Record<string, string>;
  onValueChange: (newValues: Partial<Record<string, string>>) => void;
  onSearch?: () => void;
  onReset?: () => void;
  columns?: number;
}

export default function SearchForm({
  searchConditionTitle,
  fields,
  values,
  onValueChange,
  onSearch,
  onReset,
}: // columns = 3,
  SearchFormProps) {
  // const gridColsClass = `grid grid-cols-1 sm:grid-cols-${columns} gap-4`;

  return (
    <>
      {searchConditionTitle && <SectionTitle>{searchConditionTitle}</SectionTitle>}

      {/* <div className={`grid gap-4`} style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}> */}

      {/* <div className="flex flex-wrap gap-x-6 gap-y-4 items-start">
        {fields.map((field) => (
          <div key={field.id} className="flex flex-col gap-1">
            <label htmlFor={field.id} className="text-sm font-medium text-[#667085] w-fit">
              {field.label}
            </label>

            {field.type === "select" && field.options ? (
              <select
                id={field.id}
                value={values[field.id] || ""}
                onChange={(e) => onValueChange({ [field.id]: e.target.value })}
                className="border rounded px-3 py-2 text-sm min-w-[160px]"
                disabled={field.disabled}
              >
                <option value="">選択してください</option>
                {field.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <Command className={cn("min-w-[160px]", field.className)}>
                <CommandInput
                  id={field.id}
                  placeholder={field.placeholder}
                  value={values[field.id] || ""}
                  onValueChange={(value) => onValueChange({ [field.id]: value })}
                  disabled={field.disabled}
                />
              </Command>
            )}
          </div>
        ))}

        {onSearch && (
          <div className="flex flex-wrap justify-end items-end min-h-[53px] gap-2">
            <Button variant="second" size="second" onClick={onSearch} className="w-[100px]">
              検索
            </Button>
            {onReset && (
              <Button variant="third" size="third" onClick={onReset} className="w-[100px]">
                リセット
              </Button>
            )}
          </div>
        )}
      </div> */}
      <div className="flex flex-wrap gap-x-4 gap-y-4 items-end w-full">
        {fields.map((field) => (
          <div key={field.id} className="flex flex-col gap-1 flex-1 min-w-[200px]">
            <label htmlFor={field.id} className="text-sm font-medium text-[#667085] w-fit">
              {field.label}
            </label>
            {field.type === "select" && field.options ? (
              <select
                id={field.id}
                value={values[field.id] || ""}
                onChange={(e) => onValueChange({ [field.id]: e.target.value })}
                className="border rounded px-3 py-2 text-sm w-full h-10"
                disabled={field.disabled}
              >
                {/* <option value="">選択してください</option> */}
                <option value="" disabled hidden>
                  選択してください
                </option>
                {field.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <Command className={cn("w-full", field.className)}>
                <CommandInput
                  id={field.id}
                  placeholder={field.placeholder}
                  value={values[field.id] || ""}
                  onValueChange={(value) => onValueChange({ [field.id]: value })}
                  disabled={field.disabled}
                  className="h-10"
                />
              </Command>
            )}
          </div>
        ))}

        {onSearch && (
          <div className="flex items-end gap-2 flex-none">
            <Button variant="second" size="second" onClick={onSearch} className="w-[100px]">
              検索
            </Button>
            {onReset && (
              <Button variant="third" size="third" onClick={onReset} className="w-[100px]">
                リセット
              </Button>
            )}
          </div>
        )}
      </div>
    </>
  );
}
